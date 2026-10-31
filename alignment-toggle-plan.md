# Plan: "Default" vs "Aligned" toggle for the wake model comparison site

## Goal

Let site visitors switch every page between two configurations of the same comparison:

- **Default**: the solver adapters as they are at `HEAD` (models not well aligned). This view loads first.
- **Aligned**: the current working-tree settings (models very nearly aligned).

The aligned settings must be expressible in windIO input files, and FLORIS must accept its rotor-averaging settings from its input file so windIO can drive them.

Repositories involved:

| Repo | Path | Work |
|---|---|---|
| wcomp | `/Users/rmudafor/Development/wcomp` | adapters, case files, dataset generator, site |
| windIO | `/Users/rmudafor/Development/windIO` | plant schema |
| FLORIS | `/Users/rmudafor/Development/floris` | configurable rotor averaging |

## Decisions already made

- Default means the `HEAD` adapter settings.
- The default view loads first, so default pages keep today's URLs and aligned pages live under an `aligned/` prefix.
- The toggle applies to every page: homepage, all 12 case pages, rotor averaging, turbine performance.
- FLORIS defaults go back to upstream. The local FLORIS edits (quadratic-mean default, radius ratio 1.0, separate thrust method) were alignment research: they are a reference for the aligned settings and must not leak into the default case.
- The windIO block is `attributes.analyses`.
- FOXES keeps `grid16` (its default) in both views; the aligned view documents it as a residual difference.
- FLORIS and windIO stay editable installs of the local checkouts. No `setup.py` pin changes.

## Findings that shape the plan

1. **Aligned vs default settings.** The differences are:

   | Setting | Default (`HEAD`) | Aligned |
   |---|---|---|
   | Deficit reference wind speed | FLORIS: freestream (`sosfs`, not configurable). FOXES: `ws_quadratic` (local). PyWake: `use_effective_ws=True` (local) | All three: freestream. FOXES `ws_quadratic_amb_target`, PyWake `use_effective_ws=False` |
   | Rotor grid | FLORIS: `turbine_grid` 3x3 square. FOXES: `grid16`. PyWake: `GridRotorAvg()` | FLORIS: `turbine_cubature_grid`, 9 points. PyWake: `CGIRotorAvg(n=9)`. FOXES: `grid16` (no 9-point equivalent used, a residual) |
   | Power/thrust averaging | FLORIS: cubic mean. FOXES, PyWake: linear | Linear for all (FLORIS linear cubature) |

   Already committed and shared by both views: FLORIS `kd = beta / 2` for Jimenez, TurbOPark mirror wakes disabled in FLORIS, constant vertical wind profile in FLORIS.

2. **Local FLORIS is mid-edit and currently broken for cubature.** `TurbineCubatureGrid.average_method` is still `"simple-cubature"`, but `average_velocity()` was renamed to accept `"linear-cubature"`. Running it raises `Incorrect method given.` (verified). `tests/rotor_velocity_unit_test.py` also still imports the removed `simple_cubature`. The aligned FLORIS results therefore cannot currently be regenerated.

3. **Local FLORIS changed defaults, not just options.**
   - `TurbineGrid.average_method`: `cubic-mean` to `quadratic-mean`.
   - New `thrust_average_method` on both grids, used by `solver.py` and `floris_model.py`.
   - `TurbineGrid` `radius_ratio`: `0.5` to `1.0`. With 1.0 the corner points of the 3x3 grid fall outside the rotor disk. This is research only and is not exposed as an option: the aligned view uses the cubature grid, where the ratio does not apply.
   - With these defaults the "default" FLORIS in this repo no longer reproduces the committed `HEAD` dataset (cubic mean, ratio 0.5). The defaults are restored (see the FLORIS section).

4. **windIO schema does not describe the wcomp case files.**
   - wcomp case files use `attributes.analyses` (`yaw_angles`, `wake_model.velocity`, `wake_model.deflection`). The schema only has `attributes.analysis` (singular) with a different shape (`wind_deficit_model`, `rotor_averaging`, `superposition_model`, ...).
   - `windIO.validate` is restrictive (`additionalProperties: false`), and the 12 case files already fail for unrelated reasons (`air_density` under `wind_resource`, `wind_farm` shape). Full-file validity is therefore out of scope; only the `analyses` block is made valid.
   - The existing `analysis.rotor_averaging` already has `wind_speed_exponent_for_power` and `wind_speed_exponent_for_ct`. Exponent 1/2/3 maps directly onto FLORIS linear/quadratic/cubic averaging.
   - The existing `analysis.wind_deficit_model.use_effective_ws` has an inverted description ("use freestream").

5. **Packaging.** `setup.py` pins `floris==v4.6.6` and `windIO>=2`, but the environment already has both installed editable from the local checkouts, and that stays. The new settings need those checkouts. CI builds the site from the committed dataset with no Python, so only the developer environment is affected.

6. **Repo state.** 131 dataset files are staged (the aligned state) along with unstaged adapter edits. Restructuring the dataset on top of this would be hard to review.

## Design

### windIO schema: `attributes.analyses`

Add `analyses` to `windIO/schemas/plant/wind_energy_system.yaml`, matching the keys the wcomp case files already use, plus the new settings. Shared sub-schemas go in `$defs` and are referenced by both `analysis` and `analyses` so the vocabulary is not duplicated.

```yaml
attributes:
  analyses:
    yaw_angles: [10.0, 10.0, 0.0, 0.0]        # existing, now in the schema
    wake_model:                                # existing, now in the schema
      velocity:   {name: jensen, parameters: {alpha: 0.1}}
      deflection: {name: jimenez, parameters: {beta: 0.1}}
    superposition:                             # new
      ws_superposition: Squared
      deficit_reference_wind_speed: freestream # freestream | local
    rotor_averaging:                           # extended
      grid: cubature                           # center | square | cubature
      n_points: 9                              # total points (cubature)
      wind_speed_exponent_for_power: 1         # 1 linear, 2 quadratic, 3 cubic
      wind_speed_exponent_for_ct: 1
```

Notes:

- `deficit_reference_wind_speed` replaces the boolean `use_effective_ws` in the new block because a named enum avoids the inverted-flag confusion. The legacy field in `analysis` is left alone, with its description corrected.
- `n_points` is the cross-solver quantity. For FLORIS it maps to `turbine_grid_points = sqrt(n_points)` and must be a perfect square. For PyWake it maps to `CGIRotorAvg(n)`.
- Square grids keep `n_x_grid_points` / `n_y_grid_points`.
- Every new key is optional. Omitting a key means "each solver's own legacy behaviour", which is exactly the default view.

Also in windIO:

- Add a valid example (aligned analyses) under `windIO/examples/plant/` and cover it in `test_all_plant_examples.py`.
- Add schema unit tests for the `analyses` block: accepts the wcomp default and aligned blocks, rejects an unknown `deficit_reference_wind_speed` and a non-integer `n_points`.
- Update `docs/source/plant_schema.rst` if it enumerates attributes.

### FLORIS: configurable rotor averaging

Make the averaging settings part of the `solver` block of the FLORIS input file.

```yaml
solver:
  type: turbine_cubature_grid     # or turbine_grid
  turbine_grid_points: 3
  power_average_method: linear-cubature   # new, optional (renamed from the grid's `average_method`)
  thrust_average_method: linear-cubature  # new, optional
```

Changes in `floris/core/grid.py` and `floris/core/core.py`:

- Rename the grid attribute `average_method` to `power_average_method` (pairing with `thrust_average_method`) and update every reader: the `average_velocity(...)` calls in `solver.py` and `floris_model.turbine_average_velocities`, plus the wcomp references in `wcomp/rotor_average.py`.
- Convert `power_average_method` and `thrust_average_method` from class attributes to `attrs` fields with defaults and a validator.
- `core.py` passes the optional keys from `self.solver` when it builds the grid.
- Validate pairs: mean methods (`linear-mean`, `quadratic-mean`, `cubic-mean`) only with `turbine_grid`; cubature methods (`linear-cubature`, `quadratic-cubature`, `cubic-cubature`) only with `turbine_cubature_grid`. The error lists valid choices.
- Fix the rename bug: `TurbineCubatureGrid` default becomes `"linear-cubature"`; remove the stale TODO (a `quadratic-cubature` method now exists).
- Defaults: restore the upstream behaviour. `TurbineGrid`: `cubic-mean` for power and thrust, `radius_ratio` back to the hard-coded `0.5` (not exposed). `TurbineCubatureGrid`: `linear-cubature` (the renamed upstream `simple-cubature`) for power and thrust. An input file that does not mention the new keys behaves as upstream. Anything else is set explicitly in the input file.
- Keep the renamed averaging functions and the new `quadratic-*` methods (the research edits are retained as options), but nothing that changes default numbers.
- Audit the callers that rely on `average_velocity()`'s own default (`solver.py` around lines 552 and 821, `empirical_gauss_solver`, `floris_model.turbine_average_velocities`) and decide per call whether they should follow the grid's method. Keep behaviour identical for default inputs.
- Update `tests/rotor_velocity_unit_test.py` (renamed functions), add tests for the new methods and the config path, add a regression test that default inputs reproduce the previous results, and document the keys in `default_inputs.yaml` and the input reference docs.
- Work on a branch in the FLORIS repo.

### wcomp adapters and case files

- Adapters (`floris_interface.py`, `foxes_interface.py`, `pywake_interface.py`) read the new `attributes.analyses` keys and map them to solver settings. No `alignment` argument is needed: the input file fully determines the configuration.

  | windIO key | FLORIS | FOXES | PyWake |
  |---|---|---|---|
  | `superposition.deficit_reference_wind_speed` | `freestream` only; `local` raises (`sosfs` cannot do it) | `freestream`: `ws_quadratic_amb_target`; `local`: `ws_quadratic` | `use_effective_ws = (value == "local")` |
  | `rotor_averaging.grid` + `n_points` | `turbine_grid` / `turbine_cubature_grid`, `turbine_grid_points = sqrt(n)` | `grid16` kept; other values noted as unsupported | `GridRotorAvg` / `CGIRotorAvg(n)` |
  | `wind_speed_exponent_for_power` / `_ct` | `power_average_method`, `thrust_average_method` | recorded only (REWS is linear) | recorded only (linear) |

- Keys omitted: each adapter applies its pinned legacy default (FLORIS: `turbine_grid` 3x3 with FLORIS' own defaults, i.e. `cubic-mean` for power and thrust; FOXES: `ws_quadratic`, `grid16`; PyWake: `use_effective_ws=True`, `GridRotorAvg()`). These are `HEAD` behaviour written down in one place.
- A setting a solver cannot honour is reported, not silently ignored. It is surfaced in the per-case implementation notes on the site (for example "FOXES keeps `grid16`; no 9-point cubature").
- Case files: for each of the 12 cases add `wind_energy_system_aligned.yaml` next to the existing (default) file. It is a copy that adds the aligned `superposition` and `rotor_averaging` keys. A test asserts it differs from the default file only in those keys. Committed per-case files are preferred over an overlay applied at load time because FOXES reads the file path directly (to be verified).
- `wcomp/comparison_metadata.py`: add an `ALIGNMENTS` registry (id, label, description, yaml file name). Build `SOFTWARE_NOTES` per alignment from the actual settings in the yaml instead of fixed text.

### Dataset

New layout (aligned = the current data moved down one level; default regenerated):

```
dataset/
  manifest.json               # lists alignments and their cases
  models.json  schema.json    # shared
  default/
    cases/<scenario>__<model>/...
    rotor_average.json
    turbine_performance.json
  aligned/
    cases/...  rotor_average.json  turbine_performance.json
```

- `compute_case` / `write_case` / `generate` take an alignment; CLI flag `--alignment default|aligned|all` (default `all`). Same flag on `wcomp.rotor_average` and `wcomp.turbine_performance`, which build their FLORIS/PyWake methods from the same alignment settings instead of hard-coded grids.
- `Case` gains `alignment`; `Manifest` gains an `alignments` array.
- Update path matching in `wcomp/dataset_validation.py` and `site/scripts/validate-dataset.mjs` (the `cases/<id>/...` index positions shift by one), plus `dataset/schema.json` and the dataset tests.
- Size: `dataset/` is 56 MB, so two alignments is about 110 MB in git. Mitigation if needed: store an alignment's case only where it differs from the other, with the site falling back.

### Site

- Routes. Default at today's URLs, aligned mirrored under `aligned/`:

  | Default | Aligned |
  |---|---|
  | `/` | `/aligned/` |
  | `/compare/<case>/` | `/aligned/compare/<case>/` |
  | `/compare/rotor-averaging/` | `/aligned/compare/rotor-averaging/` |
  | `/compare/turbine-performance/` | `/aligned/compare/turbine-performance/` |

  Page bodies move into shared components under `site/src/components/`; the `pages/` files become thin wrappers that pass `alignment`.
- `site/src/lib/dataset.js`: every loader takes an alignment. `getStaticPaths` emits both. Client `fetch` paths use `dataset/<alignment>/cases/<id>/`.
- `AlignmentToggle` component in `Layout.astro`: a two-option control ("Default" / "Aligned") that links to the counterpart URL for the current page and keeps the URL hash. Keep the `base` trailing-slash convention.
- Banner on each view stating what the view is, with the list of differing settings from `ALIGNMENTS`. The default view says that differences there include configuration differences, not only model differences.
- Text that currently assumes the aligned data must be made alignment-aware or data-driven:
  - `modelGuidance` and `AGREE_RMSE` in `compare/[case].astro` (for example "the three profiles coincide") are only valid for aligned. Tag each statement with the alignment it applies to; for default, use statements generated from the default metrics plus the settings differences.
  - Homepage TLDR bullets in `index.astro` (rotor-averaging statement, worst RMSE, growth with turbine count) are already computed from data; check the hard-coded wording still holds for default.
  - Rotor-averaging and turbine-performance pages: their per-solver method descriptions come from the dataset, so they switch with the data. Turbine performance is expected to be nearly identical in both views; the page says so instead of hiding the toggle.
- Optional: a small "effect of alignment" table on each case page (streamwise RMSE per software pair, default vs aligned), since both datasets are available at build time.
- `site/scripts/copy-dataset.mjs` copies the new layout.

### Documentation

- README: new `--alignment` commands, dataset layout, and the FLORIS/windIO branch requirement.
- `comparison-notes.md`: add the settings table and the default-vs-aligned rationale.

## Execution order

1. **wcomp checkpoint.** Commit the current aligned working tree as-is so the dataset restructure diff is reviewable.
2. **FLORIS.** Fix the rename bug, add the solver settings and tests (branch).
3. **windIO.** Add the `analyses` schema, example, tests (branch).
4. **wcomp backend.** Adapters, aligned case files, `ALIGNMENTS`, dataset layout and validation, rotor-average and turbine-performance generators.
5. **Generate data.** Regenerate `default` and `aligned`.
6. **Site.** Components, routes, toggle, alignment-aware text.
7. **Docs.**

## Verification

- FLORIS: full test suite, including a regression that default inputs reproduce upstream results.
- windIO: schema tests and the example-file test.
- wcomp:
  - Adapter mapping unit tests (settings to FLORIS solver dict, FOXES superposition string, PyWake `use_effective_ws` and rotor model).
  - Regenerated `default` dataset matches the committed `HEAD` dataset within tolerance. This is the key check that exposing the FLORIS settings and restoring its defaults preserved the old behaviour.
  - Regenerated `aligned` dataset matches the current staged data within tolerance.
  - Dataset schema tests for both alignments.
- Site: `npm run build --prefix site` passes the dataset validator and builds both views; spot-check in a browser (a Jensen four-turbine case, Bastankhah 2016, rotor averaging, turbine performance, homepage) that the toggle preserves the page and that default loads first.

## Resolved questions

1. **FLORIS defaults.** Back to upstream; the local research edits are reference only.
2. **windIO placement.** `attributes.analyses`.
3. **FOXES rotor grid.** `grid16` (FOXES's default) in both views.
4. **Dependencies.** Editable installs of the local FLORIS and windIO checkouts, already in place.

## Remaining detail to confirm during implementation

- Because FOXES stays on `grid16`, the aligned yaml's `rotor_averaging` (`n_points: 9`) is not honoured by FOXES. The adapter reports that, and the site's FOXES notes say so. If you prefer the schema value not to claim 9 points for all solvers, the alternative is to omit `n_points` and map FLORIS and PyWake from a named `grid` choice only.
- Whether FOXES reads the case file by path (which would rule out an overlay applied in memory). To be checked when writing the adapters.
