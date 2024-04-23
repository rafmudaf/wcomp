
from abc import ABC
from pathlib import Path
from typing import Any

from .output_struct import WakeProfile, WakePlane


class WCompBase(ABC):
    """
    WCompBase is an abstract base class that defines the interfaces required
    to conform to the `wcomp` framework. This class cannot be used directly. Instead,
    it should be used to create a subclass, and all attributes and functions
    described here should be implemented in the subclass. See function docstrings
    for implementation details.
    """

    LINE_PLOT_COLOR = "OVERWRITE"   # Color to use for all line plots; use matplotlib color codes
    LINE_PLOT_MARKER = ""           # Marker to use for all line plots; use matplotlib marker codes
    LINE_PLOT_LINESTYLE = "--"      # Line style to use for all line plots; use matplotlib line style codes
    LINE_PLOT_LINEWIDTH = 2         # Line width to use for all line plots
    LEGEND = "OVERWRITE"            # Legend entry; typically should be the name of the corresponding software

    # These generally do not need to be changed in the subclass
    N_POINTS_1D = 100               # Number of points to use for 1D line plots
    RESOLUTION_2D = 10              # Resolution for 2D contour plots in meters

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
            input_file (str | Path): Path to a windIO case input file

        Raises:
            NotImplementedError: This function must be implemented in a subclass
        """
        raise NotImplementedError("WCompBase.__init__")

    @property
    def rotor_diameter(self) -> float:
        """
        Virtual property to get the characteristic rotor diameter for use throughout the
        post processing and plotting functions. While every turbine may not have the same
        rotor diameter, one should be chosen as a reference value to set relative distances.

        Raises:
            NotImplementedError: This function must be implemented in a subclass

        Returns:
            float: Characteristic rotor diameter
        """
        raise NotImplementedError("WCompBase.rotor_diameter")

    @property
    def hub_height(self) -> float:
        """
        Virtual property to get the characteristic hub height for use throughout the
        post processing and plotting functions. While every turbine may not have the same
        hub height, one should be chosen as a reference value to set relative distances.

        Raises:
            NotImplementedError: This function must be implemented in a subclass

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

        Raises:
            NotImplementedError: This function must be implemented in a subclass

        Returns:
            float: Annual energy production (AEP) for the current case in megawatts-hours (MWh).
        """
        raise NotImplementedError("WCompBase.AEP")

    # 1D line plots

    def vertical_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        y_coordinate: float,
        zmax: float
    ) -> WakeProfile:
        """
        This function produces a 1D plot of the velocity profile in the z-x plane
        where z is normal to the ground and x is streamwise. A sample line is produced
        from the ground to the height `zmax` at the location (`x_coordinate`, `y_coordinate`)
        to sample the velocities.

        To implement this function, the subclass should produce a line of the u-component of
        velocities at the specified location and height. The {py:class}`wcomp.plotting.WakeProfile`
        class should be used to store the data. Then, the {py:meth}`wcomp.plotting.plot_profile`
        function should be used to produce the plot. A sample implementation is shown below.

        Args:
            wind_direction (float): Incoming wind direction in degrees with West at 270 degrees.
            x_coordinate (float): X-coordinate of the line to sample.
            y_coordinate (float): Y-coordinate of the line to sample.
            zmax (float): The end-point of the sample line in the vertical direction.
                The line starts at the ground.

        Raises:
            NotImplementedError: This function must be implemented in a subclass

        Returns:
            WakeProfile: The profile of wake data

        Example:
            .. code-block:: python

                # Call the wake model to produce the velocities at the sample line
                u, v, w = wake_model(...)           # Note v and w are not used
                x, y, z = wake_model.get_points()   # Get the coordinates of the sample points

                # Create a WakeProfile object to store the data
                profile = WakeProfile(z, u)

                # Plot the profile
                plot_profile(
                    profile,
                    color=self.LINE_PLOT_COLOR,
                    marker=self.LINE_PLOT_MARKER,
                    linestyle=self.LINE_PLOT_LINESTYLE,
                    label=self.LEGEND
                )

                return profile
        """
        raise NotImplementedError("WCompBase.vertical_profile_plot")

    def streamwise_profile_plot(
        self,
        wind_direction: float,
        y_coordinate: float,
        xmin: float,
        xmax: float
    ) -> WakeProfile:
        """
        This function produces a 1D plot of the velocity profile in the z-x plane
        where z is normal to the ground and x is streamwise. A sample line is produced
        from `xmin` to `xmax` at the hub height and `y_coordinate` to sample the velocities.

        To implement this function, the subclass should produce a line of the u-component of
        velocities at the specified location and height. The {py:class}`wcomp.plotting.WakeProfile`
        class should be used to store the data. Then, the {py:meth}`wcomp.plotting.plot_profile`
        function should be used to produce the plot. A sample implementation is shown below.

        Args:
            wind_direction (float): Incoming wind direction in degrees with West at 270 degrees.
            y_coordinate (float): Y-coordinate of the line to sample.
            xmin (float): Starting point of the sample line in the streamwise direction.
            xmax (float): End point of the sample line in the streamwise direction.

        Raises:
            NotImplementedError: This function must be implemented in a subclass

        Returns:
            WakeProfile: The profile of wake data

        Example:
            .. code-block:: python

                # Call the wake model to produce the velocities at the sample line
                u, v, w = wake_model(...)           # Note v and w are not used
                x, y, z = wake_model.get_points()   # Get the coordinates of the sample points

                # Create a WakeProfile object to store the data
                profile = WakeProfile(x, u)

                # Plot the profile
                plot_profile(
                    profile,
                    color=self.LINE_PLOT_COLOR,
                    marker=self.LINE_PLOT_MARKER,
                    linestyle=self.LINE_PLOT_LINESTYLE,
                    label=self.LEGEND
                )

                return profile
        """
        raise NotImplementedError("WCompBase.streamwise_profile_plot")

    def xsection_profile_plot(
        self,
        wind_direction: float,
        x_coordinate: float,
        ymin: float,
        ymax: float
    ) -> WakeProfile:
        """
        This function produces a 1D plot of the velocity profile in the y-z plane
        where z is normal to the ground and y is normal to z and the streamwise direction.
        A sample line is produced from `ymin` to `ymax` at the hub height and `x_coordinate`
        to sample the velocities.

        To implement this function, the subclass should produce a line of the u-component of
        velocities at the specified location and height. The {py:class}`wcomp.plotting.WakeProfile`
        class should be used to store the data. Then, the {py:meth}`wcomp.plotting.plot_profile`
        function should be used to produce the plot. A sample implementation is shown below.

        Args:
            wind_direction (float): Incoming wind direction in degrees with West at 270 degrees.
            x_coordinate (float): X-coordinate of the line to sample.
            ymin (float): Starting point of the sample line in the lateral direction.
            ymax (float): End point of the sample line in the lateral direction.

        Raises:
            NotImplementedError: This function must be implemented in a subclass

        Returns:
            WakeProfile: The profile of wake data

        Example:
            .. code-block:: python

                # Call the wake model to produce the velocities at the sample line
                u, v, w = wake_model(...)           # Note v and w are not used
                x, y, z = wake_model.get_points()   # Get the coordinates of the sample points

                # Create a WakeProfile object to store the data
                profile = WakeProfile(y, u)

                # Plot the profile
                plot_profile(
                    profile,
                    color=self.LINE_PLOT_COLOR,
                    marker=self.LINE_PLOT_MARKER,
                    linestyle=self.LINE_PLOT_LINESTYLE,
                    label=self.LEGEND
                )

                return profile
        """
        raise NotImplementedError("WCompBase.xsection_profile_plot")

    # 2D contour plots

    def horizontal_contour(self, wind_direction: float) -> WakePlane:
        """
        This function produces a contour plot of the velocity in the x-y plane where
        x is streamwise and y is lateral. The contour is located at the hub height.
        The extent of the sample plane should be:

        - x min: 2 rotor diameters upstream of the most upstream turbine
        - x max: 10 rotor diameters downstream of the most downstream turbine
        - y min,max: 2 rotor diameters outside the most lateral turbines

        To implement this function, the subclass should produce a plane of the u-component of
        velocities with the required bounds. The {py:class}`wcomp.plotting.WakePlane`
        class should be used to store the data. Then, the {py:meth}`wcomp.plotting.plot_plane`
        function should be used to produce the plot. A sample implementation is shown below.

        Args:
            wind_direction (float): Incoming wind direction in degrees with West at 270 degrees.

        Raises:
            NotImplementedError: This function must be implemented in a subclass

        Returns:
            WakePlane: The plane of wake data

        Example:
            .. code-block:: python

                # Call the wake model to produce the velocities at the sample line
                u, v, w = wake_model(...)           # Note v and w are not used
                x, y, z = wake_model.get_points()   # Get the coordinates of the sample points

                # Create a WakePlane object to store the data
                plane = WakePlane(
                    x,      # If 2d array, use x.flatten()
                    y,      # ^ ^ ^
                    u,
                    "z",
                )

                # Plot the plane
                plot_plane(
                    plane,
                    color=self.LINE_PLOT_COLOR,
                    marker=self.LINE_PLOT_MARKER,
                    linestyle=self.LINE_PLOT_LINESTYLE,
                    label=self.LEGEND
                )

                return plane
        """
        raise NotImplementedError("WCompBase.horizontal_contour")

    def xsection_contour(self, wind_direction: float, x_coordinate: float) -> WakePlane:
        """
        This function produces a contour plot of the velocity in the y-z plane where
        y is lateral and z is vertical. The contour is located in the streamwise direction at the
        given `x_coordinate`. The extent of the sample plane should be:

        - y min,max: 2 rotor diameters outside the most lateral turbines
        - z min: z=0.0
        - z max: 6 * hub height

        To implement this function, the subclass should produce a plane of the u-component of
        velocities with the required bounds. The {py:class}`wcomp.plotting.WakePlane`
        class should be used to store the data. Then, the {py:meth}`wcomp.plotting.plot_plane`
        function should be used to produce the plot. A sample implementation is shown below.

        Args:
            wind_direction (float): Wind direction to align the plot in the visualization in
                degrees with West being 270 degrees and North being 0 degrees
            x_coordinate (float): The streamwise location for the extracted plane

        Raises:
            NotImplementedError: This function must be implemented in a subclass

        Returns:
            WakePlane: The plane of wake data

        Example:
            .. code-block:: python

                # Call the wake model to produce the velocities at the sample line
                u, v, w = wake_model(...)           # Note v and w are not used
                x, y, z = wake_model.get_points()   # Get the coordinates of the sample points

                # Create a WakePlane object to store the data
                plane = WakePlane(
                    y,      # If 2d array, use x.flatten()
                    z,      # ^ ^ ^
                    u,
                    "x",
                )

                # Plot the plane
                plot_plane(
                    plane,
                    color=self.LINE_PLOT_COLOR,
                    marker=self.LINE_PLOT_MARKER,
                    linestyle=self.LINE_PLOT_LINESTYLE,
                    label=self.LEGEND
                )

                return plane
        """
        raise NotImplementedError("WCompBase.xsection_contour")
