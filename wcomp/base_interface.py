
from abc import ABC
from pathlib import Path

from windIO.utils.yml_utils import load_yaml

from .output_struct import WakePlane


class WCompBase(ABC):

    LPLOT_COLOR = "OVERWRITE"
    LEGEND = "OVERWRITE"

    def __init__(self, input_file: str | Path):
        input_dictionary = load_yaml(input_file)

    @property
    def rotor_diameter(self) -> float:
        pass

    @property
    def hub_height(self) -> float:
        pass

    ### Post processing

    def AEP(self) -> float:
        pass

    # 1D line plots

    def vertical_profile_plot(self, wind_direction: float, y_coordinate: float, xmin: float, xmax: float):
        pass

    def xsection_profile_plot(self, wind_direction: float, x_coordinate: float, ymin: float, ymax: float):
        pass

    # 2D contour plots

    def horizontal_contour(self, wind_direction: float, resolution: tuple) -> WakePlane:
        pass

    def xsection_contour(self, wind_direction: float, resolution: tuple, x_coordinate: float) -> WakePlane:
        pass
