# ROOT I/O

`valplot.io.root` provides helpers based on `uproot`.

## Available helpers

- `read_hist1d(file_path, object_path)`
- `read_hist2d(file_path, object_path)`
- `hist1d_from_tree(file_path, tree_path, branch, bins, range=None, weight_branch=None, name=None)`
- `hist2d_from_tree(file_path, tree_path, x_branch, y_branch, bins, range=None, weight_branch=None, name=None)`
- `profile_from_tree(file_path, tree_path, x_branch, y_branch, bins, range=None, weight_branch=None, name=None)`
- `restricted_profile_from_tree(file_path, tree_path, x_branch, y_branch, restriction_branch, restriction_range, bins, range=None, weight_branch=None, name=None)`
- `restricted_band_from_tree(file_path, tree_path, x_branch, y_branch, restriction_branch, restriction_range, bins, range=None, name=None)`
- `scatter_from_tree(file_path, tree_path, x_branch, y_branch, name=None)`
- `band_from_tree(file_path, tree_path, x_branch, y_branch, bins, range=None, name=None)`

## Reading ROOT histogram objects

```python
from valplot.io.root import read_hist1d, read_hist2d

hx = read_hist1d("tests/data/tests_input.root", "hx")
hxy = read_hist2d("tests/data/tests_input.root", "hxy")
```

## Filling from a TTree

```python
from valplot.io.root import (
    band_from_tree,
    hist1d_from_tree,
    hist2d_from_tree,
    profile_from_tree,
    scatter_from_tree,
)

file_path = "tests/data/tests_input.root"
tree_path = "tree"

hx_tree = hist1d_from_tree(
    file_path,
    tree_path,
    branch="x",
    bins=50,
    range=(-5.0, 5.0),
)

hxy_tree = hist2d_from_tree(
    file_path,
    tree_path,
    x_branch="x",
    y_branch="y",
    bins=(50, 50),
    range=((-5.0, 5.0), (-5.0, 5.0)),
)

profx_tree = profile_from_tree(
    file_path,
    tree_path,
    x_branch="x",
    y_branch="y",
    bins=50,
    range=(-5.0, 5.0),
)

scatter_xy = scatter_from_tree(
    file_path,
    tree_path,
    x_branch="x",
    y_branch="y",
)

band_xy = band_from_tree(
    file_path,
    tree_path,
    x_branch="x",
    y_branch="y",
    bins=50,
    range=(-5.0, 5.0),
)
```

## Weighted filling

The tree helpers support an optional `weight_branch`.

```python
from valplot.io.root import profile_from_tree

weighted_profile = profile_from_tree(
    "tests/data/tests_input.root",
    "tree",
    x_branch="x",
    y_branch="y",
    bins=50,
    range=(-5.0, 5.0),
    weight_branch="weight",
    name="weighted_y_vs_x",
)
```

## Restricted profiles

A restricted profile applies a selection on a second variable before filling the profile. Use `restricted_profile_from_tree` when you want to bin in `x` and average `y`, but only include events where a third variable falls within a given range:

```python
from valplot.io.root import restricted_profile_from_tree

rp = restricted_profile_from_tree(
    "tests/data/tests_restricted.root",
    "restricted_profile",
    x_branch="x",
    y_branch="v0",
    restriction_branch="y",
    restriction_range=(-4.0, 4.0),
    bins=40,
    range=(-5.0, 5.0),
    name="v0_ycut",
)
```

The returned object has the same interface as `profile` and can be used with `plot`, `plot_ratio`, and `plot_band`. Restriction metadata is stored in `rp.metadata`.

## Notes on band semantics

- `band_from_tree` computes:
  - central value per bin as the mean of `y`
  - lower/upper envelope per bin as min/max of `y`
  - `errors` as an RMS-like spread, useful with sigma-based band rendering
- In plotting:
  - `plot_band(..., spread="spread")` uses explicit `lower/upper`
  - `plot_band(..., spread="1sigma")` uses `values ± errors`

## Overlay utility for profiles

For multi-file/tree overlays of `profile`-like objects (profiles and optional restricted selection), use `utilities/overlay_profiles.py` (also wrapped by `examples/demo_overlay_profiles.py`).

The utility builds:

- profile means (via `profile_from_tree` / `restricted_profile_from_tree`)
- optional band envelopes underneath (via `band_from_tree` / `restricted_band_from_tree`)
- optional ratio panel (via `plot_ratio`)

Example:

```bash
python utilities/overlay_profiles.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --input tree \
  --plot x:y \
  --range -5 5 \
  --band spread \
  --ratio \
  --output-dir examples/output
```

Ratio y-axis modes:
- omit `--ratio` => no ratio panel
- `--ratio` or `--ratio full` => ratio panel with full y-range
- `--ratio range:min_val:max_val` => restrict ratio panel y-axis

## Overlay utility for histogram objects

For multi-file overlays of ROOT histogram objects (`hist1d` and `efficiency`), use `utilities/overlay_hist.py`.

Example (`hist1d`):

```bash
python utilities/overlay_hist.py \
  --files tests/data/tests_input.root tests/data/tests_input.root \
  --kind hist1d \
  --input hx hy \
  --band 1sigma \
  --ratio full \
  --output-dir examples/output
```
