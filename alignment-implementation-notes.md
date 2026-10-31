# Alignment toggle: implementation notes and open questions

Working log for [alignment-toggle-plan.md](alignment-toggle-plan.md). Newest items are appended to each section.

## Commit trail

| Repo | Branch | Commits |
|---|---|---|
| wcomp | `main` | `bb0251e` checkpoint of the aligned working tree (before restructuring); `4c8988e` settings resolution, aligned case files, `ALIGNMENTS`; `352e862` dataset split, generators, validation; `e3a4e5e` site; docs commit |
| FLORIS | `configurable-rotor-averaging` | `1cb00fb4`, `62ba6f05`, `6b791d47`, `8fd24b76`, `cbf17267`, `a9237569` (configurable averaging); `9fe5faca`, `6c1592ad`, `41d1cdf9` (full-flow solvers) |
| windIO | `analyses-block` | `d977231`, `59678bd` |

Nothing was pushed in any repo.

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

## Findings during implementation

1. **FLORIS wake plots ignored the `solver` block.** `calculate_*_plane` and `sample_flow_at_points` solve
   the turbines on a hidden `TurbineGrid(grid_resolution=3)` with default averaging, and the viz path replaces
   the solver dict. The new keys therefore had no effect on any wake plot. The checkpoint's "aligned" FLORIS
   plots had been produced by that hidden grid with the local research defaults (quadratic mean, radius ratio
   1.0), not by the cubature grid. Fix (FLORIS `9fe5faca`): when either averaging key is present, the hidden
   grid uses the configured grid type, points and methods. Without the keys, output is bit-identical to
   upstream v4.7 (168 arrays compared).
2. **The checkpoint's aligned `rotor_average.json` had a FLORIS broadcast bug.** Cubature velocities were reshaped
   to `(1, 1, 1, 9)` while the weights broadcast along axis 2, so the weighted mean was `mean(w) * mean(v)`.
   `wcomp/rotor_average.py` now keeps FLORIS' own array shape. FLORIS' nine-point cubature is exact on the
   quadratic field (error `1e-15`); the old text claiming FLORIS "only reaches the inner half radius" described
   the default `TurbineGrid`, and the site now says so per view.
3. **Existing site text described the default data.** The hand-written guidance on the case pages (for example
   "FOXES and PyWake coincide while FLORIS departs") matched the default dataset and not the aligned one. Each
   statement is now tagged `default`, `aligned` or both, and the aligned statements quote numbers read from the
   dataset.
4. **FOXES reads the case through the adapter's `load_yaml(input_file)`.** The plan's open question is resolved:
   there is no path dependency, so committed per-case files are a choice, not a constraint.
5. **Residual PyWake difference.** In the aligned view PyWake still departs from FLORIS and FOXES along
   the hub-height line for the four-turbine Jensen and Bastankhah 2014 cases while the cross-sections agree;
   the streamwise plot shows the dip at the last rotor plane. The page text names the rotor planes as a
   candidate and does not claim it.

## Verification results

- Regenerated `default` dataset vs the `HEAD` (`c809858`) dataset: identical (zero difference in every
  profile, contour and metric file).
- Regenerated `aligned` dataset vs the checkpoint data: FLORIS differs by up to `0.28 m/s` pointwise
  (TurbOPark, four turbines) and `0.011 m/s` in streamwise RMSE, because of finding 1. FOXES and PyWake are
  unchanged. Streamwise RMSE per software pair is within `0.002 m/s` of the checkpoint in every case.
- wcomp: 51 tests pass (settings mapping, aligned-file diff, dataset schema for both alignments, per-alignment
  rotor-averaging and turbine-performance checks).
- FLORIS: 339 tests pass. windIO: new tests pass; 3 pre-existing failures (missing `pint`, one meta-schema test)
  are the same with and without the change.
- Site: `npm run build` validates the dataset and builds 30 pages (15 per view). Checked in a browser: the
  toggle keeps the page and the `#streamwise` anchor, aligned charts load the aligned dataset.

## Decisions taken without asking

- Manifest layout: `alignments[]` each with `id`, `label`, `description`, a `settings` table, `residual_differences`
  and `cases`. The settings table is generated from the reference case (`one_turbine/jensen`); a test checks all
  cases share the same block.
- `--alignment {default,aligned,all}` on all three generators (default `all`). `wcomp.rotor_average` writes with
  `--write-dataset` (or `--output FILE` for a single alignment); without either it prints the tables.
- FLORIS accepts `power_average_method` on the cubature grid defaulting to `cubic-mean` (upstream behaviour);
  the aligned yaml names `linear-cubature` through the exponents.
- The `wind_speed_exponent_*` keys are limited to 1, 2 and 3 by the adapter, not by the windIO schema.
- Non-`Squared` superposition raises in all three adapters; only `Squared` is implemented.
- Added the optional "effect of aligning the configuration" table to each case page.

## Open questions (carried forward)

1. Should windIO enumerate model names? (Currently free strings.)
2. Should `wind_speed_exponent_*` be limited to 1, 2, 3? (Currently any number; the wcomp adapter rejects other values for FLORIS.)
3. FOXES `n_points: 9` in the aligned yaml is not honoured (FOXES keeps `grid16`). The adapter reports it and the site shows it as a residual difference.
4. FLORIS: the `cc` solver's inner rotor average ignores `thrust_average_method` on `turbine_grid`; `solver` has no
   unknown-key check; `set(solver_settings=...)` replaces the whole solver dict. None affect the wcomp cases.
5. Upstream FLORIS ignored the grid's averaging method for power (always an unweighted cubic mean). The branch
   now honours `power_average_method` with the default unchanged. Switching the cubature-grid default to
   `linear-cubature` would change upstream results and is left to the FLORIS maintainers.
6. The FLORIS `gch`/`cc` full-flow output differs from `run()` at the rotor points when secondary steering,
   yaw-added recovery or transverse velocities are on. This is upstream behaviour, unrelated to this change.
7. The Jimenez one-turbine FLORIS vs FOXES RMSE is larger in the aligned view (`0.049` vs `0.023 m/s`). The cause
   was not investigated.
