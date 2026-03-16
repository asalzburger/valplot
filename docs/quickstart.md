# Quickstart

This project works with a small set of histogram container classes and plotting helpers.

## Core objects

- `hist1d`: 1D binned counts with errors
- `hist2d`: 2D binned counts with errors
- `profile`: per-bin means with uncertainties
- `efficiency`: binomial pass/total representation

## Basic plotting

```python
from valplot import Decoration, hist1d, plot

h = hist1d(
    edges=[0.0, 1.0, 2.0, 3.0],
    counts=[12.0, 8.0, 3.0],
    name="sample",
)

fig, ax = plot(
    h,
    decoration=Decoration(
        title="Sample histogram",
        x_label="Observable",
        y_label="Entries",
        label="sample",
        show_grid=True,
        color="tab:blue",
    ),
    backend="matplotlib",
)
```

## Overlay + ratio plotting

Use `plot_ratio` for `hist1d` and `profile` objects.

```python
from valplot import Decoration, hist1d, plot_ratio

hx = hist1d(edges=[0, 1, 2, 3], counts=[10, 7, 3], name="hx")
hy = hist1d(edges=[0, 1, 2, 3], counts=[8, 6, 4], name="hy")

fig, (ax_top, ax_ratio) = plot_ratio(
    [hx, hy],
    [
        Decoration(title="hx vs hy", x_label="x", y_label="Entries", label="hx"),
        Decoration(label="hy", line_style="--"),
    ],
    backend="matplotlib",
)
```

Notes:

- The first input object is used as denominator for ratios.
- The first object is not plotted in the ratio panel (no self-ratio).
- The lower panel height is one third of the upper panel.

## See also

- ROOT integration examples: [`root-io.md`](root-io.md)
- Complete script: [`../examples/demo_root_plot.py`](../examples/demo_root_plot.py)
- Multi-file CLI script: [`../examples/demo_overlay_from_trees.py`](../examples/demo_overlay_from_trees.py)
