
import base64
from io import BytesIO
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .output_struct import WakePlane, WakeProfile

if TYPE_CHECKING:
    import IPython

# Default per-software colors shared by the interactive dashboard plots
DASHBOARD_COLORS = {
    "FLORIS": "#2ca02c",
    "FOXES": "#d62728",
    "PyWake": "#1f77b4",
}


def plot_profile(
    wake_profile: WakeProfile,
    # direction='x',
    # component='u',
    title="",
    **kwargs
):
    if len(plt.get_fignums()) == 0:
        fig, ax = plt.subplots()
    else:
        ax = plt.gca()

    ax.plot(
        wake_profile.x1,
        wake_profile.values,
        # ls= '--',
        **kwargs
    )

def plot_plane(
    wake_plane: WakePlane,
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
    if len(plt.get_fignums()) == 0:
        fig, ax = plt.subplots()
    else:
        ax = plt.gca()

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


def compare_profiles_plotly(
    profiles: dict[str, WakeProfile],
    xlabel: str = "",
    ylabel: str = "U (m/s)",
    title: str = "",
    show_diff: bool = True,
    colors: dict[str, str] = None,
) -> go.Figure:
    """
    Build an interactive Plotly figure comparing the same 1D wake profile
    computed by multiple software packages, including traces for the absolute
    difference between consecutive software results.

    Args:
        profiles (dict[str, WakeProfile]): Mapping of software name (e.g. "FLORIS")
            to its computed WakeProfile for one comparison location.
        xlabel (str, optional): X-axis label. Defaults to "".
        ylabel (str, optional): Y-axis label. Defaults to "U (m/s)".
        title (str, optional): Figure title. Defaults to "".
        show_diff (bool, optional): If True, add a trace for the absolute
            difference between each consecutive pair of software results.
            Defaults to True.
        colors (dict[str, str], optional): Mapping of software name to a plotly
            color string. Defaults to `DASHBOARD_COLORS`.

    Returns:
        plotly.graph_objects.Figure: Interactive comparison figure. Traces can be
            toggled on/off via the legend and hovered for exact values.
    """
    colors = colors or DASHBOARD_COLORS
    names = list(profiles.keys())

    fig = go.Figure()
    for name in names:
        profile = profiles[name]
        fig.add_trace(go.Scatter(
            x=np.asarray(profile.x1),
            y=np.asarray(profile.values),
            mode="lines",
            name=name,
            line=dict(color=colors.get(name), width=2),
        ))

    if show_diff and len(names) > 1:
        for a, b in zip(names[:-1], names[1:]):
            diff = profiles[a] - profiles[b]
            fig.add_trace(go.Scatter(
                x=np.asarray(diff.x1),
                y=np.abs(np.asarray(diff.values)),
                mode="lines",
                name=f"|{a} - {b}|",
                line=dict(color="#888888", width=1.5, dash="dot"),
            ))

    fig.update_layout(
        title=title,
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(t=50, b=40, l=60, r=160),
        height=380,
    )
    return fig


def compare_xsections_plotly(
    xsections: dict[str, dict[str, WakeProfile]],
    xlabel: str = "Y (m)",
    ylabel: str = "U (m/s)",
    title: str = "",
    colors: dict[str, str] = None,
    ymin: float = None,
    ymax: float = None,
) -> go.Figure:
    """
    Build an interactive Plotly figure comparing cross-section wake profiles
    computed by multiple software packages at several downstream locations.

    Args:
        xsections (dict[str, dict[str, WakeProfile]]): Mapping of a downstream
            location label (e.g. "5 D", used verbatim as the subplot title) to a
            mapping of software name to its computed WakeProfile at that location.
        xlabel (str, optional): X-axis label. Defaults to "Y (m)".
        ylabel (str, optional): Y-axis label. Defaults to "U (m/s)".
        title (str, optional): Figure title. Defaults to "".
        colors (dict[str, str], optional): Mapping of software name to a plotly
            color string. Defaults to `DASHBOARD_COLORS`.
        ymin (float, optional): Fixed lower bound applied to every subplot's y-axis, so
            cross-sections are comparable across downstream locations and wake models.
            Defaults to None (auto-scaled per subplot).
        ymax (float, optional): Fixed upper bound applied to every subplot's y-axis. See
            `ymin`. Defaults to None (auto-scaled per subplot).

    Returns:
        plotly.graph_objects.Figure: Figure with one row per downstream location,
            sharing a single, de-duplicated legend.
    """
    colors = colors or DASHBOARD_COLORS
    locations = list(xsections.keys())
    yrange = [ymin, ymax] if ymin is not None and ymax is not None else None

    fig = make_subplots(
        rows=len(locations),
        cols=1,
        shared_xaxes=True,
        subplot_titles=locations,
        vertical_spacing=0.08,
    )

    seen_legend_names = set()
    for row, location in enumerate(locations, start=1):
        for name, profile in xsections[location].items():
            fig.add_trace(
                go.Scatter(
                    x=np.asarray(profile.x1),
                    y=np.asarray(profile.values),
                    mode="lines",
                    name=name,
                    legendgroup=name,
                    showlegend=name not in seen_legend_names,
                    line=dict(color=colors.get(name), width=2),
                ),
                row=row,
                col=1,
            )
            seen_legend_names.add(name)

    fig.update_layout(
        title=title,
        template="plotly_white",
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(t=50, b=40, l=60, r=160),
        height=260 * len(locations),
    )
    fig.update_xaxes(title_text=xlabel, row=len(locations), col=1)
    for row in range(1, len(locations) + 1):
        fig.update_yaxes(title_text=ylabel, range=yrange, row=row, col=1)
    return fig



def compare_contours(
    planes: dict[str, WakePlane],
    title: str = "Horizontal streamwise velocity contour",
):
    """
    Build a matplotlib figure comparing horizontal contour planes from exactly two
    software packages, plus a third panel showing their difference.

    Args:
        planes (dict[str, WakePlane]): Mapping of exactly two software names to their
            computed WakePlane for the same case.
        title (str, optional): Figure title. Defaults to
            "Horizontal streamwise velocity contour".

    Returns:
        matplotlib.figure.Figure
    """
    names = list(planes.keys())
    if len(names) != 2:
        raise ValueError("compare_contours() requires exactly two planes to compare.")
    a, b = names
    diff = planes[a] - planes[b]
    abs_diff = np.abs(diff.values)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    plt.axes(axes[0])
    plot_plane(planes[a], clevels=100, color_bar=True, title=a)
    plt.axes(axes[1])
    plot_plane(planes[b], clevels=100, color_bar=True, title=b)
    plt.axes(axes[2])
    plot_plane(
        diff,
        min_speed=-1 * np.max(abs_diff),
        max_speed=np.max(abs_diff),
        cmap='PuOr',
        clevels=100,
        color_bar=True,
        title=f"{a} - {b}",
    )
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def _plotly_to_html(fig: go.Figure, include_js: bool) -> str:
    height = fig.layout.height or 400
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if include_js else False,
        default_width="100%",
        default_height=f"{height}px",
    )


def _matplotlib_to_html(fig) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f'<img alt="{fig._suptitle.get_text() if fig._suptitle else ""}" src="data:image/png;base64,{encoded}" style="max-width: 100%;" />'


def render_wake_model_tabs(cases: dict[str, dict]) -> "IPython.core.display.HTML":
    """
    Build a single interactive tab-set, reusing the CSS already loaded by
    sphinx-design's `{tab-set}` directive, where each tab shows the complete set of
    comparison plots (1D profiles, cross-sections, and a contour comparison, where
    available) for one wake model. This exists because myst-nb does not support
    executable code cells nested inside other directives (like a MyST tab-item), so
    the whole tab-set is instead rendered as a single, self-contained HTML output.

    Args:
        cases (dict[str, dict]): Mapping of a tab label (e.g. a wake model name) to
            the dict returned by a case's compute function, with keys "streamwise",
            "xsections", "wind_speed" (used to fix the cross-section y-axis range to
            [0, wind_speed] so it's comparable across locations and wake models), and
            (optionally) "planes".

    Returns:
        IPython.display.HTML: A rich HTML display object for the whole tab-set.
    """
    from IPython.display import HTML

    group_name = "wake-model-tabs"
    include_js = True
    parts = ['<div class="sd-tab-set docutils">']
    for i, (label, case) in enumerate(cases.items()):
        input_id = f"{group_name}-{i}"
        checked = " checked" if i == 0 else ""
        parts.append(f'<input{checked} id="{input_id}" name="{group_name}" type="radio">')
        parts.append(f'<label class="sd-tab-label" for="{input_id}">{label}</label>')
        parts.append('<div class="sd-tab-content docutils">')

        streamwise_fig = compare_profiles_plotly(
            case["streamwise"], xlabel="X (m)", title="Streamwise velocity"
        )
        parts.append(_plotly_to_html(streamwise_fig, include_js))
        include_js = False

        xsections_fig = compare_xsections_plotly(
            case["xsections"], title="Cross-section velocity",
            ymin=0, ymax=case.get("wind_speed"),
        )
        parts.append(_plotly_to_html(xsections_fig, include_js))

        if case.get("planes"):
            parts.append(_matplotlib_to_html(compare_contours(case["planes"])))

        parts.append('</div>')
    parts.append('</div>')
    return HTML("\n".join(parts))


