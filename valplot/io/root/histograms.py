"""ROOT histogram adapters and TTree/RNtuple fillers."""

from __future__ import annotations

from typing import Any

import numpy as np

from ...histograms import hist1d, hist2d, profile


def _import_uproot():
    try:
        import uproot
    except ImportError as exc:  # pragma: no cover - exercised by users without optional dependency
        raise ImportError("uproot is required for ROOT I/O. Install it with `pip install uproot`.") from exc
    return uproot


def hist1d_from_uproot(obj: Any, name: str | None = None) -> hist1d:
    """Build a ``hist1d`` from a TH1-like uproot object."""
    counts, edges = obj.to_numpy(flow=False)
    counts = np.asarray(counts, dtype=float)
    edges = np.asarray(edges, dtype=float)

    underflow = 0.0
    overflow = 0.0
    try:
        flow_counts, _ = obj.to_numpy(flow=True)
        flow_counts = np.asarray(flow_counts, dtype=float)
        if flow_counts.shape[0] == counts.shape[0] + 2:
            underflow = float(flow_counts[0])
            overflow = float(flow_counts[-1])
    except Exception:
        pass

    errors = None
    try:
        variances = obj.variances(flow=False)
        if variances is not None:
            errors = np.sqrt(np.clip(np.asarray(variances, dtype=float), a_min=0.0, a_max=None))
    except Exception:
        errors = None

    return hist1d(
        edges=edges,
        counts=counts,
        errors=errors,
        underflow=underflow,
        overflow=overflow,
        name=name,
    )


def hist2d_from_uproot(obj: Any, name: str | None = None) -> hist2d:
    """Build a ``hist2d`` from a TH2-like uproot object."""
    counts, x_edges, y_edges = obj.to_numpy(flow=False)
    counts = np.asarray(counts, dtype=float)
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)

    underflow = 0.0
    overflow = 0.0
    try:
        flow_counts, _, _ = obj.to_numpy(flow=True)
        flow_counts = np.asarray(flow_counts, dtype=float)
        if flow_counts.shape[0] == counts.shape[0] + 2 and flow_counts.shape[1] == counts.shape[1] + 2:
            underflow = float(np.sum(flow_counts[0, :]) + np.sum(flow_counts[-1, :]))
            overflow = float(np.sum(flow_counts[:, 0]) + np.sum(flow_counts[:, -1]))
    except Exception:
        pass

    errors = None
    try:
        variances = obj.variances(flow=False)
        if variances is not None:
            errors = np.sqrt(np.clip(np.asarray(variances, dtype=float), a_min=0.0, a_max=None))
    except Exception:
        errors = None

    return hist2d(
        x_edges=x_edges,
        y_edges=y_edges,
        counts=counts,
        errors=errors,
        underflow=underflow,
        overflow=overflow,
        name=name,
    )


def read_hist1d(file_path: str, object_path: str) -> hist1d:
    """Read a TH1-like object from a ROOT file."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        return hist1d_from_uproot(root_file[object_path], name=object_path)


def read_hist2d(file_path: str, object_path: str) -> hist2d:
    """Read a TH2-like object from a ROOT file."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        return hist2d_from_uproot(root_file[object_path], name=object_path)


def hist1d_from_tree(
    file_path: str,
    tree_path: str,
    branch: str,
    bins: int | np.ndarray | list[float],
    range: tuple[float, float] | None = None,
    weight_branch: str | None = None,
    name: str | None = None,
) -> hist1d:
    """Create ``hist1d`` by filling from TTree/RNtuple arrays."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        tree = root_file[tree_path]
        requested = [branch] if weight_branch is None else [branch, weight_branch]
        arrays = tree.arrays(requested, library="np")
        values = np.asarray(arrays[branch], dtype=float)
        weights = None if weight_branch is None else np.asarray(arrays[weight_branch], dtype=float)

    counts, edges = np.histogram(values, bins=bins, range=range, weights=weights)
    counts = np.asarray(counts, dtype=float)
    edges = np.asarray(edges, dtype=float)

    if weights is None:
        errors = np.sqrt(np.clip(counts, a_min=0.0, a_max=None))
    else:
        sumw2, _ = np.histogram(values, bins=edges, weights=np.square(weights))
        errors = np.sqrt(np.clip(np.asarray(sumw2, dtype=float), a_min=0.0, a_max=None))

    return hist1d(edges=edges, counts=counts, errors=errors, name=name or branch)


def hist2d_from_tree(
    file_path: str,
    tree_path: str,
    x_branch: str,
    y_branch: str,
    bins: tuple[int | np.ndarray | list[float], int | np.ndarray | list[float]],
    range: tuple[tuple[float, float], tuple[float, float]] | None = None,
    weight_branch: str | None = None,
    name: str | None = None,
) -> hist2d:
    """Create ``hist2d`` by filling from TTree/RNtuple arrays."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        tree = root_file[tree_path]
        requested = [x_branch, y_branch] if weight_branch is None else [x_branch, y_branch, weight_branch]
        arrays = tree.arrays(requested, library="np")
        x_values = np.asarray(arrays[x_branch], dtype=float)
        y_values = np.asarray(arrays[y_branch], dtype=float)
        weights = None if weight_branch is None else np.asarray(arrays[weight_branch], dtype=float)

    counts, x_edges, y_edges = np.histogram2d(
        x_values,
        y_values,
        bins=bins,
        range=range,
        weights=weights,
    )
    counts = np.asarray(counts, dtype=float)
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)

    if weights is None:
        errors = np.sqrt(np.clip(counts, a_min=0.0, a_max=None))
    else:
        sumw2, _, _ = np.histogram2d(
            x_values,
            y_values,
            bins=(x_edges, y_edges),
            weights=np.square(weights),
        )
        errors = np.sqrt(np.clip(np.asarray(sumw2, dtype=float), a_min=0.0, a_max=None))

    return hist2d(x_edges=x_edges, y_edges=y_edges, counts=counts, errors=errors, name=name or f"{x_branch}_{y_branch}")


def profile_from_tree(
    file_path: str,
    tree_path: str,
    x_branch: str,
    y_branch: str,
    bins: int | np.ndarray | list[float],
    range: tuple[float, float] | None = None,
    weight_branch: str | None = None,
    name: str | None = None,
) -> profile:
    """Create ``profile`` by filling from TTree/RNtuple arrays."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        tree = root_file[tree_path]
        requested = [x_branch, y_branch] if weight_branch is None else [x_branch, y_branch, weight_branch]
        arrays = tree.arrays(requested, library="np")
        x_values = np.asarray(arrays[x_branch], dtype=float)
        y_values = np.asarray(arrays[y_branch], dtype=float)
        weights = None if weight_branch is None else np.asarray(arrays[weight_branch], dtype=float)

    if weights is None:
        sumw, edges = np.histogram(x_values, bins=bins, range=range)
        sumwy, _ = np.histogram(x_values, bins=edges, weights=y_values)
        sumwy2, _ = np.histogram(x_values, bins=edges, weights=np.square(y_values))
        sumw = np.asarray(sumw, dtype=float)
        entries = sumw
        neff = entries
    else:
        sumw, edges = np.histogram(x_values, bins=bins, range=range, weights=weights)
        sumwy, _ = np.histogram(x_values, bins=edges, weights=weights * y_values)
        sumwy2, _ = np.histogram(x_values, bins=edges, weights=weights * np.square(y_values))
        sumw2, _ = np.histogram(x_values, bins=edges, weights=np.square(weights))
        sumw = np.asarray(sumw, dtype=float)
        sumw2 = np.asarray(sumw2, dtype=float)
        entries = sumw
        neff = np.divide(np.square(sumw), sumw2, out=np.zeros_like(sumw), where=sumw2 > 0.0)

    edges = np.asarray(edges, dtype=float)
    means = np.divide(sumwy, sumw, out=np.zeros_like(sumwy, dtype=float), where=sumw > 0.0)
    second_moment = np.divide(sumwy2, sumw, out=np.zeros_like(sumwy2, dtype=float), where=sumw > 0.0)
    variances = np.clip(second_moment - np.square(means), a_min=0.0, a_max=None)
    errors = np.sqrt(np.divide(variances, neff, out=np.zeros_like(variances), where=neff > 0.0))

    return profile(
        edges=edges,
        means=means,
        errors=errors,
        entries=entries,
        name=name or f"{y_branch}_vs_{x_branch}",
    )
