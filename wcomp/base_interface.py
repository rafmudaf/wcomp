
from abc import ABC
from pathlib import Path

from .output_struct import WakePlane


class WCompBase(ABC):
    """
    WCompBase is an abstract base class that defines the interfaces required
    to conform to the wcomp framework. This class cannot be used directly. Instead,
    it should be used to create a subclass, and all attributes and functions
    described here should be implemented in the subclass.
    """

    LINE_PLOT_COLOR = "OVERWRITE"   # Color to use for all line plots; use matplotlib color codes
    LEGEND = "OVERWRITE"            # Legend entry; typically should be the name of the corresponding software

    def __init__(self, input_file: str | Path):
        """
        The initialization for all subclasses must create the results from the
        corresponding software, so that they are ready for post processing in
        the other functions of this class. This typically consists of at least
        the following:
        1. Load the windIO input file describing the case
        2. Initialize all required data for the corresponding model
        3. Complete all calculations defined by the windIO case definition

        Args:
            input_file (str | Path): Path to windIO case input file
        """
        raise NotImplementedError("WCompBase.__init__")

    @property
    def rotor_diameter(self) -> float:
        """
        Stores a characteristic rotor diameter for use throughout the
        post processing and plotting functions.

        Returns:
            float: Characteristic rotor diameter
        """
        raise NotImplementedError("WCompBase.rotor_diameter")

    @property
    def hub_height(self) -> float:
        """
        Stores a characteristic hub height for use throughout the
        post processing and plotting functions.

        Returns:
            float: Characteristic hub height
        """
        raise NotImplementedError("WCompBase.hub_height")

    ### Post processing

    def AEP(self) -> float:
        """
        Computes the annual energy production (AEP) for the current case.
        This is typically implemented in the corresponding software, so
        it should not be computed here. 

        Returns:
            float: Annual energy production (AEP) for the current case
                in megawatts-hours (MWh).
        """
        raise NotImplementedError("WCompBase.AEP")

    # 1D line plots

    def vertical_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        y_coordinate: float,
        zmax: float
    ):
        """
        This function produces a 1D plot of the velocity profile in the z-x plane
        where z is normal to the ground and x is streamwise.

        Args:
            wind_direction (float): Wind direction to align the plot in the visualization in
                degrees with West being 270 degrees and North being 0 degrees
            y_coordinate (float): The lateral location to extract the plotted values
        """
        raise NotImplementedError("WCompBase.vertical_profile_plot")

    def streamwise_profile_plot(
        self,
        wind_direction: float,
        y_coordinate: float,
        xmin: float,
        xmax: float
    ):
        """
        This function produces a 1D plot of the velocity profile in the z-x plane
        where z is normal to the ground and x is streamwise.

        Args:
            wind_direction (float): Wind direction to align the plot in the visualization in
                degrees with West being 270 degrees and North being 0 degrees
            y_coordinate (float): The lateral location to extract the plotted values
            xmin (float): The lower bound of the plot in the streamwise direction
            xmax (float): The upper bound of the plot in the streamwise direction
        """
        raise NotImplementedError("WCompBase.streamwise_profile_plot")

    def xsection_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        ymin: float,
        ymax: float
    ):
        """
        This function produces a 1D plot of the velocity profile in the y-z plane
        where z is normal to the ground and y is normal to z and the streamwise direction.

        Args:
            wind_direction (float): Wind direction to align the plot in the visualization in
                degrees with West being 270 degrees and North being 0 degrees
            x_coordinate (float): The streamwise location to extract the plotted values
            ymin (float): The lower bound of the plot in the lateral direction
            ymax (float): The upper bound of the plot in the lateral direction
        """
        raise NotImplementedError("WCompBase.xsection_profile_plot")

    # 2D contour plots

    def horizontal_contour(
        self,
        wind_direction: float,
        resolution: tuple
    ) -> WakePlane:
        """
        This function produces a contour plot of the velocity in the x-y plane
        parallel to the ground. The contour is located at the hub height obtained
        by the interface's `hub_height` property (`self.hub_height`).

        Args:
            wind_direction (float): Wind direction to align the plot in the visualization in
                degrees with West being 270 degrees and North being 0 degrees
            resolution (tuple): Grid resolution for the contour plot;
                element 0 is the resolution in x and element 1 is the resolution in y

        Returns:
            WakePlane
        """
        raise NotImplementedError("WCompBase.horizontal_contour")

    def xsection_contour(
        self,
        wind_direction: float,
        resolution: tuple,
        x_coordinate: float
    ) -> WakePlane:
        """
        This function produces a contour plot of the velocity in the y-z plane
        perpendicular to the wind direction.

        Args:
            wind_direction (float): Wind direction to align the plot in the visualization in
                degrees with West being 270 degrees and North being 0 degrees
            resolution (tuple): Grid resolution for the contour plot;
                element 0 is the resolution in y and element 1 is the resolution in z
            x_coordinate (float): The streamwise location for the extracted plane

        Returns:
            WakePlane
        """
        raise NotImplementedError("WCompBase.xsection_contour")
