
from pathlib import Path

import matplotlib.pyplot as plt
import foxes.constants as FC
import foxes.variables as FV
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from foxes.algorithms.downwind import Downwind
from foxes.core import WindFarm
from foxes.input.farm_layout import add_from_df
from foxes.input.states import StatesTable
from foxes.models.turbine_types import CpCtFromTwo
from foxes.output import FlowPlots2D
from foxes.models.model_book import ModelBook
from windIO.utils.yml_utils import load_yaml

from .base_interface import WCompBase
from .output_struct import WakePlane, WakeProfile
from .plotting import plot_plane, plot_profile


class WCompFoxes(WCompBase):

    LPLOT_COLOR = "red"
    LEGEND = "Foxes"

    def __init__(self, input_file: str | Path):
        input_dictionary = load_yaml(input_file)
        self.mbook, self.farm, self.states, self.algo = self.read_case(input_dictionary)
        self.farm_results = self.algo.calc_farm()

    @property
    def rotor_diameter(self) -> float:
        return self.mbook.turbine_types["windio_turbine"].D

    @property
    def hub_height(self) -> float:
        return self.mbook.turbine_types["windio_turbine"].H

    ### Create the model from windIO

    def read_resource(self, res, fixed_vars={}, **kwargs):
        """
        Reads a WindIO energy resource

        Parameters
        ----------
        res_yaml : str
            Path to the yaml file
        fixed_vars : dict
            Additional fixes variables that do 
            not occur in the yaml
        kwargs : dict, optional
            Additional arguments for StatesTable

        Returns
        -------
        states: foxes.states.StatesTable
            The uniform states

        """
        wres = res["wind_resource"]

        wd = np.array(wres["wind_direction"], dtype=FC.DTYPE)
        ws = np.array(wres["wind_speed"], dtype=FC.DTYPE)
        n_wd = len(wd)
        n_ws = len(ws)
        n = n_wd*n_ws

        data = np.zeros((n_wd, n_ws, 2), dtype=FC.DTYPE)
        data[:, :, 0] = wd[:, None]
        data[:, :, 1] = ws[None, :]
        names = ["wind_direction", "wind_speed"]

        def _to_data(v, d, dims):
            nonlocal data, names
            hdata = np.zeros((n_wd, n_ws, 1), dtype=FC.DTYPE)
            if len(dims) == 0:
                hdata[:, :, 0] = FC.DTYPE(d)
            elif len(dims) == 1:
                if dims[0] == "wind_direction":
                    hdata[:, :, 0] = np.array(d, dtype=FC.DTYPE)[:, None]
                elif dims[0] == "wind_speed":
                    hdata[:, :, 0] = np.array(d, dtype=FC.DTYPE)[None, :]
                else:
                    raise ValueError(f"Unknown dimension '{dims[0]}' for data '{v}'")
            elif len(dims) == 2:
                if dims[0] == "wind_direction" and dims[1] == "wind_speed":
                    hdata[:, :, 0] = np.array(d, dtype=FC.DTYPE)
                elif dims[1] == "wind_direction" and dims[0] == "wind_speed":
                    hdata[:, :, 0] = np.swapaxes(np.array(d, dtype=FC.DTYPE), 0, 1)
                else:
                    raise ValueError(f"Cannot handle dims = {dims} for data '{v}'")
            else:
                raise ValueError(f"Can not accept more than two dimensions, got {dims} for data '{v}'")
            data = np.append(data, hdata, axis=2)
            names.append(v)

        vmap = {
            "wind_direction": FV.WD,
            "wind_speed": FV.WS,
            "turbulence_intensity": FV.TI,
            "air_density": FV.RHO,
            "probability": FV.WEIGHT
        }

        for v, d in wres.items():
            if v in vmap and isinstance(d, dict):
                _to_data(v, d["data"], d["dims"])

        n_vars = len(names)
        data = data.reshape(n, n_vars) 

        data = pd.DataFrame(index=range(n), data=data, columns=names)
        data.index.name = "state"
        data.rename(columns=vmap, inplace=True)
        
        ovars = {v: v for v in data.columns if v != FV.WEIGHT}
        ovars.update({k: v for k, v in fixed_vars.items() if k not in data.columns})

        return StatesTable(
            data,
            output_vars=ovars,
            fixed_vars=fixed_vars,
            **kwargs
        )

    def read_site(self, site, **kwargs):
        """
        Reads a WindIO site

        Parameters
        ----------
        site_yaml : str
            Path to the yaml file
        kwargs : dict, optional
            Additional arguments for read_resource

        Returns
        -------
        states : foxes.states.States
            The states object

        """
        res_yaml = site["energy_resource"]
        states = self.read_resource(res_yaml, **kwargs)

        return states

    def read_farm(self, fdict, mbook=None, layout=-1, turbine_models=[], **kwargs):
        """
        Reads a WindIO wind farm

        Parameters
        ----------
        farm_yaml : str
            Path to the yaml file
        mbook : foxes.ModelBook, optional
            The model book to start from
        layout : str or int
            The layout choice
        turbine_models : list of str
            Additional turbine models
        kwargs : dict, optional
            Additional parameters for add_from_df()

        Returns
        -------
        mbook : foxes.ModelBook
            The model book
        farm : foxes.WindFarm
            The wind farm

        """
        mbook = ModelBook() if mbook is None else mbook

        if isinstance(layout, str):
            layout = fdict['layouts'][layout]
        else:
            lname = list(fdict['layouts'].keys())[layout]
            layout = fdict['layouts'][lname]

        x = np.array(layout["coordinates"]["x"], dtype=FC.DTYPE)
        y = np.array(layout["coordinates"]["y"], dtype=FC.DTYPE)
        N = len(x)
        ldata = pd.DataFrame(index=range(N))
        ldata.index.name = "index"
        ldata["x"] = x
        ldata["y"] = y

        tdict = fdict["turbines"]
        pdict = tdict["performance"]

        ct_ws = np.array(pdict["Ct_curve"]["Ct_wind_speeds"], dtype=FC.DTYPE)
        ct_data = pd.DataFrame(index=range(len(ct_ws)))
        ct_data["ws"] = ct_ws
        ct_data["ct"] = np.array(pdict["Ct_curve"]["Ct_values"], dtype=FC.DTYPE)

        cp_ws = np.array(pdict["Cp_curve"]["Cp_wind_speeds"], dtype=FC.DTYPE)
        cp_data = pd.DataFrame(index=range(len(cp_ws)))
        cp_data["ws"] = cp_ws
        cp_data["cp"] = np.array(pdict["Cp_curve"]["Cp_values"], dtype=FC.DTYPE)

        D = float(tdict["rotor_diameter"])
        H = float(tdict["hub_height"])

        mbook.turbine_types["windio_turbine"] = CpCtFromTwo(
            cp_data,
            ct_data,
            col_ws_cp_file="ws",
            col_cp="cp",
            D=D,
            H=H
        )

        models = ["windio_turbine"] + turbine_models
        farm = WindFarm(name=fdict["name"])

        add_from_df(farm, ldata, col_x="x", col_y="y", turbine_models=models, **kwargs)

        return mbook, farm

    def read_anlyses(self, analyses, mbook, farm, states, keymap={}, **algo_pars):
        """
        Reads a WindIO wind farm

        Parameters
        ----------
        analyses : dict
            The analyses sub-dict of the case
        mbook : foxes.ModelBook
            The model book
        farm : foxes.WindFarm
            The wind farm
        states : foxes.states.States
            The states object
        keymap : dict
            Translation from windio to foxes keywords
        algo_type : str
            The default algorithm class name
        algo_pars : dict, optional
            Additional parameters for the algorithm 
            constructor

        Returns
        -------
        algo : foxes.core.Algorithm
            The algorithm

        """
        wmodel = analyses["wake_model"]["name"]
        wmodels = [keymap.get(wmodel, wmodel)]

        return Downwind(
            mbook,
            farm,
            states,
            verbosity=0,
            rotor_model="grid16",
            wake_models=wmodels,
            **algo_pars
        )

    def read_case(self, case, site_pars={}, farm_pars={}, ana_pars={}):
        """
        Reads a WindIO case

        Parameters
        ----------
        case_yaml : str
            Path to the yaml file
        site_pars : dict
            Additional arguments for read_site
        farm_pars : dict
            Additional arguments for read_farm
        ana_pars : dict
            Additional arguments for read_analyses

        Returns
        -------
        mbook : foxes.ModelBook
            The model book
        farm : foxes.WindFarm
            The wind farm
        states : foxes.states.States
            The states object
        algo : foxes.core.Algorithm
            The algorithm

        """
        site_yaml = case["site"]
        states = self.read_site(site_yaml, **site_pars)

        farm_yaml = case["wind_farm"]
        mbook, farm = self.read_farm(farm_yaml, **farm_pars)

        attr_dict = case["attributes"]

        algo = self.read_anlyses(
            attr_dict["analyses"],
            mbook,
            farm,
            states,
            **ana_pars
        )

        return mbook, farm, states, algo

    ### Post processing

    def AEP(self):
        return self.sim_res.aep(normalize_probabilities=True).sum()

    # 1D line plots

    def vertical_profile_plot(
        self,
        wind_direction: float,
        y_coordinate: float,
        xmin: float,
        xmax: float
    ):
        """
        Args:
            wind_direction (float): The wind direction to use for the visualization
            resolution (tuple): The (x, y) resolution of the horizontal plane
        """
        ax = plt.gca()

        # create points of interest, shape (n_states, n_points, 3):
        n_points = 8000
        points = np.zeros((1, n_points, 3))
        points[:, :, 0] = np.linspace(xmin, xmax, n_points)[None, :]
        points[:, :, 2] = self.hub_height

        point_results = self.algo.calc_points(self.farm_results, points)

        profile = WakeProfile(
            points[0, :, 0],
            point_results[FV.WS][0, :],
        )
        plot_profile(
            profile,
            ax=ax,
            # direction='x',
            # component='u',
            color=self.LPLOT_COLOR,
            label=self.LEGEND
        )

    def xsection_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        ymin: float,
        ymax: float
    ):
        ax = plt.gca()

        # create points of interest, shape (n_states, n_points, 3):
        n_points = 8000
        points = np.zeros((1, n_points, 3))
        points[:, :, 0] = x_coordinate * np.ones((1, n_points))[None, :]
        points[:, :, 1] = np.linspace(ymin, ymax, n_points)[None, :]
        points[:, :, 2] = self.hub_height

        # calculate point results:
        point_results = self.algo.calc_points(self.farm_results, points)

        # create figure:
        profile = WakeProfile(
            points[0, :, 1],
            point_results[FV.WS][0, :],
        )
        plot_profile(
            profile,
            ax=ax,
            # direction='y',
            # component='u',
            color=self.LPLOT_COLOR,
            label=self.LEGEND
        )

    # 2D contour plots

    def horizontal_contour(self, wind_direction: float, resolution: tuple) -> WakePlane:

        x1_bounds = (np.min(self.farm_results.X) - 2 * self.rotor_diameter, np.max(self.farm_results.X) + 10 * self.rotor_diameter)
        x2_bounds = (np.min(self.farm_results.Y) - 2 * self.rotor_diameter, np.max(self.farm_results.Y) + 2 * self.rotor_diameter)

        o = FlowPlots2D(self.algo, self.farm_results)
        # g = o.gen_states_fig_xy("WS", resolution=10, figsize=(10, 5), verbosity=0)
        xres = (x1_bounds[1] - x1_bounds[0]) / resolution[0]
        yres = (x2_bounds[1] - x2_bounds[0]) / resolution[1]
        grid_points, u = o.get_mean_fig_xy(
            "WS",
            xmin=x1_bounds[0],
            xmax=x1_bounds[1],
            ymin=x2_bounds[0],
            ymax=x2_bounds[1],
            resolution=(xres, yres),
            figsize=(10, 5)
        )
        x = grid_points[:, :, 0]
        y = grid_points[:, :, 1]
        # z = grid_points[:, :, 2]

        plane = WakePlane(
            x[0],
            y[0],
            u,
            "z",
            resolution,
        )
        plot_plane(
            plane,
            ax=plt.gca(), #axarr,
            # cmap='Blues_r',
            # color_bar=True,
            clevels=100
        )
        return plane
    
    def xsection_contour(self, wind_direction: float, resolution: tuple, x_coordinate: float) -> WakePlane:
        # TODO
        pass
