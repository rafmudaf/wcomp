
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from py_wake import HorizontalGrid, XZGrid, YZGrid
from py_wake.site.xrsite import XRSite
from py_wake.wind_farm_models.engineering_models import EngineeringWindFarmModel
from py_wake.wind_turbines import WindTurbine
from py_wake.wind_turbines.power_ct_functions import PowerCtFunctions

from py_wake.wind_farm_models.engineering_models import PropagateDownwind
from py_wake.literature.noj import Jensen_1983
from py_wake.literature.gaussian_models import Niayifar_PorteAgel_2016
from py_wake.deficit_models.gaussian import BastankhahGaussianDeficit
from py_wake.deflection_models import JimenezWakeDeflection
from py_wake.literature.turbopark import Nygaard_2022

from windIO.utils.yml_utils import load_yaml

from .base_interface import WCompBase
from .output_struct import WakePlane, WakeProfile
from .plotting import plot_plane, plot_profile

# This dictionary maps generic model names in the windIO input file
# to the tool's specific name. It also maps parameter names from the
# referenced papers to the parameters in the implementation.
WAKE_MODEL_MAPPING = {

    # Velocity models
    "jensen": {
        "model_ref": Jensen_1983,
        "parameters": {
            "k": "alpha",
        }
    },
    # "niayifar-porteagel": {
    #     "model_ref": Niayifar_PorteAgel_2016,
    #     "parameters": {
    #         "a1": "a0",
    #         "a2": "a1",
    #     }
    # },
    # "bastankhah2014": {
    #     "model_ref": BastankhahGaussianDeficit,
    #     "parameters": {
    # #         "k": "a0",
    # #         "a2": "a1",
    #     }
    # },
    # "bastankhah2016": {     # NOT IMPLEMENTED
    #     "model_ref": None,
    #     "parameters": {
    #     }
    # },
    "turbopark": {
        "model_ref": Nygaard_2022,
        "parameters": {
            "A": "A",
        }
    },

    # Deflection model
    # None: {
    #     "model_ref": "none",
    #     "parameters": {}
    # },
    "jimenez": {
        "model_ref": JimenezWakeDeflection,
        "parameters": {}    # No parameters
    },
    # "bastankhah2016_deflection": {
    #     "model_ref": ,
    #     "parameters": {}    # No parameters
    # },
}

class WCompPyWake(WCompBase):

    LINE_PLOT_COLOR = "blue"
    LINE_PLOT_MARKER = ""
    LINE_PLOT_LINESTYLE = "--"
    LEGEND = "PyWake"

    def __init__(self, input_file: str | Path):
        input_dictionary = load_yaml(input_file)
        self.site, self.wt, (self.x, self.y) = self._create_pywake_data(input_dictionary)

        yaw_angles = input_dictionary["attributes"]["analyses"]["yaw_angles"]
        tilt_angles = [0.0]

        wes_analysis = input_dictionary["attributes"]["analyses"]
        _velocity_model_mapping = WAKE_MODEL_MAPPING[wes_analysis["wake_model"]["velocity"]["name"]]
        _velocity_model = _velocity_model_mapping["model_ref"]
        _velocity_model_parameters = {
            k: wes_analysis["wake_model"]["velocity"]["parameters"][v]
            for k, v in _velocity_model_mapping["parameters"].items()
        }

        deflection_model = None

        # added_args_velocity_deficit = {}
        # if velocity_deficit 

        self.wfm = _velocity_model(
            site=self.site,
            windTurbines=self.wt,
            **_velocity_model_parameters,
            deflectionModel=deflection_model,
        )
        self.sim_res = self.wfm(
            self.x,
            self.y,
            wd=self.site.ds.wd.data,
            yaw=yaw_angles,
            tilt=tilt_angles,
        )

    @property
    def rotor_diameter(self) -> float:
        return self.wt.diameter()

    @property
    def hub_height(self) -> float:
        return self.wt.hub_height()

    ### Create the model from windIO

    def _yml2Site(self, resource):
        if 'energy_resource' in resource:
            resource = resource['energy_resource']
        data = resource['wind_resource']
        ds = xr.Dataset({k: (v['dims'], v['data']) for k, v in data.items() if hasattr(v, 'keys') and 'dims' in v},
                        coords={k: v for k, v in data.items() if not hasattr(v, 'keys')})
        return self._xr2Site(ds)

    def _xr2Site(self, ds, interp_method='nearest') -> XRSite:
        ds = ds.rename(**{k: v for k, v in [('height', 'h'),
                                            ('wind_direction', 'wd'),
                                            ('wind_speed', 'ws'),
                                            ('wind_turbine', 'i'),
                                            ('probability', 'P'),
                                            ('weibull_a', 'Weibull_A'),
                                            ('weibull_k', 'Weibull_k'),
                                            ('sector_probability', 'Sector_frequency'),
                                            ('turbulence_intensity', 'TI')] if k in ds})
        if 'ws' in ds:
            return XRSite(ds, default_ws=ds.ws, interp_method=interp_method)
        else:
            return XRSite(ds, interp_method=interp_method)

    def _yml2WindTurbines(self, wt):
        power = wt['performance']

        if 'power_curve' in power:
            raise NotImplementedError()
        elif 'cp_curve' in power:
            raise NotImplementedError()
        else:
            def power_func(ws):
                return np.interp(
                    ws,
                    power['Cp_curve']['Cp_wind_speeds'],
                    power['Cp_curve']['Cp_values']
                )

            def ct_func(ws):
                return np.interp(
                    ws,
                    power['Ct_curve']['Ct_wind_speeds'],
                    power['Ct_curve']['Ct_values']
                )

        return WindTurbine(
            name=wt['name'],
            diameter=wt['rotor_diameter'],
            hub_height=wt['hub_height'],
            powerCtFunction=PowerCtFunctions(power_func, 'w', ct_func)
        )

    def _create_pywake_data(self, wes):
        wf = wes['wind_farm']
        x, y = [wf['layouts']['initial_layout']['coordinates'][xy] for xy in 'xy']

        wt = self._yml2WindTurbines(wf['turbines'])
        site = self._yml2Site(wes['site'])
        return site, wt, (x, y)

    ### Post processing

    def AEP(self):
        return self.sim_res.aep(normalize_probabilities=True).sum()

    # 1D line plots

    def vertical_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        y_coordinate: float,
        zmax: float
    ):
        """
        Args:
            wind_direction (float): The wind direction to use for the visualization
            resolution (tuple): The (x, y) resolution of the horizontal plane
        """
        ax = plt.gca()

        n_points = 20

        wake_data = self.sim_res.flow_map(
            XZGrid(
                y=y_coordinate,
                x=x_coordinate,
                z=np.linspace(0, zmax, n_points),
            ),
            wd=wind_direction,
            ws=None
        )
        # wake_data.plot_wake_map()

        _z = wake_data.h
        _u = wake_data.sel(h=_z).WS_eff
        profile = WakeProfile(
            _z,
            _u[:,0,0,0]
        )
        plot_profile(
            profile,
            ax=ax,
            color=self.LINE_PLOT_COLOR,
            marker=self.LINE_PLOT_MARKER,
            linestyle=self.LINE_PLOT_LINESTYLE,
            label=self.LEGEND
        )

    def streamwise_profile_plot(
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

        n_points_x = 50
        # n_points_y = 50

        wake_data = self.sim_res.flow_map(
            XZGrid(
                y=y_coordinate,
                x=np.linspace(xmin, xmax, n_points_x),
                z=self.hub_height,
                # resolution=100,  # Points in the x direction; z points are derived from this: z = np.arange(0, (1 + self.extend) * (h_i.max() + d_i.max() / 2), np.diff(x[:2])[0])
                # resolution is not used in this case because I'm specifying x and z grids and the y location
                # extend=1000
            ),
            wd=wind_direction,
            ws=None
        )
        # wake_data.plot_wake_map()

        _x = wake_data.sel(h=self.hub_height).x
        _u = wake_data.sel(h=self.hub_height).WS_eff

        profile = WakeProfile(
            _x,
            _u[:,0,0,0]
        )
        plot_profile(
            profile,
            ax=ax,
            # direction='x',
            # component='u',
            color=self.LINE_PLOT_COLOR,
            marker=self.LINE_PLOT_MARKER,
            linestyle=self.LINE_PLOT_LINESTYLE,
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

        n_points = 20
        wake_data = self.sim_res.flow_map(
            YZGrid(
                x=x_coordinate,
                y=np.linspace(ymin, ymax, n_points),
                z=self.hub_height,
            ),
            wd=wind_direction,
            ws=None
        )
        # wake_data.plot_wake_map()

        _y = wake_data.sel(h=self.hub_height).y
        _u = wake_data.sel(h=self.hub_height).WS_eff
        profile = WakeProfile(
            _y,
            _u[:,0,0,0],
        )
        plot_profile(
            profile,
            ax=ax,
            # direction='x',
            # component='u',
            color=self.LINE_PLOT_COLOR,
            marker=self.LINE_PLOT_MARKER,
            linestyle=self.LINE_PLOT_LINESTYLE,
            label=self.LEGEND
        )

    # 2D contour plots

    def horizontal_contour(self, wind_direction: float, resolution: float) -> WakePlane:
        """
        Args:
            wind_direction (float): The wind direction to use for the visualization
            resolution (float): The spacial resolution of the horizontal plane
        """

        x_min = np.min(self.sim_res.x) - 2 * self.rotor_diameter
        x_max = np.max(self.sim_res.x) + 10 * self.rotor_diameter
        y_min = np.min(self.sim_res.y) - 2 * self.rotor_diameter
        y_max = np.max(self.sim_res.y) + 2 * self.rotor_diameter

        grid = HorizontalGrid(
            x=np.linspace(x_min, x_max, int((x_max - x_min) / resolution) + 1),
            y=np.linspace(y_min, y_max, int((y_max - y_min) / resolution) + 1),
            h=self.hub_height,
        )
        flow_map = self.sim_res.flow_map(wd=wind_direction, grid=grid)

        x = flow_map.X.flatten()
        y = flow_map.Y.flatten()
        u = flow_map.WS_eff.to_numpy().flatten()

        plane = WakePlane(x, y, u, "z", resolution)
        plot_plane(
            plane,
            ax=plt.gca(),
            # cmap='Blues_r',
            # color_bar=True,
            clevels=100
        )
        return plane

    def xsection_contour(
        self,
        wind_direction: float,
        resolution: float,
        x_coordinate: float
    ) -> WakePlane:

        y_min = np.min(self.sim_res.y) - 2 * self.rotor_diameter
        y_max = np.max(self.sim_res.y) + 2 * self.rotor_diameter
        z_min = 0.001
        z_max = 6 * self.hub_height

        grid = YZGrid(
            x=x_coordinate,
            y=np.linspace(y_min, y_max, int((y_max - y_min) / resolution) + 1),
            z=np.linspace(z_min, z_max, int((z_max - z_min) / resolution) + 1),
        )
        flow_map = self.sim_res.flow_map(wd=wind_direction, grid=grid)

        y = flow_map.Y.flatten()
        z = flow_map.Z.flatten()
        u = flow_map.WS_eff.to_numpy().flatten()

        plane = WakePlane(y, z, u, "x", resolution)
        plot_plane(
            plane,
            ax=plt.gca(),
            # cmap='Blues_r',
            # color_bar=True,
            clevels=100
        )
        return plane