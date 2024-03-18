
import copy
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from floris.tools import FlorisInterface
from windIO.utils.yml_utils import load_yaml

from .base_interface import WCompBase
from .output_struct import WakePlane, WakeProfile
from .plotting import plot_plane, plot_profile

# This dictionary maps generic model names in the windIO input file
# to the tool's specific name. It also maps parameter names from the
# referenced papers to the parameters in the implementation.
# "windIO_model_name": {
#   "model_ref": the current software's reference for this wake model,
#   "parameters": {
#       "windIO_parameter": current software's analogous parameter
#   }
# }
# WAKE_MODEL_MAPPING = {
#     "jensen": {
#         "model_ref": "jensen",
#         "parameters": {
#             "alpha": "we",
#         }
#     },    
# }

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
        'enable_secondary_steering': True,
        'enable_yaw_added_recovery': True,
        'enable_transverse_velocities': True,
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
    """
    LINE_PLOT_COLOR = "green"
    LINE_PLOT_MARKER = ""
    LINE_PLOT_LINESTYLE = "--"
    LEGEND = "Floris"

    def __init__(
        self,
        input_file: str | Path,
        velocity_deficit: str,
        velocity_deficit_p: dict,
        deflection: str = "none",
        deflection_p: dict = None,
        yaw_angles = [0.0],
    ):
        input_dictionary = load_yaml(input_file)

        self.velocity_deficit_model_string = velocity_deficit
        self.velocity_deficit_parameters = velocity_deficit_p
        self.deflection_model_string = deflection
        self.deflection_parameters = deflection_p

        self.floris_dict = self._create_floris_dict(input_dictionary)
        self.fi = FlorisInterface(self.floris_dict)

        self.yaw_angles = np.array([[yaw_angles]])
        self.fi.calculate_wake(yaw_angles=self.yaw_angles)

    @property
    def rotor_diameter(self) -> float:
        return self.fi.floris.farm.rotor_diameters[0,0,0]

    @property
    def hub_height(self) -> float:
        return self.fi.floris.farm.hub_heights[0,0,0]

    ### Create the model from windIO

    def _create_floris_dict(self, wes):
        # "wes" is the wind energy system windIO file

        new_dict = copy.deepcopy(basic_dict)
        new_dict["name"] = wes["name"]
        new_dict["description"] = wes["name"]
        new_dict["floris_version"] = "v3.4.0"

        wes_wind_resource = wes["site"]["energy_resource"]["wind_resource"]
        new_dict["flow_field"] = {
            'air_density': 1.225,
            'reference_wind_height': -1,
            'turbulence_intensity': wes_wind_resource["turbulence_intensity"]["data"],
            'wind_directions': wes_wind_resource["wind_direction"],
            'wind_shear': 0.12,
            'wind_speeds': wes_wind_resource["wind_speed"],
            'wind_veer': 0.0
        }

        wes_turbine = wes["wind_farm"]["turbines"]

        new_turbine = {
            "turbine_type": wes_turbine["name"],
            "generator_efficiency": 1.0,
            "hub_height": wes_turbine["hub_height"],
            "pP": 1.88,
            "pT": 1.88,         # How to set these?
            "rotor_diameter": wes_turbine["rotor_diameter"],
            "TSR": 8.0,         # Can we calculate this from diameter and power curve?
            "ref_density_cp_ct": 1.225,
            "ref_tilt_cp_ct": 0.0,       # Set to 0
            "power_thrust_table": {
                "power": wes_turbine["performance"]["Cp_curve"]["Cp_values"],
                "thrust": wes_turbine["performance"]["Ct_curve"]["Ct_values"],
                "wind_speed": wes_turbine["performance"]["Ct_curve"]["Ct_wind_speeds"]
            }
        }

        new_dict["farm"] = {
            "layout_x": wes["wind_farm"]["layouts"]["initial_layout"]["coordinates"]["x"],
            "layout_y": wes["wind_farm"]["layouts"]["initial_layout"]["coordinates"]["y"],
            'turbine_type': [new_turbine]
        }

        if self.deflection_parameters is not None:
            _deflection_parameters = {**self.deflection_parameters}
        else:
            _deflection_parameters = {}

        new_dict['wake'] = {
            'model_strings': {
                'combination_model': 'sosfs',
                'deflection_model': self.deflection_model_string,
                'turbulence_model': 'crespo_hernandez',
                'velocity_model': self.velocity_deficit_model_string
            },
            'enable_secondary_steering': False,
            'enable_yaw_added_recovery': False,
            'enable_transverse_velocities': False,
            'wake_deflection_parameters': { 
                self.deflection_model_string: _deflection_parameters
            },
            'wake_velocity_parameters': {
                self.velocity_deficit_model_string: {
                    **self.velocity_deficit_parameters
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

        return new_dict

    ### Post processing

    def AEP(self):
        self.fi.get_farm_AEP()

    # 1D line plots

    def vertical_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        y_coordinate: float,
        zmax: float
    ):
        """
        Creates the plot figures via matplotlib, but it does not show them.
        This requires plt.show() to be called when appropriate.

        Args:
            wind_direction (float): The wind direction to use for the visualization
            resolution (tuple): The (x, y) resolution of the horizontal plane
        """
        ax = plt.gca()

        cut_plane = self.fi.calculate_y_plane(
            crossstream_dist=y_coordinate,
            wd=[wind_direction],
            x_resolution=20,
            z_resolution=20,
            x_bounds=[x_coordinate, x_coordinate],
            z_bounds=[0, zmax],
            yaw_angles=self.yaw_angles,
        )
        profile = WakeProfile(
            cut_plane.df.x2,
            cut_plane.df.u,
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

    def streamwise_profile_plot(
        self,
        wind_direction: float,
        y_coordinate: float,
        xmin: float,
        xmax: float
    ):
        """
        Creates the plot figures via matplotlib, but it does not show them.
        This requires plt.show() to be called when appropriate.

        Args:
            wind_direction (float): The wind direction to use for the visualization
            resolution (tuple): The (x, y) resolution of the horizontal plane
        """
        ax = plt.gca()

        cut_plane = self.fi.calculate_y_plane(
            crossstream_dist=y_coordinate,
            wd=[wind_direction],
            x_resolution=50,
            z_resolution=50,
            x_bounds=[xmin, xmax],
            z_bounds=[self.hub_height, self.hub_height],
            yaw_angles=self.yaw_angles,
        )
        profile = WakeProfile(
            cut_plane.df.x1,
            cut_plane.df.u,
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

        cut_plane = self.fi.calculate_horizontal_plane(
            height=self.hub_height,
            wd=[wind_direction],
            # x_resolution=resolution[0],
            y_resolution=20,
            x_bounds=[x_coordinate, x_coordinate],
            y_bounds=[ymin, ymax],
            yaw_angles=self.yaw_angles,
        )
        profile = WakeProfile(
            cut_plane.df.x2,
            cut_plane.df.u,
        )
        plot_profile(
            profile,
            ax=ax,
            # direction='y',
            # component='u',
            color=self.LINE_PLOT_COLOR,
            marker=self.LINE_PLOT_MARKER,
            linestyle=self.LINE_PLOT_LINESTYLE,
            label=self.LEGEND
        )

    # 2D contour plots

    def horizontal_contour(
        self,
        wind_direction: float,
        resolution: tuple,
    ) -> WakePlane:
        """
        Creates the plot figures via matplotlib, but it does not show them.
        This requires plt.show() to be called when appropriate.
        NOTE:
        - The height of the plane is the hub height of the first wind turbine.
        If there are different hub heights, handle this appropriately.

        Args:
            wind_direction (float): The wind direction to use for the visualization
            resolution (tuple): The (x, y) resolution of the horizontal plane
        """
        # fig, axarr = plt.subplots(1, 1)
        cut_plane = self.fi.calculate_horizontal_plane(
            height=self.hub_height,
            wd=[wind_direction],
            x_resolution=resolution[0],
            y_resolution=resolution[1],
            yaw_angles=self.yaw_angles,
        )
        # print("FLORIS bounds")
        # print(min(cut_plane.df.x1), max(cut_plane.df.x1))
        # print(min(cut_plane.df.x2), max(cut_plane.df.x2))
        plane = WakePlane(
            cut_plane.df.x1,
            cut_plane.df.x2,
            cut_plane.df.u,
            cut_plane.normal_vector,
            cut_plane.resolution
        )
        plot_plane(
            plane,
            ax=plt.gca(), #axarr,
            # cmap='Blues_r',
            # color_bar=True,
            clevels=100
        )
        return plane

    def xsection_contour(
        self,
        wind_direction: float,
        resolution: tuple,
        x_coordinate: float
    ) -> WakePlane:
        """
        Creates the plot figures via matplotlib, but it does not show them.
        This requires plt.show() to be called when appropriate.
        NOTE:
        - The height of the plane is the hub height of the first wind turbine.
        If there are different hub heights, handle this appropriately.

        Args:
            wind_direction (float): The wind direction to use for the visualization
            resolution (tuple): The (x, y) resolution of the horizontal plane
        """
        cut_plane = self.fi.calculate_cross_plane(
            downstream_dist=x_coordinate,
            wd=[wind_direction],
            y_resolution=resolution[0],
            z_resolution=resolution[1],
            yaw_angles=self.yaw_angles,
        )
        plane = WakePlane(
            cut_plane.df.x1,
            cut_plane.df.x2,
            cut_plane.df.u,
            cut_plane.normal_vector,
            cut_plane.resolution
        )
        plot_plane(
            plane,
            ax=plt.gca(),
            color_bar=True,
            clevels=100
        )
        return plane