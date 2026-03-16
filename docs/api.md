# API Overview

This page summarizes the public surface currently exported by `valplot`.

## Top-level exports

From `valplot`:

- containers:
  - `hist1d`
  - `hist2d`
  - `profile`
  - `efficiency`
- drawing:
  - `Decoration`
  - `plot`
  - `plot_ratio`

## `Decoration`

`Decoration` controls labels and style options for plotting. Common fields:

- labels: `title`, `x_label`, `y_label`, `label`
- line style: `color`, `line_style`, `line_width`, `alpha`
- marker style: `marker`, `marker_size`
- extras: `show_grid`, `show_legend`, `cmap`

## `plot`

```python
plot(
    histogram,
    decoration=None,
    *,
    backend="matplotlib",
    figure=None,
    axis=None,
    row=None,
    col=None,
)
```

- Supports: `hist1d`, `hist2d`, `profile`, `efficiency`.
- Backends:
  - `matplotlib`
  - `plotly`

## `plot_ratio`

```python
plot_ratio(
    histograms,
    decorations=None,
    *,
    backend="matplotlib",
)
```

- Supports: `hist1d` and `profile`.
- Uses the first object as denominator.
- Ratio panel excludes the first object (no self-ratio line).
- Current backend support: `matplotlib` only.
