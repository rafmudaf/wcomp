
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
    ax=None,
    min_speed=None,
    max_speed=None,
    cmap="coolwarm",
    levels=None,
    clevels=None,
    color_bar=False,
    **kwargs
):
    """
    Generate pseudocolor mesh plot of the cut_plane.

    Args:
        cut_plane (:py:class:`~.tools.cut_plane.CutPlane`): 2D
            plane through wind plant.
        ax (:py:class:`matplotlib.pyplot.axes`, optional): Figure axes. Defaults
            to None.
        vel_component (str, optional): The velocity component that the cut plane is
            perpendicular to.
        min_speed (float, optional): Minimum value of wind speed for
            contours. Defaults to None.
        max_speed (float, optional): Maximum value of wind speed for
            contours. Defaults to None.
        cmap (str, optional): Colormap specifier. Defaults to
            'coolwarm'.
        levels (np.array, optional): Contour levels for line contour plot.
            Defaults to None.
        clevels (np.array, optional): Contour levels for tricontourf plot.
            Defaults to None.
        color_bar (Boolean, optional): Flag to include a color bar on the plot.
            Defaults to False.
        title (str, optional): User-supplied title for the plot. Defaults to "".
        **kwargs: Additional parameters to pass to line contour plot.

    Returns:
        im (:py:class:`matplotlib.plt.pcolormesh`): Image handle.
    """

    if not ax:
        fig, ax = plt.subplots()

    # Allow separate number of levels for tricontourf and for line_contour
    if clevels is None:
        clevels = levels

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
    )

    if wake_plane.normal_vector == "x":
        ax.invert_xaxis()

    if color_bar:
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('m/s')

    # Make equal axis
    ax.set_aspect("equal")

    return im
