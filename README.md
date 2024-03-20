
# wcomp - A framework for comparing steady-state wind turbine wake modeling software

`wcomp` is a Python-based framework for comparing the wind turbine and wind farm wake
calculations from a class of simulation software that typically have the following
characteristics:

- Python-based
- Low-fidelity, analytical models
- Research oriented

The objective is to provide a framework for characterizing the spread in implementations
and customizations of a common set of mathematical wake models. 

This framework and simple use cases were presented at the
2023 Wind Energy Sciences Conference in Glasgow, Scotland, by Rafael Mudafort.
The slides from this talk are available at
[here](https://github.com/rafmudaf/wcomp/blob/main/2.2%20Mudafort%20Validation%20Framework%20for%20Python-based%20steady-state%20wake%20models.pptx),
and a corresponding executable notebook is [here](https://github.com/rafmudaf/wcomp/blob/main/examples/wesc2023_demo.ipynb).
Documentation for `wcomp` is available at https://rafmudaf.github.io/wcomp/.

**DOI: 10.11578/dc.20231113.4**

# Installation

Currently, `wcomp` must be installed manually `pip`. The dependencies are:

- windIO v1.0, can be installed directly from PyPI
- FLORIS v3.6 (current develop branch), not yet released so must be installed from locally from https://github.com/nrel/floris
- foxes v0.6.2, can be installed directly from PyPI
- PyWake v2.5.0 plus three additional commits, must be installed from https://github.com/rafmudaf/PyWake at master branch

Follow these steps to install the dependencies and `wcomp`:
1. Create a new Python environment
2. Install the dependencies:

```bash
pip install windIO
pip install foxes==0.6.2
git clone https://github.com/nrel/floris -b develop && pip install -e floris/
git clone https://github.com/rafmudaf/PyWake && pip install -e PyWake/
```

3. Install `wcomp`:

```bash
git clone https://github.com/rafmudaf/wcomp
pip install -e wcomp
```

## Architecture and Design

The `wcomp` framework is meant to be simple and flexible. At it's core, it is three
district components:

1. A connection to the windIO interface for each integrated wake modeling software
2. A library of data structures to represent the results of a wake calculation
3. A library of plotting methods that couple with the included data structures

Any methods related to wind farm simulations or the calculation of related values
or statistics should exist in the wake modeling software packages themselves.
This framework should remain the point of the connection across this class of
software.

The architecture of this framework is outlined below. The integrated wake modeling
software are dependencies of `wcomp`, but their source code is external to this repository.
The `windIO` package is used both to define the comparison cases and to load the input files.

```mermaid
graph TD
    L["FLORIS"]
    M["foxes"]
    N["PyWake"]

    A["windIO"]
    subgraph a[wcomp]
        B["Model Interface"]
        C["Output Data Structure"]
        D["Plotting"]
    end

    L --> a
    M --> a
    N --> a
    A --> B
    C --> B
```

See the [Architecture](https://rafmudaf.github.io/wcomp/architecture.html) and
[API documentation](https://rafmudaf.github.io/wcomp/api_docs.html) for more information.


# Limitations
- Can only use 1 turbine type
    - Foxes calls the windIO input by a hard coded name, so any additional turbine type will overwrite the previous definition
- windIO doesn't have a schema for model inputs, so these are currently hard coded in the code interfaces (WindIOCode-classes)
