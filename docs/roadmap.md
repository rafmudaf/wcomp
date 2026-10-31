# Roadmap

This page tracks planned additions to the [Dashboard](dashboard.md) that aren't
implemented yet.

## Spatial discretization and rotor average velocity

Since the focus is specifically on analytical wake models, this class of software does not
require a specific type of grid to model the wake. In practice, each software can choose a
grid that meets its design and use objectives. However, the grid type has an impact on the
results of the model through the computation of the thrust coefficient from a rotor-averaged
velocity. The comparison plan below is meant to isolate this effect and quantify how FLORIS,
FOXES, and PyWake differ after the rotor-average step.

### Comparison plan

1. **Create a canonical rotor disk benchmark**
   - Use a common normalized rotor and a ladder of four velocity fields of increasing difficulty,
     so that each step adds exactly one new source of quadrature error:
     1. *Uniform* (`U/U∞ = 1`) — verifies that each stencil's weights are normalized; exact for all.
     2. *Linear vertical shear* (`1 + 0.2 z/R`) — exact for symmetric stencils under arithmetic
       averaging, which isolates the effect of a nonlinear (cubic) aggregation.
     3. *Quadratic radial deficit* (`1 - 0.2 (r/R)²`, exact area average 0.9) — the first case with
       curvature, which ranks the methods by how far they reach toward the blade tips.
     4. *Offset Gaussian deficit* — an asymmetric field that resembles partial wake coverage.
   - Evaluate each configured stencil on those identical fields.
   - Instantiate each installed framework's configured rotor model and use its native
     rotor-averaging API to produce the reported value; do not duplicate the framework's
     quadrature or aggregation formula in wcomp.
   - Compare each with a dense-disk numerical reference using the same aggregation semantics.

2. **Document the implementation-specific rotor averaging method**
   - FLORIS: turbine-grid sampling and rotor plane weighting within the turbine model.
   - FOXES: the radial or field-based rotor average used for its wake/CT calculations.
   - PyWake: the rotor-averaging model selected for `PropagateDownwind` (for example `GridRotorAvg`,
     `EqGridRotorAvg`, `GQGridRotorAvg`, etc.).
   - Record the sampling pattern, weighting, and any assumptions about partial wake coverage.

3. **Run the same benchmark for each configured method**
   - FLORIS: nine equal-weight `TurbineGrid` samples and a cubic mean.
   - FOXES: the weighted 16-point `GridRotor` and arithmetic `REWS` used by the interface.
   - PyWake: four equal-weight `GridRotorAvg` samples and arithmetic deficit averaging.
   - Compare each result against its matching dense-disk reference and against the other methods.

4. **Probe the failure modes that matter most**
   - **Point placement**: how the sample points are placed across the rotor and whether they are
     clustered near the edge or at the hub.
   - **Rotor velocity average**: the value obtained after averaging a smooth profile with a known
     analytical integral.
   - **Partial wake treatment**: how the mean is modified when only part of the rotor is waked.
   - **Grid dependence**: how the result changes with the number of grid points or radial rings.

5. **Report the comparison in a consistent format**
   - Use the same rotor radius, same analytic profiles, and same reference values for every solver.
   - Report a table of sample-average, exact-average, absolute error, and relative error.
   - Plot the profile and average on a normalized rotor radius to isolate numerical method choices
     from wake-model physics.

This task is implemented in `wcomp/rotor_average.py`, exercised by
`tests/test_rotor_average.py`, and published on the site's rotor velocity averaging comparison
page.

## Overlapping wakes

Compare how each software combines the velocity deficit from multiple overlapping wakes
(superposition models), and how the choice of combination model changes the predicted
velocity deficit at a downstream turbine.

## Wind shear and veer

Compare how each software models wind shear and wind veer, and the effect of each on the
wake profiles shown on the dashboard.
