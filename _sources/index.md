
# Wakes Compared (wcomp)

Wind farm flow control presents an opportunity to improve the cost of energy and energy yield
of wind farms in specific environments.
A class of software tools that model the effects of wake losses and opportunities for wake
loss mitigation via wind farm flow control has emerged in the past decade.
Many of these tools share key characteristics:
-	Written in the Python programming language
-	Implement multiple steady-state, analytical wake models
-	Target workstation use
-	Integrate with optimization software ecosystems

However, software design decisions and implementation details can lead to discrepancies
and errors across tools that reference corresponding models.
`wcomp` is a Python package that provides an interface to data structures and plotting functions
that enable the comparison of wake model implementations across different software tools.
At its core, `wcomp` provides a set of data structures to contain the results of a
wind farm wake model simulation and a set of plotting functions to inspect these data structures.
Any wind farm wake modeling software that implements the `wcomp` interface can be included
in the comparison directly.

The package diagram below shows the modules within `wcomp` and how each relates to the
others as dependencies (in other words, which modules import which other modules).

<!-- Command: pyreverse --colorized -o mmd . --verbose -->
  <!-- class wcomp {
  }
  class base_interface {
  }
  class floris_interface {
  }
  class foxes_interface {
  }
  class output_struct {
  }
  class plotting {
  }
  class pywake_interface {
  }
  The mermaid on github doesnt support this syntax for some reason.
  I gives a "syntax error in text" message -->

```{mermaid}
classDiagram
  wcomp --> floris_interface
  wcomp --> foxes_interface
  wcomp --> pywake_interface
  base_interface --> output_struct
  floris_interface --> base_interface
  floris_interface --> output_struct
  floris_interface --> plotting
  foxes_interface --> base_interface
  foxes_interface --> output_struct
  foxes_interface --> plotting
  plotting --> output_struct
  pywake_interface --> base_interface
  pywake_interface --> output_struct
  pywake_interface --> plotting
```




## Class
```{mermaid}
classDiagram
    class WCompFloris {
        LEGEND : str
        LINE_PLOT_COLOR : str
        LINE_PLOT_LINESTYLE : str
        LINE_PLOT_MARKER : str
        deflection_model_string : str
        deflection_parameters : Optional[dict]
        fi : FlorisInterface
        floris_dict : dict
        hub_height
        rotor_diameter
        velocity_deficit_model_string : str
        velocity_deficit_parameters : dict
        yaw_angles : ndarray
        AEP()
        horizontal_contour(wind_direction: float, resolution: tuple) WakePlane
        streamwise_profile_plot(wind_direction: float, y_coordinate: float, xmin: float, xmax: float)
        vertical_profile_plot(wind_direction: float, x_coordinate: float, y_coordinate: float, zmax: float)
        xsection_contour(wind_direction: float, resolution: tuple, x_coordinate: float) WakePlane
        xsection_profile_plot(wind_direction: float, x_coordinate: float, ymin: float, ymax: float)
    }
```

## Abstract Class
```{mermaid}
classDiagram
  class WCompBase {
    LEGEND : str
    LINE_PLOT_COLOR : str
    hub_height
    rotor_diameter
    AEP()* float
    horizontal_contour(wind_direction: float, resolution: tuple)* WakePlane
    streamwise_profile_plot(wind_direction: float, y_coordinate: float, xmin: float, xmax: float)*
    vertical_profile_plot(wind_direction: float, x_coordinate: float, y_coordinate: float, zmax: float)*
    xsection_contour(wind_direction: float, resolution: tuple, x_coordinate: float)* WakePlane
    xsection_profile_plot(wind_direction: float, x_coordinate: float, ymin: float, ymax: float)*
  }
```

## Inheritance

**All the details**
```{mermaid}
classDiagram
  class WCompBase {
    LEGEND : str
    LINE_PLOT_COLOR : str
    hub_height
    rotor_diameter
    AEP()* float
    horizontal_contour(wind_direction: float, resolution: tuple)* WakePlane
    streamwise_profile_plot(wind_direction: float, y_coordinate: float, xmin: float, xmax: float)*
    vertical_profile_plot(wind_direction: float, x_coordinate: float, y_coordinate: float, zmax: float)*
    xsection_contour(wind_direction: float, resolution: tuple, x_coordinate: float)* WakePlane
    xsection_profile_plot(wind_direction: float, x_coordinate: float, ymin: float, ymax: float)*
  }
  class WCompFloris {
    LEGEND : str
    LINE_PLOT_COLOR : str
    LINE_PLOT_LINESTYLE : str
    LINE_PLOT_MARKER : str
    deflection_model_string : str
    deflection_parameters : Optional[dict]
    fi : FlorisInterface
    floris_dict : dict
    hub_height
    rotor_diameter
    velocity_deficit_model_string : str
    velocity_deficit_parameters : dict
    yaw_angles : ndarray
    AEP()
    horizontal_contour(wind_direction: float, resolution: tuple) WakePlane
    streamwise_profile_plot(wind_direction: float, y_coordinate: float, xmin: float, xmax: float)
    vertical_profile_plot(wind_direction: float, x_coordinate: float, y_coordinate: float, zmax: float)
    xsection_contour(wind_direction: float, resolution: tuple, x_coordinate: float) WakePlane
    xsection_profile_plot(wind_direction: float, x_coordinate: float, ymin: float, ymax: float)
  }
  WCompBase <|-- WCompFloris
```

**Only interface**
```{mermaid}
classDiagram
  class WCompBase {
    LEGEND : str
    LINE_PLOT_COLOR : str
    hub_height
    rotor_diameter
    AEP()* float
    horizontal_contour(wind_direction: float, resolution: tuple)* WakePlane
    streamwise_profile_plot(wind_direction: float, y_coordinate: float, xmin: float, xmax: float)*
    vertical_profile_plot(wind_direction: float, x_coordinate: float, y_coordinate: float, zmax: float)*
    xsection_contour(wind_direction: float, resolution: tuple, x_coordinate: float)* WakePlane
    xsection_profile_plot(wind_direction: float, x_coordinate: float, ymin: float, ymax: float)*
  }
  class WCompFloris {
    deflection_model_string : str
    deflection_parameters : Optional[dict]
    fi : FlorisInterface
    floris_dict : dict
    velocity_deficit_model_string : str
    velocity_deficit_parameters : dict
    yaw_angles : ndarray
  }
  WCompBase <|-- WCompFloris
```

## Aggregation and Composition

  class WCompBase {
  }
  class WCompFloris {
  }
  class WCompFoxes {
  }
  class WCompPyWake {
  }

```{mermaid}
classDiagram
  class WakePlane {
    normal_vector : str
    resolution : Tuple
    values
    x1
    x2
  }
  class WakeProfile {
    values
    x1
  }
  WCompBase <|-- WCompFloris
  WCompBase <|-- WCompFoxes
  WCompBase <|-- WCompPyWake
  WakeProfile *-- WCompFloris
  WakeProfile *-- WCompFoxes
  WakeProfile *-- WCompPyWake
  WakePlane *-- WCompFloris
  WakePlane *-- WCompFoxes
  WakePlane *-- WCompPyWake
```


## Package

```{mermaid}
classDiagram
  wcomp --> floris_interface
  wcomp --> foxes_interface
  wcomp --> pywake_interface
  base_interface --> output_struct
  floris_interface --> base_interface
  floris_interface --> output_struct
  floris_interface --> plotting
  foxes_interface --> base_interface
  foxes_interface --> output_struct
  foxes_interface --> plotting
  plotting --> output_struct
  pywake_interface --> base_interface
  pywake_interface --> output_struct
  pywake_interface --> plotting
```



