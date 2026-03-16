"""Core histogram helper containers used by plotting backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np


ArrayLike = np.ndarray | list[float] | tuple[float, ...]


def _as_1d_float_array(values: ArrayLike, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1-dimensional, got shape={arr.shape!r}")
    return arr


def _as_float_array(values: Any, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 0:
        raise ValueError(f"{name} must be at least 1-dimensional")
    return arr


@dataclass(frozen=True)
class hist1d:
    """Container for one-dimensional binned histogram content."""

    edges: ArrayLike
    counts: ArrayLike
    errors: ArrayLike | None = None
    underflow: float = 0.0
    overflow: float = 0.0
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        edges = _as_1d_float_array(self.edges, "edges")
        counts = _as_1d_float_array(self.counts, "counts")
        if edges.shape[0] != counts.shape[0] + 1:
            raise ValueError("edges length must be counts length + 1")
        if np.any(np.diff(edges) <= 0):
            raise ValueError("edges must be strictly increasing")

        if self.errors is None:
            errors = np.sqrt(np.clip(counts, a_min=0.0, a_max=None))
        else:
            errors = _as_1d_float_array(self.errors, "errors")
            if errors.shape != counts.shape:
                raise ValueError("errors shape must match counts shape")
            if np.any(errors < 0):
                raise ValueError("errors must be non-negative")

        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "counts", counts)
        object.__setattr__(self, "errors", errors)

    @property
    def n_bins(self) -> int:
        return int(self.counts.shape[0])

    @property
    def variances(self) -> np.ndarray:
        return np.square(self.errors)

    def integral(self, include_flow: bool = False) -> float:
        total = float(np.sum(self.counts))
        if include_flow:
            total += float(self.underflow) + float(self.overflow)
        return total

    def compatible_with(self, other: "hist1d", atol: float = 0.0, rtol: float = 0.0) -> bool:
        return np.allclose(self.edges, other.edges, atol=atol, rtol=rtol)


@dataclass(frozen=True)
class hist2d:
    """Container for two-dimensional binned histogram content."""

    x_edges: ArrayLike
    y_edges: ArrayLike
    counts: Any
    errors: Any | None = None
    underflow: float = 0.0
    overflow: float = 0.0
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        x_edges = _as_1d_float_array(self.x_edges, "x_edges")
        y_edges = _as_1d_float_array(self.y_edges, "y_edges")
        counts = _as_float_array(self.counts, "counts")
        if counts.ndim != 2:
            raise ValueError("counts must be a 2-dimensional array")
        expected_shape = (x_edges.shape[0] - 1, y_edges.shape[0] - 1)
        if counts.shape != expected_shape:
            raise ValueError(f"counts shape must be {expected_shape!r}, got {counts.shape!r}")
        if np.any(np.diff(x_edges) <= 0) or np.any(np.diff(y_edges) <= 0):
            raise ValueError("edge arrays must be strictly increasing")

        if self.errors is None:
            errors = np.sqrt(np.clip(counts, a_min=0.0, a_max=None))
        else:
            errors = _as_float_array(self.errors, "errors")
            if errors.shape != counts.shape:
                raise ValueError("errors shape must match counts shape")
            if np.any(errors < 0):
                raise ValueError("errors must be non-negative")

        object.__setattr__(self, "x_edges", x_edges)
        object.__setattr__(self, "y_edges", y_edges)
        object.__setattr__(self, "counts", counts)
        object.__setattr__(self, "errors", errors)

    @property
    def shape(self) -> tuple[int, int]:
        return (int(self.counts.shape[0]), int(self.counts.shape[1]))

    @property
    def variances(self) -> np.ndarray:
        return np.square(self.errors)

    def integral(self, include_flow: bool = False) -> float:
        total = float(np.sum(self.counts))
        if include_flow:
            total += float(self.underflow) + float(self.overflow)
        return total

    def compatible_with(self, other: "hist2d", atol: float = 0.0, rtol: float = 0.0) -> bool:
        return np.allclose(self.x_edges, other.x_edges, atol=atol, rtol=rtol) and np.allclose(
            self.y_edges, other.y_edges, atol=atol, rtol=rtol
        )


@dataclass(frozen=True)
class profile:
    """Container for profile histogram means and associated per-bin uncertainties."""

    edges: ArrayLike
    means: ArrayLike
    errors: ArrayLike
    entries: ArrayLike
    underflow_entries: float = 0.0
    overflow_entries: float = 0.0
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        edges = _as_1d_float_array(self.edges, "edges")
        means = _as_1d_float_array(self.means, "means")
        errors = _as_1d_float_array(self.errors, "errors")
        entries = _as_1d_float_array(self.entries, "entries")
        if edges.shape[0] != means.shape[0] + 1:
            raise ValueError("edges length must be means length + 1")
        if means.shape != errors.shape or means.shape != entries.shape:
            raise ValueError("means, errors, and entries must have identical shapes")
        if np.any(entries < 0):
            raise ValueError("entries must be non-negative")
        if np.any(errors < 0):
            raise ValueError("errors must be non-negative")

        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "means", means)
        object.__setattr__(self, "errors", errors)
        object.__setattr__(self, "entries", entries)

    @property
    def n_bins(self) -> int:
        return int(self.means.shape[0])


@dataclass(frozen=True)
class efficiency:
    """Container for binomial efficiency information."""

    edges: ArrayLike
    passed: ArrayLike
    total: ArrayLike
    errors: ArrayLike | None = None
    underflow_passed: float = 0.0
    underflow_total: float = 0.0
    overflow_passed: float = 0.0
    overflow_total: float = 0.0
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        edges = _as_1d_float_array(self.edges, "edges")
        passed = _as_1d_float_array(self.passed, "passed")
        total = _as_1d_float_array(self.total, "total")
        if edges.shape[0] != passed.shape[0] + 1:
            raise ValueError("edges length must be passed/total length + 1")
        if passed.shape != total.shape:
            raise ValueError("passed and total must have the same shape")
        if np.any(passed < 0) or np.any(total < 0):
            raise ValueError("passed and total must be non-negative")
        if np.any(passed > total):
            raise ValueError("passed cannot exceed total")

        if self.errors is None:
            with np.errstate(divide="ignore", invalid="ignore"):
                p = np.divide(passed, total, out=np.zeros_like(passed), where=total > 0)
                errors = np.sqrt(np.divide(p * (1.0 - p), total, out=np.zeros_like(total), where=total > 0))
        else:
            errors = _as_1d_float_array(self.errors, "errors")
            if errors.shape != passed.shape:
                raise ValueError("errors shape must match passed/total shape")
            if np.any(errors < 0):
                raise ValueError("errors must be non-negative")

        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "passed", passed)
        object.__setattr__(self, "total", total)
        object.__setattr__(self, "errors", errors)

    @property
    def values(self) -> np.ndarray:
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.divide(self.passed, self.total, out=np.zeros_like(self.passed), where=self.total > 0)

    @property
    def n_bins(self) -> int:
        return int(self.passed.shape[0])
