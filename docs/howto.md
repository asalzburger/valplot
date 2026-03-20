# How-To Recipes

Practical workflows for common tasks.

## Create a ratio plot

```python
from valplot import Decoration, plot_ratio

fig, (ax_top, ax_ratio) = plot_ratio(
    [h_ref, h_cmp],
    [
        Decoration(title="Comparison", x_label="x", y_label="Entries", label="reference"),
        Decoration(label="comparison", line_style="--"),
    ],
)
```

Notes:

- first object is denominator
- denominator is not drawn in the ratio panel

## Draw sigma bands around a profile

```python
from valplot import Decoration, plot_band

fig, ax = plot_band(
    [profile_obj],
    [Decoration(title="Profile 1-sigma band", color="tab:blue", fill_color="tab:blue", band_alpha=0.3)],
    spread="1sigma",
)
```

## Draw min/max spread bands from tree data

```python
from valplot.io.root import band_from_tree
from valplot import Decoration, plot_band

b = band_from_tree("file.root", "tree", x_branch="x", y_branch="y", bins=40, range=(-5, 5))
fig, ax = plot_band(
    [b],
    [Decoration(title="Spread band", color="tab:green", fill_color="tab:green", band_alpha=0.25)],
    spread="spread",
)
```

## Overlay scatter plots from trees

```python
from valplot.io.root import scatter_from_tree
from valplot import Decoration, plot_scatter

s1 = scatter_from_tree("a.root", "tree", "x", "y", name="sample A")
s2 = scatter_from_tree("b.root", "tree", "x", "y", name="sample B")

fig, ax = plot_scatter(s1, Decoration(title="Scatter overlay", x_label="x", y_label="y", label="A", marker="o"))
plot_scatter(s2, Decoration(label="B", marker="x", color="tab:red"), axis=ax)
```

## Stamp a logo onto an SVG plot

Use `utilities/stamp_svg.py` after exporting your figure as SVG:

```bash
python utilities/stamp_svg.py \
  --input overlay_hx_hy.svg \
  --stamp resources/sd/super_duper.svg \
  --outout overlay_hx_hy_sd.svg \
  --location 0.15 0.3 \
  --size 0.2
```

Parameters:

- `--location X Y`: fractions of input width/height from top-left
- `--size`: stamp width as a fraction of input width
