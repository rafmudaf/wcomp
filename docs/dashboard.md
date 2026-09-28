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

## Wake model implementations
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


### Wake profiles

The schematic below shows the sample locations used for every comparison in this section:
a streamwise profile through four turbines, a cross-stream profile 4D downstream of the
first turbine, and cross-stream profiles at 1D, 5D, and 10D downstream of the last
turbine, where the combined farm wake has developed.

```{code-cell}
---
tags: [remove-input]
---

y_turbine = np.array([-ROTOR_D/2, ROTOR_D/2])
x_streamwise = np.array([XMIN, XMAX])
y_streamwise = np.array([0.0, 0.0])
y_crosswise = np.array([YMIN, YMAX])
first_turbine_d = TURBINE_LOCATIONS_D[0]
last_turbine_d = TURBINE_LOCATIONS_D[-1]

fig, ax = plt.subplots(figsize=(6, 3))
for i, turbine_d in enumerate(TURBINE_LOCATIONS_D):
    x_turbine = np.array([turbine_d * ROTOR_D, turbine_d * ROTOR_D])
    ax.plot(
        x_turbine, y_turbine, '-', color='black', linewidth=3,
        label="Turbine" if i == 0 else None,
    )
ax.plot(x_streamwise, y_streamwise, '-.', color='black', linewidth=2, label="Streamwise")
x_4d = np.array([(first_turbine_d + 4) * ROTOR_D, (first_turbine_d + 4) * ROTOR_D])
ax.plot(
    x_4d, y_crosswise, linestyle=(0, (1, 1)), color='black', linewidth=2,
    label="4D cross section (past first turbine)",
)
for i, d in enumerate((1, 5, 10)):
    x_d = np.array([(last_turbine_d + d) * ROTOR_D, (last_turbine_d + d) * ROTOR_D])
    ax.plot(
        x_d, y_crosswise, linestyle=(0, (2, 3)), color='black', linewidth=2,
        label="1D, 5D, 10D cross sections (past last turbine)" if i == 2 else None,
    )
ax.set_title("Four-turbine sample locations")
ax.set_xlabel("X (m)")
ax.set_ylabel("Y (m)")
ax.set_ylim([-1000, 1000])
ax.axis('equal')
ax.grid()
ax.legend()
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

## What's next

Spatial discretization/rotor-averaging comparisons, overlapping wakes, and wind shear/veer
handling are planned additions to this dashboard. See the [Roadmap](roadmap.md) page for
details on what's coming.

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
