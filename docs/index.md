
# Wind turbine wake models compared

There is a set of wind turbine wake modeling software that share common characteristics:
- Steady state, low order mathematical models
- Python-based
- Research-oriented

```{tableofcontents}
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

  class wcomp {
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


## Specification

```{mermaid}
classDiagram

  class WakeModelManager {
    combination_function
    deflection_function
    turbulence_function
    velocity_function
    validate_model_strings(instance: attrs.Attribute, value: dict) None
  }
  <<interface>> WakeModelManager
  class GaussVelocityDeficit {
    prepare_function(grid: Grid, flow_field: FlowField) Dict[str, Any]
    function(x_i: np.ndarray,\ny_i: np.ndarray,\nz_i: np.ndarray,\naxial_induction_i: np.ndarray,\ndeflection_field_i: np.ndarray,\nyaw_angle_i: np.ndarray,\nturbulence_intensity_i: np.ndarray,\nct_i: np.ndarray,\nhub_height_i: float,\nrotor_diameter_i: np.ndarray) None
  }
  class GaussVelocityDeflection {
    prepare_function(grid: Grid, flow_field: FlowField) dict[str, Any]
    function(x_i: np.ndarray,\ny_i: np.ndarray,\nyaw_i: np.ndarray,\nturbulence_intensity_i: np.ndarray,\nct_i: np.ndarray,\nrotor_diameter_i: float)
  }
  WakeModelManager -- GaussVelocityDeficit
  WakeModelManager -- GaussVelocityDeflection
```

## Implementation

```{mermaid}
classDiagram
  class BaseClass {
    logger
  }
  class Grid {
    cubature_weights
    grid_resolution : int | Iterable
    n_turbines : int
    n_wind_directions : int
    n_wind_speeds : int
    time_series : bool
    turbine_coordinates
    turbine_diameters
    wind_directions
    wind_speeds
    x_sorted
    x_sorted_inertial_frame
    y_sorted
    y_sorted_inertial_frame
    z_sorted
    z_sorted_inertial_frame
    check_coordinates(instance: attrs.Attribute, value: np.ndarray) None
    grid_resolution_validator(instance: attrs.Attribute, value: int | Iterable) None
    set_grid()* None
    wind_directions_validator(instance: attrs.Attribute, value: NDArrayFloat) None
    wind_speeds_validator(instance: attrs.Attribute, value: NDArrayFloat) None
  }
  <<abstract>> Grid
  class TurbineGrid {
    average_method : str
    sorted_coord_indices
    sorted_indices
    unsorted_indices
    x_center_of_rotation
    y_center_of_rotation
    set_grid() None
  }
  class FromDictMixin {
    as_dict() dict
    from_dict(data: dict)
  }

  FromDictMixin <|-- BaseClass
  BaseClass <|-- Grid
  Grid <|-- TurbineGrid
```

## Sequence

```{mermaid}
sequenceDiagram
  participant AA as Floris
  participant A as Solver
  participant B as DeficitModel
  participant C as DeflectionModel
  participant D as CombinationModel
  activate AA
  AA ->> A: <<create>>
  AA ->> B: <<create>>
  AA ->> C: <<create>>
  deactivate AA

  activate A
  A ->> B: prepare_function()
  A ->> C: prepare_function()

loop Every turbine
    A ->> C: function()
    deactivate A
    activate C
    C ->> A: deflection_field
    deactivate C
    A ->> B: function()
    activate B
    B ->> A: velocity_deficit
    deactivate B
    A ->> D: function()
    activate D
    D ->> A: full wake field with current turbine's wake
    deactivate D
    activate A
end

A ->> A: Save solver data to Floris objects (velocity components)
deactivate A

AA ->> AA: Post processes to calculate AEP or power
```
