
import matplotlib
import matplotlib.pyplot as plt

from .output_struct import WakePlane, WakeProfile

# Method to add plots to an axis
# plot_1d(ax, series)

def plot_profile(
    wake_profile: WakeProfile,
    ax=None,
    # direction='x',
    # component='u',
    title="",
    **kwargs
):
    if not ax:
        fig, ax = plt.subplots()

    ax.plot(
        wake_profile.x1,
        wake_profile.values,
        # ls= '--',
        **kwargs
    )

def plot_plane(
    wake_plane: WakePlane,
    ax: matplotlib.axes.Axes = None,
    min_speed: float = None,
    max_speed: float = None,
    cmap: str = "coolwarm",
    clevels: int = None,
    color_bar: bool = False,
    title: str = None,
    **kwargs
) -> None:
    """
    Plot the data in a WakePlane object on a 2D contour plot.

    Args:
        wake_plane (WakePlane): Data structure containing the sample data on a plane.
        ax (matplotlib.axes.Axes, optional): matplotlib Axes to place the plot. Defaults to None.
            If None, a new figure and axes are created.
        min_speed (float, optional): Minimum value of wind speed for the contour plot color range.
            Defaults to None. If None, the minimum value in the data is used.
        max_speed (float, optional): Maximum value of wind speed for the contour plot color range.
            Defaults to None. If None, the maximum value in the data is used.
        cmap (str, optional): Colormap name from
            https://matplotlib.org/stable/users/explain/colors/colormaps.html.
            Defaults to "coolwarm".
        clevels (int or array-like, optional):
            From the matplotlib documentation:
            Determines the number and positions of the contour lines / regions.
            If an int n, use MaxNLocator, which tries to automatically choose no more than n+1
            "nice" contour levels between between minimum and maximum numeric values of Z.
            If array-like, draw contour lines at the specified levels.
            The values must be in increasing order.
            Reference: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tricontourf.html.
            Defaults to None.
        color_bar (bool, optional): Flag to enable displaying a color bar for this Axes.
            Defaults to False.
        title (str, optional): Title for this Axes. Defaults to None.
        kwargs: Additional parameters passed to pyplot.tricontourf.
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tricontourf.html
            for available parameters.
    """

    if not ax:
        fig, ax = plt.subplots()

    if title:
        ax.set_title(title)

    im = ax.tricontourf(
        wake_plane.x1,
        wake_plane.x2,
        wake_plane.values,
        vmin=min_speed,
        vmax=max_speed,
        levels=clevels,
        cmap=cmap,
        extend="neither",
        # norm=colors.CenteredNorm()
        **kwargs
    )

    if wake_plane.normal_vector == "x":
        ax.invert_xaxis()

    if color_bar:
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('m/s')

    # Make equal axis
    ax.set_aspect("equal")
