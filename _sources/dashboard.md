---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python
---

```{code-cell}
---
tags: [remove-input]
---

# stdlib
import warnings
from pathlib import Path

# Silence solver-related warnings (e.g. tqdm's IProgress notice, raised at import
# time by FOXES) so they don't end up embedded in the built page.
warnings.filterwarnings("ignore")

# third-party
import matplotlib.pyplot as plt
import numpy as np
import plotly.io as pio

# wcomp
from wcomp import WCompFloris, WCompPyWake, WCompFoxes
from wcomp.cache import DiskCache, quiet
from wcomp.plotting import render_wake_model_tabs
from windIO import load_yaml

# Load plotly.js once from a CDN instead of inlining a full copy in every cell output.
pio.renderers.default = "notebook_connected"

plt.rc('axes', labelsize=12)
plt.rc('axes', titlesize=14)
plt.rc('legend', fontsize=12)
plt.rc('figure', titlesize=14)

CASE_ROOT = Path('cases_torque2024/four_turbine')

# The four turbines in this case are evenly spaced 5D apart (0D, 5D, 10D, 15D)
TURBINE_LOCATIONS_D = [0, 5, 10, 15]

# Solver results are cached on disk (see wcomp.cache.DiskCache) so that rebuilding this
# page doesn't require re-running every wake model every time, and so the noisy console
# output the solvers produce (progress bars, per-chunk logging) doesn't end up embedded
# in the page on cache hits. wcomp.cache.quiet() silences that output on cache misses.
CACHE = DiskCache(Path('.cache/dashboard'))

# Maps each wake-model case to the software packages that implement it, and the subset
# (if any) that should also be compared with a horizontal contour plot.
WAKE_MODEL_CASES = {
    "jensen": {
        "software": [WCompFloris, WCompFoxes, WCompPyWake],
        "contour_software": [WCompFloris, WCompFoxes],
    },
    "bastankhah2014": {
        "software": [WCompFoxes, WCompPyWake],
        "contour_software": [WCompFoxes, WCompPyWake],
    },
    "bastankhah2016": {
        "software": [WCompFloris, WCompFoxes],
        "contour_software": [WCompFloris, WCompFoxes],
    },
    "bastankhah2016_deflection": {
        "software": [WCompFloris, WCompFoxes],
        "contour_software": [],
    },
    "jimenez": {
        "software": [WCompFloris, WCompPyWake],
        "contour_software": [WCompFloris, WCompPyWake],
    },
    "turbopark": {
        "software": [WCompFloris, WCompFoxes, WCompPyWake],
        "contour_software": [WCompFloris, WCompFoxes],
    },
}

def compute_case(wake_model: str) -> dict:
    """
    Run (or load from the on-disk cache) every software package integrated for a given
    wake-model case, and extract the plain data needed to render the comparison plots.
    """
    spec = WAKE_MODEL_CASES[wake_model]
    case_file = CASE_ROOT / wake_model / 'wind_energy_system.yaml'

    def _run():
        with quiet():
            instances = {cls: cls(case_file) for cls in spec["software"]}
            rotor_d = next(iter(instances.values())).rotor_diameter
            # Cross-section plots share this as their y-axis range, so they're
            # comparable across wake models and downstream locations.
            wind_speed = load_yaml(case_file)["site"]["energy_resource"]["wind_resource"]["wind_speed"][0]
            first_turbine_d = TURBINE_LOCATIONS_D[0]
            last_turbine_d = TURBINE_LOCATIONS_D[-1]
            xmin, xmax = -1 * rotor_d, (last_turbine_d + 20) * rotor_d
            ymin, ymax = -2 * rotor_d, 2 * rotor_d

            # Cross-sections are sampled 4D past the first turbine (before its wake
            # reaches the second turbine) and 1D/5D/10D past the last turbine, where
            # the combined wake of the whole farm has had a chance to develop.
            xsection_locations = {
                "4 D (past first turbine)": first_turbine_d + 4,
                "1 D (past last turbine)": last_turbine_d + 1,
                "5 D (past last turbine)": last_turbine_d + 5,
                "10 D (past last turbine)": last_turbine_d + 10,
            }

            streamwise = {}
            xsections = {label: {} for label in xsection_locations}
            for cls, instance in instances.items():
                streamwise[cls.LEGEND] = instance.streamwise_profile_plot(
                    wind_direction=270, y_coordinate=0.0, xmin=xmin, xmax=xmax
                )
                for label, location_d in xsection_locations.items():
                    xsections[label][cls.LEGEND] = instance.xsection_profile_plot(
                        wind_direction=270,
                        x_coordinate=location_d * rotor_d,
                        ymin=ymin,
                        ymax=ymax,
                    )

            planes = {
                cls.LEGEND: instances[cls].horizontal_contour(wind_direction=270)
                for cls in spec["contour_software"]
            }

        plt.close('all')  # discard the matplotlib figures created as a side effect above
        return {
            "rotor_diameter": rotor_d,
            "wind_speed": wind_speed,
            "streamwise": streamwise,
            "xsections": xsections,
            "planes": planes,
        }

    return CACHE.get_or_compute(wake_model, _run)

# Used below to draw the schematic of sample locations, shared across every case.
_jensen_result = compute_case("jensen")
ROTOR_D = _jensen_result["rotor_diameter"]
XMIN, XMAX = -1 * ROTOR_D, (TURBINE_LOCATIONS_D[-1] + 20) * ROTOR_D
YMIN, YMAX = -2 * ROTOR_D, 2 * ROTOR_D
```

# Dashboard

This page compares the integrated wake modeling software (FLORIS, FOXES, PyWake) on a
common set of cases. Each comparison figure is interactive: hover over a trace for exact
values, or click a legend entry to toggle it on/off.

## Implementation table
The mathematical models included in each software are generally grouped into models
describing the velocity of the wind in a wind turbine wake (velocity model) and
models describing the magnitude of deflection of the wake (deflection model).
The models available in each software are shown in the tables below.

:::{table} Velocity models
:align: center
:width: 75%

| Wake Model                        | FLORIS | FOXES | PyWake |
| --------------------------------- | ------ | ----- | ------ |
| **Jensen 1983**                   | •      | •     | •      |
| Larsen 2009                       |        |       | •      |
| **Bastankhah / Porte Agel 2014**  |        | •     | •      |
| **Bastankhah / Porte Agel 2016**  | •      | •     |        |
| Niayifar / Porté-Agel 2016        |        |       | •      |
| IEA Task 37 Bastankhah 2018       |        |       | •      |
| Carbajo Fuertes / Markfort / Porté-Agel 2018  |        |       | •      |
| Blondel / Cathelain 2020          |        |       | •      |
| Zong / Porté-Agel 2020            |        |       | •      |
| Cumulative Curl 2022              | •      |       |        |
| **TurbOPark (Nygaard 2022)**      | •      | •     | •      |
| Empirical Gauss 2023              | •      |       |        |
:::

:::{table} Deflection models
:align: center
:width: 75%

| Wake Model                        | FLORIS | FOXES | PyWake |
| --------------------------------- | ------ | ----- | ------ |
| **Jimenez 2010**                  | •      |       | •      |
| **Bastankhah / Porte Agel 2016**  | •      | •     |        |
| Larsen et al 2020                 |        |       | •      |
| Empirical Gauss 2023              | •      |       |        |
:::


## Wake profiles

The schematic below shows the sample locations used for every comparison in this section:
- A streamwise profile through four turbines
- A cross-stream profile 4D downstream of the first turbine
- Cross-stream profiles at 1D, 5D, and 10D downstream of the last turbine where the combined
  wake is fully developed

In the deflection model cases, the first two turbines are yawed 10°.
Without a deflection model, all turbines are aligned with the wind.

```{code-cell}
---
tags: [remove-input]
---

from IPython.display import HTML

first_turbine_d = TURBINE_LOCATIONS_D[0]
last_turbine_d = TURBINE_LOCATIONS_D[-1]
schematic_width = 920
schematic_height = 300
left_margin = 60
right_margin = 60
usable_width = schematic_width - left_margin - right_margin
scale = usable_width / (XMAX - XMIN)

def x_px(distance_m: float) -> float:
    return left_margin + (distance_m - XMIN) * scale

# Vertical layout, top to bottom: cross-section plane labels, the planes themselves
# (centered on the streamwise axis, since that's the line they actually sample along),
# turbines drawn on top of the axis, turbine labels below the planes, and the
# streamwise arrow at the bottom. Keeping each label in its own horizontal band means
# nearby markers (e.g. the last turbine and the "1D past last turbine" plane, only 1D
# apart) never collide, regardless of how close their x positions are.
axis_y = 130
plane_label_y = 45
plane_top, plane_bottom = axis_y - 70, axis_y + 70
turbine_top, turbine_bottom = axis_y - 25, axis_y + 25
turbine_label_y = plane_bottom + 20
arrow_y = turbine_label_y + 30
arrow_label_y = arrow_y + 18
footnote_y = arrow_label_y + 22

def cross_section_plane(distance_m: float, label: str, color: str) -> str:
    x_pos = x_px(distance_m)
    return f'''
    <line x1="{x_pos:.1f}" y1="{plane_top}" x2="{x_pos:.1f}" y2="{plane_bottom}"
          stroke="{color}" stroke-width="2.5" stroke-dasharray="6 5" />
    <text x="{x_pos:.1f}" y="{plane_label_y}" text-anchor="middle" class="plane-label" fill="{color}">{label}</text>
    '''

planes = cross_section_plane((first_turbine_d + 4) * ROTOR_D, "4D", "#2563eb")
planes += ''.join(
    cross_section_plane((last_turbine_d + d) * ROTOR_D, f"{d}D", "#15803d")
    for d in (1, 5, 10)
)

# The first two turbines are yawed 10 degrees, matching the yaw_angles used in the
# deflection cases (e.g. bastankhah2016_deflection/wind_energy_system.yaml).
TURBINE_YAW_DEG = [10, 10, 0, 0]

def turbine_marker(turbine_d: float, yaw_deg: float) -> str:
    x_pos = x_px(turbine_d * ROTOR_D)
    rotate = f' transform="rotate({yaw_deg} {x_pos:.1f} {axis_y})"' if yaw_deg else ''
    label = f"{turbine_d}D" + (f" ({yaw_deg}\u00b0 yaw)" if yaw_deg else "")
    return f'''
    <line x1="{x_pos:.1f}" y1="{turbine_top}" x2="{x_pos:.1f}" y2="{turbine_bottom}"
          stroke="#111827" stroke-width="6" stroke-linecap="round"{rotate} />
    <text x="{x_pos:.1f}" y="{turbine_label_y}" text-anchor="middle" class="turbine-label">{label}</text>
    '''

turbines = ''.join(
    turbine_marker(turbine_d, yaw_deg)
    for turbine_d, yaw_deg in zip(TURBINE_LOCATIONS_D, TURBINE_YAW_DEG)
)

stream_start, stream_end = x_px(XMIN), x_px(XMAX)
stream_mid = 0.5 * (stream_start + stream_end)

svg = f'''
<div style="max-width: 920px; margin: 0 auto; font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;">
  <svg viewBox="0 0 {schematic_width} {schematic_height}" width="100%" role="img" aria-labelledby="wake-sample-title wake-sample-desc">
    <title id="wake-sample-title">Four-turbine sample locations</title>
    <desc id="wake-sample-desc">A streamwise profile through the farm, a 4D cross section past the first turbine, and cross sections 1D, 5D, and 10D past the last turbine.</desc>

    <defs>
      <marker id="arrow-orange" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M 0 0 L 6 3 L 0 6 z" fill="#d97706" />
      </marker>
      <style>
        .plane-label {{ font-size: 12px; font-weight: 600; }}
        .turbine-label {{ font-size: 13px; font-weight: 600; fill: #111827; }}
        .caption {{ font-size: 12px; fill: #6b7280; }}
      </style>
    </defs>

    <rect x="0" y="0" width="{schematic_width}" height="{schematic_height}" rx="18" fill="#fafafa" stroke="#e5e7eb" />

    {planes}

    <line x1="{left_margin}" y1="{axis_y}" x2="{schematic_width - right_margin}" y2="{axis_y}" stroke="#9ca3af" stroke-width="2" />

    {turbines}

    <line x1="{stream_start:.1f}" y1="{arrow_y}" x2="{stream_end:.1f}" y2="{arrow_y}" stroke="#d97706" stroke-width="1.5" marker-start="url(#arrow-orange)" marker-end="url(#arrow-orange)" />
    <text x="{stream_mid:.1f}" y="{arrow_label_y}" text-anchor="middle" class="caption" fill="#d97706">Streamwise direction (X)</text>

    <text x="{stream_mid:.1f}" y="{footnote_y}" text-anchor="middle" class="caption">Bold lines mark turbine locations. Dashed lines mark cross-section sample planes.</text>
  </svg>
</div>
'''

HTML(svg)
```

```{code-cell}
---
tags: [remove-input]
---

# Each tab shows the full set of comparison plots (1D profiles, cross-sections, and a
# contour comparison where available) for one wake model. This is rendered as a single
# self-contained HTML block because myst-nb does not support executable code cells
# nested inside other directives (like a MyST tab-item).
render_wake_model_tabs({
    "Jensen": _jensen_result,
    "Bastankhah / Porte Agel 2014": compute_case("bastankhah2014"),
    "Bastankhah / Porte Agel 2016": compute_case("bastankhah2016"),
    "Bastankhah / Porte Agel 2016 (with deflection)": compute_case("bastankhah2016_deflection"),
    "Jensen / Jimenez (with deflection)": compute_case("jimenez"),
    "TurbOPark": compute_case("turbopark"),
})
```

# Software projects described

```{mermaid}
---
title: Timeline of software releases
<!-- theme: base
themeVariables:
  sectionBkgColor: green
  altSectionBkgColor: red
  sectionBkgColor2: blue
  taskBkgColor: lightgrey
  taskBorderColor: black
  taskTextColor: black -->
caption: Timeline of software releases
---
gantt
    dateFormat  YYYY-MM-DD
    axisFormat  %Y
    todayMarker off

    section FLORIS
    0.1 :2018-01-16, 2019-05-07
    1.0 :2019-05-07, 2020-04-27
    2.0 :2020-04-27, 2020-06-23
    2.1 :2020-06-23, 2020-09-25
    2.2 :2020-09-25, 2021-05-01
    2.3 :2021-05-01, 2021-10-02
    2.4 :2021-10-02, 2022-02-25
    2.5 :2022-02-25, 2022-03-01
    3.0 :2022-03-01, 2022-04-06
    3.1 :2022-04-06, 2022-09-16
    3.2 :2022-09-16, 2023-03-07
    3.3 :2023-03-07, 2023-05-16
    3.4 :2023-05-16, 2023-10-26
    3.5 :2023-10-26, 2024-03-15
    3.6 :2024-04-05, 2024-04-09
    4.0 :2024-04-09, 2024-06-01

    section FOXES
    0.1 (alpha) :2022-07-01, 2022-10-22
    0.2 (alpha) :2022-10-22, 2023-01-27
    0.3 (alpha) :2023-01-27, 2023-06-12
    0.4 :2023-06-12, 2023-12-13
    0.5 :2023-12-13, 2024-02-12
    0.6 :2024-02-12, 2024-05-08
    0.7 :2024-05-08, 2024-06-01

    section PyWake
    0.1 :2018-12-03, 2019-01-10
    1.0 :2019-01-10, 2020-04-14
    1.1 :2020-04-14, 2020-04-17
    2.0 :2020-04-17, 2020-09-15
    2.1 :2020-09-15, 2021-03-26
    2.2 :2021-03-26, 2022-03-18
    2.3 :2022-03-18, 2022-07-06
    2.4 :2022-07-06, 2023-02-15
    2.5 :2023-02-15, 2024-06-01
```
