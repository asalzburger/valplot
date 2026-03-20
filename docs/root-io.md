# ROOT I/O

`valplot.io.root` provides helpers based on `uproot`.

## Available helpers

- `read_hist1d(file_path, object_path)`
- `read_hist2d(file_path, object_path)`
- `hist1d_from_tree(file_path, tree_path, branch, bins, range=None, weight_branch=None, name=None)`
- `hist2d_from_tree(file_path, tree_path, x_branch, y_branch, bins, range=None, weight_branch=None, name=None)`
- `profile_from_tree(file_path, tree_path, x_branch, y_branch, bins, range=None, weight_branch=None, name=None)`
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

## Notes on band semantics

- `band_from_tree` computes:
  - central value per bin as the mean of `y`
  - lower/upper envelope per bin as min/max of `y`
  - `errors` as an RMS-like spread, useful with sigma-based band rendering
- In plotting:
  - `plot_band(..., spread="spread")` uses explicit `lower/upper`
  - `plot_band(..., spread="1sigma")` uses `values ± errors`
