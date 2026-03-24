# valplot

Small plotting and validation helpers for histogram-like data, with optional ROOT I/O via `uproot`.

## What this project provides

- Typed containers for:
  - `hist1d`
  - `hist2d`
  - `profile`
  - `restricted_profile` (profile with selection on a second variable)
  - `efficiency`
  - `scatter`
  - `band`
- Backend-agnostic plotting:
  - `plot(...)` for single objects
  - `plot_ratio(...)` for overlaid 1D/profile plots with a ratio panel
  - `plot_scatter(...)` for point-wise overlays
  - `plot_band(...)` for spread / sigma bands
- ROOT helpers in `valplot.io.root`:
  - read TH1/TH2 objects
  - fill 1D/2D histograms, profiles, restricted profiles, scatters, and bands from TTree branches
- Utility scripts:
  - `utilities/overlay_from_trees.py` for instruction-driven multi-file/tree overlays

## Installation

This repository currently does not ship packaging metadata (`pyproject.toml`) yet.
For local usage, install dependencies in your environment and import from the repo checkout.

Typical requirements:

- core: `numpy`
- plotting: `matplotlib` (and optionally `plotly`)
- ROOT I/O: `uproot`

## Quick example

```python
from valplot import Decoration, hist1d, plot, plot_ratio

hx = hist1d(edges=[0, 1, 2, 3], counts=[10, 7, 3], name="hx")
hy = hist1d(edges=[0, 1, 2, 3], counts=[8, 6, 4], name="hy")

# Single panel
fig, _ = plot(
    hx,
    decoration=Decoration(
        title="Distribution",
        x_label="x",
        y_label="Entries",
        label="hx",
        show_grid=True,
    ),
    backend="matplotlib",
)

# Overlay + ratio panel (hy / hx in lower panel)
fig_ratio, _ = plot_ratio(
    [hx, hy],
    [
        Decoration(title="Comparison with ratio", x_label="x", y_label="Entries", label="hx"),
        Decoration(label="hy", line_style="--"),
    ],
)
```

## Demos
### ROOT plotting demo

`examples/demo_root_plot.py` uses `tests/data/tests_input.root` and generates:

- `examples/output/overlay_hx_hy.png`
- `examples/output/hxy_heatmap.png`
- `examples/output/profiles.png`
- `examples/output/efficiency.png`
- `examples/output/ratio_hx_hy.png`

Run:

```bash
python examples/demo_root_plot.py
```

### Multi-file overlay CLI demo

`examples/demo_overlay_from_trees.py` reuses `utilities/overlay_from_trees.py` for instruction-driven plotting across multiple files/trees.

Examples:

```bash
python examples/demo_overlay_from_trees.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --trees tree tree \
  --plots profile:ratio:x:y profile:band:x:y hist1d:x scatter:x:y
```

### Style showcase demo

`examples/demo_style_showcase.py` demonstrates style variants and color schemas for:

- profile with error bars + ratio
- profile with band + ratio
- hist1 style overlays
- hist2 colormap styles

Run:

```bash
python examples/demo_style_showcase.py
```

### Restricted profile demo

`examples/demo_restricted_profile.py` shows unrestricted and restricted profile ratio comparisons using `tests/data/tests_restricted.root`:

- v1/v0 vs x and vs y (unrestricted)
- v1/v0 vs x with y ∈ [-4, 4] (restricted)

Run:

```bash
python examples/demo_restricted_profile.py
```

## Documentation

- [`docs/quickstart.md`](docs/quickstart.md)
- [`docs/root-io.md`](docs/root-io.md)
- [`docs/api.md`](docs/api.md)
- [`docs/demos.md`](docs/demos.md)
- [`docs/howto.md`](docs/howto.md)
