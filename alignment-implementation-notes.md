# Alignment toggle: implementation notes and open questions

Working log for [alignment-toggle-plan.md](alignment-toggle-plan.md). Newest items are appended to each section.

## Commit trail

| Repo | Branch | Commits |
|---|---|---|
| wcomp | `main` | `bb0251e` checkpoint of the aligned working tree (before restructuring) |
| FLORIS | `configurable-rotor-averaging` | `1cb00fb4`, `62ba6f05`, `6b791d47`, `8fd24b76`, `cbf17267`, `a9237569` |
| windIO | `analyses-block` | `d977231`, `59678bd` |

## FLORIS

- Keys live in the `solver` block: `power_average_method`, `thrust_average_method` (both optional).
  - `turbine_grid`: `linear-mean`, `quadratic-mean`, `cubic-mean` (default `cubic-mean`).
  - `turbine_cubature_grid`: `linear-cubature`, `quadratic-cubature`, `cubic-cubature`. Thrust default is `linear-cubature`; power default stays `cubic-mean` (upstream behaviour).
- `turbine_cubature_grid` with `turbine_grid_points: N` has N x N points (N = 3 gives 9). So windIO `n_points` maps to `sqrt(n_points)`.
- Upstream `FlorisModel._get_turbine_powers` ignored the grid's averaging method (always an unweighted cubic mean). The branch now passes `power_average_method`, with the default unchanged.
- Decision for the plan: the plan said cubature-grid power defaults to `linear-cubature`. The FLORIS work kept upstream numerics instead (`cubic-mean`), since a different default would change upstream results. The aligned yaml sets `linear-cubature` explicitly, so nothing is lost.
- Not changed, flagged by the FLORIS work: the `cc` solver inner average keeps its `cubic-mean` default; `solver` has no unknown-key check; `set(solver_settings=...)` replaces the whole dict; `full_flow_*` solvers and the visualization path build a hidden default grid and ignore the new keys.

## windIO

- `attributes.analyses` is in the plant schema, all 12 wcomp `analyses` blocks validate against it.
- Whole-file validation of the wcomp case files still fails for unrelated reasons (`air_density`, `wind_farm` shape). Out of scope.
- `velocity.name` / `deflection.name` are free strings (no enum).
- Not encoded in the schema: `cubature` needs `n_points`, FLORIS needs a perfect square. The wcomp adapter enforces both.

## Open questions (carried forward)

1. Should windIO enumerate model names? (Currently free strings.)
2. Should `wind_speed_exponent_*` be limited to 1, 2, 3? (Currently any number; the wcomp adapter rejects other values for FLORIS.)
3. FOXES `n_points: 9` in the aligned yaml is not honoured (FOXES keeps `grid16`). The adapter reports it and the site shows it as a residual difference.
