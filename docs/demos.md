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

## `demo_overlay_profiles.py` / `utilities/overlay_profiles.py`

Purpose:

- overlay ROOT `profile`-like plots from multiple files
- supports optional:
  - `--band` (draw band underneath profile means, with optional `spread`/`<N>sigma`)
  - `--ratio` (ratio panel below; modes: `full` or `range:min_val:max_val`)
  - `--restrict` (restricted profile/band with a branch selection)

Run:

```bash
python examples/demo_overlay_profiles.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --input tree \
  --plot x:y \
  --band spread \
  --ratio \
  --show
```

CLI notes:

- `--plot` value is `x:y` and create profile plots of `y` vs `x`
- `--x-label` optional x-axis label (supports LaTeX/mathtext, e.g. `'$\\alpha$'`)
- `--y-label` optional y-axis label (supports LaTeX/mathtext, e.g. `'$\\beta$'`)
- `--no-title` switch off the title on the top panel
- `--range LO HI` override the x-axis range used for binning/plotting
- `--restrict` syntax is `branch:lo:hi` (e.g. `y:-4:4`)
- `--band` optionally takes `spread` or `<N>sigma` (if omitted, uses default mode)
- `--ratio` (no value) => `full` (no y-axis restriction)
- `--ratio full` => same as `--ratio`
- `--ratio range:min_val:max_val` => restrict the ratio panel y-axis
- `--labels` optionally provides per-input labels (length must match `--files`). If omitted (or set to `None`), uses file stems. Ratio panel legend is always suppressed.
- `--show` keeps the script running and shows the resulting canvas

Greek/LaTeX example:

```bash
python examples/demo_overlay_profiles.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --input tree \
  --plot x:y \
  --x-label '$\\alpha$' \
  --y-label '$\\mu$' \
  --no-title \
  --band spread \
  --ratio
```

## `utilities/overlay_hist.py`

Purpose:

- overlay 1D ROOT histogram-like objects across files
- supports `hist1d` and `efficiency`
- optional `--ratio` and `--band` modes, plus labels/title/axis customization

Run (`hist1d`):

```bash
python utilities/overlay_hist.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --kind hist1d \
  --input hx hy \
  --band 1sigma \
  --ratio full \
  --show
```

Run (`efficiency`, expects TEfficiency objects):

```bash
python utilities/overlay_hist.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --kind efficiency \
  --input eff_x eff_x \
  --ratio range:0.5:1.5 \
  --show
```

Demo wrapper:

```bash
python examples/demo_overlay_hist.py
```

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
