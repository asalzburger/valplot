# API Overview

This page summarizes the public surface currently exported by `valplot`.

## Top-level exports

From `valplot`:

- containers:
  - `hist1d`
  - `hist2d`
  - `profile`
  - `restricted_profile`
  - `efficiency`
  - `scatter`
  - `band`
- drawing:
  - `Decoration`
  - `plot`
  - `plot_ratio`
  - `plot_scatter`
  - `plot_band`

## `Decoration`

`Decoration` controls labels and style options for plotting. Common fields:

- labels: `title`, `x_label`, `y_label`, `label`
- line style: `color`, `line_style`, `line_width`, `alpha`
- marker style: `marker`, `marker_size`
- extras: `show_grid`, `show_legend`, `cmap`, `band_alpha`

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

- Supports: `hist1d`, `hist2d`, `profile`, `restricted_profile`, `efficiency`, `scatter`, `band`.
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

- Supports: `hist1d`, `profile`, and `restricted_profile` (profile-like types can be mixed).
- Uses the first object as denominator.
- Ratio panel excludes the first object (no self-ratio line).
- Current backend support: `matplotlib` only.

## `plot_scatter`

```python
plot_scatter(
    points,
    decoration=None,
    *,
    backend="matplotlib",
    figure=None,
    axis=None,
)
```

- Supports: `scatter`.
- Backends:
  - `matplotlib`
  - `plotly`

## `plot_band`

```python
plot_band(
    histograms,
    decorations=None,
    *,
    spread=None,
    show_values=True,
    backend="matplotlib",
    figure=None,
    axis=None,
)
```

- Supports: `hist1d`, `profile`, `restricted_profile`, `band`.
- `spread` options:
  - for `hist1d`/`profile`: sigma mode (`"1sigma"`, `"2sigma"`, ...)
  - for `band`: `"spread"` (default) or sigma mode
- `show_values`: when `False`, omit the central value line and draw only the filled envelope.
- Current backend support: `matplotlib` only.
