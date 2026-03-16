# valplot

Small plotting and validation helpers for histogram-like data, with optional ROOT I/O via `uproot`.

## What this project provides

- Typed containers for:
  - `hist1d`
  - `hist2d`
  - `profile`
  - `efficiency`
- Backend-agnostic plotting:
  - `plot(...)` for single objects
  - `plot_ratio(...)` for overlaid 1D/profile plots with a ratio panel
- ROOT helpers in `valplot.io.root`:
  - read TH1/TH2 objects
  - fill 1D/2D histograms and profiles from TTree branches

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

## Example script

See `examples/demo_root_plot.py` for a complete demo using `tests/data/tests_input.root`.

It generates:

- `examples/output/overlay_hx_hy.png`
- `examples/output/hxy_heatmap.png`
- `examples/output/profiles.png`
- `examples/output/efficiency.png`
- `examples/output/ratio_hx_hy.png`

Run:

```bash
python examples/demo_root_plot.py
```

## Documentation

- [`docs/quickstart.md`](docs/quickstart.md)
- [`docs/root-io.md`](docs/root-io.md)
- [`docs/api.md`](docs/api.md)
