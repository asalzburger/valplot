# Demos

This repository contains multiple runnable demos under `examples/`.

## `demo_root_plot.py`

Purpose:

- single-file showcase using `tests/data/tests_input.root`
- includes `hist1d`, `hist2d`, `profile`, `efficiency`, and ratio plotting

Run:

```bash
python examples/demo_root_plot.py
```

Outputs:

- `examples/output/overlay_hx_hy.png`
- `examples/output/hxy_heatmap.png`
- `examples/output/profiles.png`
- `examples/output/efficiency.png`
- `examples/output/ratio_hx_hy.png`

## `demo_overlay_from_trees.py` / `utilities/overlay_from_trees.py`

Purpose:

- overlay plots from multiple ROOT files/trees
- instruction-based CLI for quick comparisons
- demo script is a thin wrapper around `utilities/overlay_from_trees.py`

Run:

```bash
python examples/demo_overlay_from_trees.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --trees tree tree \
  --plots profile:ratio:x:y profile:band:x:y hist1d:x scatter:x:y
```

Instruction forms:

- `hist1d:<branch>`
- `hist1d:ratio:<branch>`
- `hist1d:band:<branch>`
- `profile:<x_branch>:<y_branch>`
- `profile:ratio:<x_branch>:<y_branch>`
- `profile:band:<x_branch>:<y_branch>`
- `restricted_profile:<x_branch>:<y_branch>:<restriction_branch>:<lo>:<hi>`
- `restricted_profile:ratio:<x_branch>:<y_branch>:<restriction_branch>:<lo>:<hi>`
- `restricted_profile:band:<x_branch>:<y_branch>:<restriction_branch>:<lo>:<hi>`
- `scatter:<x_branch>:<y_branch>`
- `band:<x_branch>:<y_branch>`

## `demo_style_showcase.py`

Purpose:

- compare style variants and color schemas
- demonstrates:
  - profile with error bars + ratio
  - profile with band + ratio
  - styled `hist1d` overlays
  - styled `hist2d` heatmaps

Run:

```bash
python examples/demo_style_showcase.py
```

Outputs are written to `examples/output/` with `style_*` prefixes.

## `demo_restricted_profile.py`

Purpose:

- unrestricted vs restricted profile ratio comparisons
- uses `tests/data/tests_restricted.root` with tree `restricted_profile` (branches: x, y, v0, v1)

Run:

```bash
python examples/demo_restricted_profile.py
```

Outputs:

- `restricted_profile_ratio_v1_v0_vs_x.png` (unrestricted)
- `restricted_profile_ratio_v1_v0_vs_y.png` (unrestricted)
- `restricted_profile_ratio_v1_v0_vs_x_zcut.png` (restricted: y ∈ [-4, 4])
