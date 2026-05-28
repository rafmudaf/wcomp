
import copy
from pathlib import Path

import numpy as np
from floris.floris_model import FlorisModel
from windIO import load_yaml

from .base_interface import WCompBase
from .output_struct import WakePlane, WakeProfile
from .plotting import plot_plane, plot_profile

# This dictionary maps generic model names in the windIO input file
# to the tool's specific name. It also maps parameter names from the
# referenced papers to the parameters in the implementation.
# "windIO_model_name": {
#   "model_ref": the current software's reference for this wake model,
#   "parameters": {
#       "model parameter": windIO parameter
#   }
# }
WAKE_MODEL_MAPPING = {

    # Velocity models
    "jensen": {
        "model_ref": "jensen",
        "parameters": {
            "we": "alpha",
        }
    },
    # "bastankhah2014": {     # NOT IMPLEMENTED
    #     "model_ref": None,
    #     "parameters": {}
    # },
    "bastankhah2016": {
        "model_ref": "gauss",
        "parameters": {
            "alpha": "alpha",
            "beta": "beta",
            "ka": "ka",
            "kb": "kb",
        }
    },
    "turbopark": {
        "model_ref": "turboparkgauss",
        "parameters": {
            "A": "A",
        }
    },

    # Deflection model
    "jimenez": {
        "model_ref": "jimenez",
        "parameters": {
            "kd": "beta",
        }
    },
    "bastankhah2016_deflection": {
        "model_ref": "gauss",
        "parameters": {
            "alpha": "alpha",
            "beta": "beta",
            "ka": "ka",
            "kb": "kb",
        }
    },
}

basic_dict = {
    'name': 'Jensen-Jimenez',
    'description': 'Three turbines using Jensen / Jimenez models',
    'floris_version': 'v3.4.0',
    'logging': {
        'console': {'enable': True, 'level': 'WARNING'},
        'file': {'enable': False, 'level': 'WARNING'}
    },
    'solver': {
        'type': 'turbine_grid', 'turbine_grid_points': 3
    },
    'farm': {
        'layout_x': [0.0, 630.0, 1260.0],
        'layout_y': [0.0, 0.0, 0.0],
        'turbine_type': ['nrel_5MW']
    },
    'flow_field': {
        'air_density': 1.225,
        'reference_wind_height': -1,
        'turbulence_intensity': 0.06,
        'wind_directions': [270.0],
        'wind_shear': 0.12,
        'wind_speeds': [8.0],
        'wind_veer': 0.0
    },
    'wake': {
        'model_strings': {
            'combination_model': 'sosfs',
            'deflection_model': 'jimenez',
            'turbulence_model': 'crespo_hernandez',
            'velocity_model': 'jensen'
        },
        'enable_secondary_steering': False,
        'enable_yaw_added_recovery': False,
        'enable_transverse_velocities': False,
        'enable_active_wake_mixing': False,
        'wake_deflection_parameters': {
            'jimenez': {
                'ad': 0.0,
                'bd': 0.0,
                'kd': 0.05
            }
        },
        'wake_velocity_parameters': {
            'jensen': {
                'we': 0.05
            }
        },
        'wake_turbulence_parameters': {
            'crespo_hernandez': {
                'initial': 0.1,
                'constant': 0.5,
                'ai': 0.8,
                'downstream': -0.32
            }
        }
    }
}

class WCompFloris(WCompBase):

    """
    `WCompFloris` implements the wcomp interface to the FLORIS software.
    The connection points to FLORIS are shown in the diagram below.

    .. mermaid::

        classDiagram
            class FlorisInterface
            class WCompFloris {
                fi : FlorisInterface
                floris_dict : dict
                hub_height
                rotor_diameter
                yaw_angles : ndarray
                AEP()
                _create_floris_dict(windIO_wes_dict: dict)
            }

            WCompFloris --* FlorisInterface
    """
    LINE_PLOT_COLOR = "green"
    LINE_PLOT_MARKER = ""
    LINE_PLOT_LINESTYLE = "--"
    LINE_PLOT_LINEWIDTH = 2
    LEGEND = "FLORIS"

    def __init__(self, input_file: str | Path):

        input_dictionary = load_yaml(input_file)

        self.floris_dict = self._create_floris_dict(input_dictionary)
        self.fmodel = FlorisModel(self.floris_dict)

        n_findex = self.fmodel.core.flow_field.n_findex
        n_turbines = self.fmodel.core.farm.n_turbines
        yaw_angles = np.zeros((n_findex, n_turbines))
        yaw_angles[:] = input_dictionary["attributes"]["analyses"]["yaw_angles"]    # We need the extra dimension here to set the yaw angles for all findex. The current windIO inputs don't have the wind condition dimension so we apply the yaw setting to all.
        self.fmodel.set(yaw_angles=yaw_angles)
        self.fmodel.run()

    @property
    def rotor_diameter(self) -> float:
        return self.fmodel.core.farm.rotor_diameters[0,0]

    @property
    def hub_height(self) -> float:
        return self.fmodel.core.farm.hub_heights[0,0]

    ### Create the model from windIO

    def _create_floris_dict(self, wes):
        # "wes" is the wind energy system windIO file

        new_dict = copy.deepcopy(basic_dict)
        new_dict["name"] = wes["name"]
        new_dict["description"] = wes["name"]
        new_dict["floris_version"] = "v4"

        wes_wind_resource = wes["site"]["energy_resource"]["wind_resource"]
        new_dict["flow_field"] = {
            'air_density': 1.225,
            'reference_wind_height': -1,
            'turbulence_intensities': [wes_wind_resource["turbulence_intensity"]["data"]],
            'wind_directions': wes_wind_resource["wind_direction"],
            'wind_shear': 0.12,
            'wind_speeds': wes_wind_resource["wind_speed"],
            'wind_veer': 0.0
        }

        wes_turbine = wes["wind_farm"]["turbines"]

        new_turbine = {
            "turbine_type": wes_turbine["name"],
            "hub_height": wes_turbine["hub_height"],
            "rotor_diameter": wes_turbine["rotor_diameter"],
            "TSR": 8.0,         # Can we calculate this from diameter and power curve?
            "operation_model": "cosine-loss",
            "power_thrust_table": {
                "ref_air_density": 1.225,
                "ref_tilt": 5.0,
                "cosine_loss_exponent_yaw": 1.88,
                "cosine_loss_exponent_tilt": 1.88,
                # helix_a: 1.719
                # helix_power_b: 4.823e-03
                # helix_power_c: 2.314e-10
                # helix_thrust_b: 1.157e-03
                # helix_thrust_c: 1.167e-04
                "power": wes_turbine["performance"]["Cp_curve"]["Cp_values"],
                "thrust_coefficient": wes_turbine["performance"]["Ct_curve"]["Ct_values"],
                "wind_speed": wes_turbine["performance"]["Ct_curve"]["Ct_wind_speeds"]
            },
        }

        new_dict["farm"] = {
            "layout_x": wes["wind_farm"]["layouts"]["initial_layout"]["coordinates"]["x"],
            "layout_y": wes["wind_farm"]["layouts"]["initial_layout"]["coordinates"]["y"],
            'turbine_type': [new_turbine]
        }

        wes_analysis = wes["attributes"]["analyses"]
        _velocity_model_mapping = WAKE_MODEL_MAPPING[wes_analysis["wake_model"]["velocity"]["name"]]
        _velocity_model = _velocity_model_mapping["model_ref"]
        _velocity_model_parameters = {
            k: wes_analysis["wake_model"]["velocity"]["parameters"][v]
            for k, v in _velocity_model_mapping["parameters"].items()
        }
        if wes_analysis["wake_model"]["deflection"]["name"] is not None:
            _deflection_model_mapping = WAKE_MODEL_MAPPING[wes_analysis["wake_model"]["deflection"]["name"]]
            _deflection_model = _deflection_model_mapping["model_ref"]
            _deflection_model_parameters = {
                k: wes_analysis["wake_model"]["deflection"]["parameters"][v]
                for k, v in _deflection_model_mapping["parameters"].items()
            }
        else:
            _deflection_model = "none"
            _deflection_model_parameters = {}

        new_dict['wake'] = {
            'model_strings': {
                'combination_model': 'sosfs',
                'deflection_model': _deflection_model,
                'turbulence_model': 'crespo_hernandez',
                'velocity_model': _velocity_model
            },
            'enable_secondary_steering': False,
            'enable_yaw_added_recovery': False,
            'enable_transverse_velocities': False,
            'enable_active_wake_mixing': False,
            'wake_deflection_parameters': {_deflection_model: _deflection_model_parameters},
            'wake_velocity_parameters': {_velocity_model: _velocity_model_parameters},
            'wake_turbulence_parameters': {
                'crespo_hernandez': {
                    'initial': 0.1,
                    'constant': 0.5,
                    'ai': 0.8,
                    'downstream': -0.32
                }
            }
        }

        return new_dict

    ### Post processing

    def AEP(self):
        self.fmodel.get_farm_AEP()

    # 1D line plots

    def vertical_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        y_coordinate: float,
        zmax: float
    ) -> WakeProfile:

        findex = np.where(self.fmodel.core.flow_field.wind_directions == wind_direction)[0][0]
        cut_plane = self.fmodel.calculate_y_plane(
            crossstream_dist=y_coordinate,
            x_resolution=self.N_POINTS_1D,
            z_resolution=self.N_POINTS_1D,
            x_bounds=[x_coordinate, x_coordinate],
            z_bounds=[0, zmax],
            findex_for_viz=findex,
        )
        profile = WakeProfile(
            cut_plane.df.x2,
            cut_plane.df.u,
        )
        plot_profile(
            profile,
            # direction='x',
            # component='u',
            color=self.LINE_PLOT_COLOR,
            marker=self.LINE_PLOT_MARKER,
            linestyle=self.LINE_PLOT_LINESTYLE,
            linewidth=self.LINE_PLOT_LINEWIDTH,
            label=self.LEGEND
        )
        return profile

    def streamwise_profile_plot(
        self,
        wind_direction: float,
        y_coordinate: float,
        xmin: float,
        xmax: float
    ) -> WakeProfile:

        findex = np.where(self.fmodel.core.flow_field.wind_directions == wind_direction)[0][0]
        cut_plane = self.fmodel.calculate_y_plane(
            crossstream_dist=y_coordinate,
            x_resolution=self.N_POINTS_1D,
            z_resolution=self.N_POINTS_1D,
            x_bounds=[xmin, xmax],
            z_bounds=[self.hub_height, self.hub_height],
            findex_for_viz=findex,
        )
        profile = WakeProfile(
            cut_plane.df.x1,
            cut_plane.df.u,
        )
        plot_profile(
            profile,
            # direction='x',
            # component='u',
            color=self.LINE_PLOT_COLOR,
            marker=self.LINE_PLOT_MARKER,
            linestyle=self.LINE_PLOT_LINESTYLE,
            linewidth=self.LINE_PLOT_LINEWIDTH,
            label=self.LEGEND
        )
        return profile

    def xsection_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        ymin: float,
        ymax: float
    ) -> WakeProfile:

        findex = np.where(self.fmodel.core.flow_field.wind_directions == wind_direction)[0][0]
        cut_plane = self.fmodel.calculate_horizontal_plane(
            height=self.hub_height,
            # x_resolution=resolution[0],
            y_resolution=self.N_POINTS_1D,
            x_bounds=[x_coordinate, x_coordinate],
            y_bounds=[ymin, ymax],
            findex_for_viz=findex,
        )
        profile = WakeProfile(
            cut_plane.df.x2,
            cut_plane.df.u,
        )
        plot_profile(
            profile,
            # direction='y',
            # component='u',
            color=self.LINE_PLOT_COLOR,
            marker=self.LINE_PLOT_MARKER,
            linestyle=self.LINE_PLOT_LINESTYLE,
            linewidth=self.LINE_PLOT_LINEWIDTH,
            label=self.LEGEND
        )
        return profile

    # 2D contour plots

    def horizontal_contour(self, wind_direction: float) -> WakePlane:
        coordinates = np.array([
            (x, y, self.hub_height)
            for x, y in list(zip(self.fmodel.layout_x, self.fmodel.layout_y))
        ])
        _x, _y, _ = coordinates.T
        x_min = np.min(_x) - 2 * self.rotor_diameter
        x_max = np.max(_x) + 10 * self.rotor_diameter
        y_min = np.min(_y) - 2 * self.rotor_diameter
        y_max = np.max(_y) + 2 * self.rotor_diameter
        x, y = np.meshgrid(
            np.linspace(x_min, x_max, int((x_max - x_min) / self.RESOLUTION_2D) + 1),
            np.linspace(y_min, y_max, int((y_max - y_min) / self.RESOLUTION_2D) + 1),
            indexing='ij'
        )
        x = x.flatten()
        y = y.flatten()
        z = self.hub_height * np.ones_like(x)

        u = self.fmodel.sample_flow_at_points(x, y, z)[0]

        plane = WakePlane(x, y, u, "z")
        plot_plane(
            plane,
            # cmap='Blues_r',
            # color_bar=True,
            clevels=100
        )
        return plane

    def xsection_contour(self, wind_direction: float, x_coordinate: float) -> WakePlane:
        coordinates = np.array([
            (x, y, self.hub_height)
            for x, y in list(zip(self.fmodel.layout_x, self.fmodel.layout_y))
        ])
        _, _y, _z = coordinates.T
        y_min = np.min(_y) - 2 * self.rotor_diameter
        y_max = np.max(_y) + 2 * self.rotor_diameter
        z_min = 0.001
        z_max = 6 * self.hub_height
        y, z = np.meshgrid(
            np.linspace(y_min, y_max, int((y_max - y_min) / self.RESOLUTION_2D) + 1),
            np.linspace(z_min, z_max, int((z_max - z_min) / self.RESOLUTION_2D) + 1),
            indexing='ij'
        )
        y = y.flatten()
        z = z.flatten()
        x = x_coordinate * np.ones_like(y)

        u = self.fmodel.sample_flow_at_points(x, y, z)[0]

        plane = WakePlane(y, z, u, "x")
        plot_plane(
            plane,
            # cmap='Blues_r',
            # color_bar=True,
            clevels=100
        )
        return plane
