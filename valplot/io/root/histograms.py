"""ROOT histogram adapters and TTree/RNtuple fillers."""

from __future__ import annotations

from typing import Any

import numpy as np

from ...histograms import band, efficiency, hist1d, hist2d, profile, restricted_profile, scatter


def _import_uproot():
    try:
        import uproot
    except ImportError as exc:  # pragma: no cover - exercised by users without optional dependency
        raise ImportError("uproot is required for ROOT I/O. Install it with `pip install uproot`.") from exc
    return uproot


def _th1_bin_contents(obj: Any) -> np.ndarray:
    """TH1-like bin contents, preferring ``values(flow=False)`` when available."""
    values_fn = getattr(obj, "values", None)
    if callable(values_fn):
        try:
            return np.asarray(values_fn(flow=False), dtype=float)
        except TypeError:
            return np.asarray(values_fn(), dtype=float)
    counts, _ = obj.to_numpy(flow=False)
    return np.asarray(counts, dtype=float)


def _th1_edges(obj: Any) -> np.ndarray:
    """TH1-like bin edges (no under/overflow in the edge array)."""
    axis = getattr(obj, "axis", None)
    if callable(axis):
        ax = axis()
        edges_fn = getattr(ax, "edges", None)
        if callable(edges_fn):
            return np.asarray(edges_fn(flow=False), dtype=float)
    _, edges = obj.to_numpy(flow=False)
    return np.asarray(edges, dtype=float)


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


def efficiency_from_tefficiency_uproot(obj: Any, name: str | None = None) -> efficiency:
    """Build an :class:`efficiency` from a uproot ``TEfficiency`` (member histograms)."""
    passed_histo = obj.member("fPassedHistogram")
    total_histo = obj.member("fTotalHistogram")
    passed_values = _th1_bin_contents(passed_histo)
    total_values = _th1_bin_contents(total_histo)
    edges = _th1_edges(passed_histo)
    edges_total = _th1_edges(total_histo)
    if edges.shape != edges_total.shape or not np.allclose(edges, edges_total):
        raise ValueError("TEfficiency passed/total histograms must have matching edges.")
    if passed_values.shape != total_values.shape:
        raise ValueError("TEfficiency passed/total histograms must have the same number of bins.")
    return efficiency(edges=edges, passed=passed_values, total=total_values, name=name)


def hist1d_from_tefficiency_uproot(obj: Any, name: str | None = None) -> hist1d:
    """Build a ``hist1d`` from a TEfficiency-like uproot object.

    Uses ``fPassedHistogram`` / ``fTotalHistogram`` and per-bin ``values()``
    when available. The returned ``hist1d`` stores efficiency values as
    ``counts`` and binomial uncertainties as ``errors``.
    """
    try:
        eff = efficiency_from_tefficiency_uproot(obj, name=name)
    except Exception as first_exc:
        try:
            values = np.asarray(obj.values(flow=False), dtype=float)
            errors = np.asarray(obj.errors(flow=False), dtype=float)
            axis = obj.axis() if callable(getattr(obj, "axis", None)) else obj.axes[0]
            edges = np.asarray(axis.edges(flow=False), dtype=float)
            return hist1d(edges=edges, counts=values, errors=errors, name=name)
        except Exception:
            raise ValueError("Could not convert TEfficiency object to hist1d.") from first_exc

    return hist1d(edges=eff.edges, counts=eff.values, errors=eff.errors, name=name)


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
        try:
            obj = root_file[object_path]
        except NotImplementedError as exc:
            raise NotImplementedError(
                "uproot could not deserialize this object. "
                "If this is a TEfficiency with unsupported streamer payload, "
                "read passed/total TH1 objects instead."
            ) from exc
        if getattr(obj, "classname", "") == "TEfficiency":
            return hist1d_from_tefficiency_uproot(obj, name=object_path)
        return hist1d_from_uproot(obj, name=object_path)


def read_tefficiency(file_path: str, object_path: str) -> efficiency:
    """Read a ``TEfficiency`` from a ROOT file into :class:`efficiency` (passed/total per bin)."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        try:
            obj = root_file[object_path]
        except NotImplementedError as exc:
            raise NotImplementedError(
                "uproot could not deserialize this object. "
                "If this is a TEfficiency with unsupported streamer payload, "
                "try a different uproot version or export passed/total TH1 objects."
            ) from exc
        if getattr(obj, "classname", "") != "TEfficiency":
            raise ValueError(
                f"ROOT object '{object_path}' has classname {getattr(obj, 'classname', '')!r}; "
                "expected 'TEfficiency'."
            )
        return efficiency_from_tefficiency_uproot(obj, name=object_path)


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


def scatter_from_tree(
    file_path: str,
    tree_path: str,
    x_branch: str,
    y_branch: str,
    name: str | None = None,
) -> scatter:
    """Create ``scatter`` points from two TTree/RNtuple branches."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        tree = root_file[tree_path]
        arrays = tree.arrays([x_branch, y_branch], library="np")
        x_values = np.asarray(arrays[x_branch], dtype=float)
        y_values = np.asarray(arrays[y_branch], dtype=float)

    return scatter(x=x_values, y=y_values, name=name or f"{y_branch}_vs_{x_branch}")


def band_from_tree(
    file_path: str,
    tree_path: str,
    x_branch: str,
    y_branch: str,
    bins: int | np.ndarray | list[float],
    range: tuple[float, float] | None = None,
    name: str | None = None,
) -> band:
    """Create ``band`` from TTree/RNtuple values using per-bin spread and RMS."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        tree = root_file[tree_path]
        arrays = tree.arrays([x_branch, y_branch], library="np")
        x_values = np.asarray(arrays[x_branch], dtype=float)
        y_values = np.asarray(arrays[y_branch], dtype=float)

    entries, edges = np.histogram(x_values, bins=bins, range=range)
    entries = np.asarray(entries, dtype=float)
    edges = np.asarray(edges, dtype=float)
    sumy, _ = np.histogram(x_values, bins=edges, weights=y_values)
    sumy2, _ = np.histogram(x_values, bins=edges, weights=np.square(y_values))
    means = np.divide(sumy, entries, out=np.zeros_like(sumy, dtype=float), where=entries > 0.0)
    second_moment = np.divide(sumy2, entries, out=np.zeros_like(sumy2, dtype=float), where=entries > 0.0)
    errors = np.sqrt(np.clip(second_moment - np.square(means), a_min=0.0, a_max=None))

    bin_ids = np.digitize(x_values, edges) - 1
    n_bins = entries.shape[0]
    lower = np.full(n_bins, np.nan, dtype=float)
    upper = np.full(n_bins, np.nan, dtype=float)
    for idx in np.arange(n_bins):
        mask = bin_ids == idx
        if np.any(mask):
            lower[idx] = float(np.min(y_values[mask]))
            upper[idx] = float(np.max(y_values[mask]))
        else:
            lower[idx] = means[idx]
            upper[idx] = means[idx]

    return band(
        edges=edges,
        values=means,
        lower=lower,
        upper=upper,
        errors=errors,
        name=name or f"{y_branch}_vs_{x_branch}",
    )


def restricted_band_from_tree(
    file_path: str,
    tree_path: str,
    x_branch: str,
    y_branch: str,
    restriction_branch: str,
    restriction_range: tuple[float, float],
    bins: int | np.ndarray | list[float],
    range: tuple[float, float] | None = None,
    name: str | None = None,
) -> band:
    """Create ``band`` from TTree values using per-bin min/max within a selection."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        tree = root_file[tree_path]
        requested = [x_branch, y_branch, restriction_branch]
        arrays = tree.arrays(requested, library="np")

    x_values = np.asarray(arrays[x_branch], dtype=float)
    y_values = np.asarray(arrays[y_branch], dtype=float)
    rest_values = np.asarray(arrays[restriction_branch], dtype=float)

    lo, hi = restriction_range
    mask = (rest_values >= lo) & (rest_values <= hi)
    x_values = x_values[mask]
    y_values = y_values[mask]

    entries, edges = np.histogram(x_values, bins=bins, range=range)
    entries = np.asarray(entries, dtype=float)
    edges = np.asarray(edges, dtype=float)
    sumy, _ = np.histogram(x_values, bins=edges, weights=y_values)
    sumy2, _ = np.histogram(x_values, bins=edges, weights=np.square(y_values))
    means = np.divide(sumy, entries, out=np.zeros_like(sumy, dtype=float), where=entries > 0.0)
    second_moment = np.divide(sumy2, entries, out=np.zeros_like(sumy2, dtype=float), where=entries > 0.0)
    errors = np.sqrt(np.clip(second_moment - np.square(means), a_min=0.0, a_max=None))

    bin_ids = np.digitize(x_values, edges) - 1
    n_bins = entries.shape[0]
    lower = np.full(n_bins, np.nan, dtype=float)
    upper = np.full(n_bins, np.nan, dtype=float)
    for idx in np.arange(n_bins):
        mask_bin = bin_ids == idx
        if np.any(mask_bin):
            lower[idx] = float(np.min(y_values[mask_bin]))
            upper[idx] = float(np.max(y_values[mask_bin]))
        else:
            lower[idx] = means[idx]
            upper[idx] = means[idx]

    return band(
        edges=edges,
        values=means,
        lower=lower,
        upper=upper,
        errors=errors,
        name=name or f"{y_branch}_vs_{x_branch}",
        metadata={"restriction_branch": restriction_branch, "restriction_range": restriction_range},
    )


def restricted_profile_from_tree(
    file_path: str,
    tree_path: str,
    x_branch: str,
    y_branch: str,
    restriction_branch: str,
    restriction_range: tuple[float, float],
    bins: int | np.ndarray | list[float],
    range: tuple[float, float] | None = None,
    weight_branch: str | None = None,
    name: str | None = None,
) -> restricted_profile:
    """Create ``restricted_profile`` from TTree with selection on a second variable."""
    uproot = _import_uproot()
    with uproot.open(file_path) as root_file:
        tree = root_file[tree_path]
        requested = [x_branch, y_branch, restriction_branch]
        if weight_branch is not None:
            requested.append(weight_branch)
        arrays = tree.arrays(requested, library="np")
        x_values = np.asarray(arrays[x_branch], dtype=float)
        y_values = np.asarray(arrays[y_branch], dtype=float)
        rest_values = np.asarray(arrays[restriction_branch], dtype=float)
        weights = None if weight_branch is None else np.asarray(arrays[weight_branch], dtype=float)

    lo, hi = restriction_range
    mask = (rest_values >= lo) & (rest_values <= hi)
    x_values = x_values[mask]
    y_values = y_values[mask]
    if weights is not None:
        weights = weights[mask]

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

    return restricted_profile(
        edges=edges,
        means=means,
        errors=errors,
        entries=entries,
        name=name or f"{y_branch}_vs_{x_branch}",
        metadata={"restriction_branch": restriction_branch, "restriction_range": restriction_range},
    )
