"""MR-05 — compression: VQ codebook + information-bottleneck relevance.

Omni maintains a *reduction surface*: the compressed local picture of the graph it
explores (spec 10 §"reduction surface"). This module compresses the diffusion
embedding into a **vector-quantization codebook** (Lloyd / k-means++ over the
diffusion coordinates) and scores it by the **information bottleneck** principle:
a good codebook ``T = q(X)`` is a lossy summary of the geometry ``X`` that still
carries information about a *relevance* variable ``Y`` (a seed label, region tag,
or target field).

The **compression gain** ``ΔH = I(T; Y)`` (bits) — the relevance information the
codebook captures — is the quantity the MR-06 compile certificate's
``compression_gain`` gate consumes (``ΔH > h*``): a region earns compiled status
only if a compact codebook of it still explains the relevance target. A codebook
that carves the geometry but says nothing about ``Y`` has ΔH ≈ 0 and fails the
gate; a single codeword (``k = 1``) is a constant summary with ΔH = 0 by
construction.

Requires the ``scientific`` extra (``numpy``).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_LOG2 = np.log(2.0)


@dataclass(frozen=True)
class VQCodebook:
    """A vector-quantization codebook over an embedding.

    ``centroids`` is ``(k, d)``; ``labels`` assigns each of the ``n`` input points
    to a codeword in ``[0, k)``; ``inertia`` is the within-cluster sum of squared
    distances (the quantization distortion).
    """

    centroids: np.ndarray
    labels: np.ndarray
    inertia: float

    @property
    def k(self) -> int:
        return int(self.centroids.shape[0])


def _as_2d(x) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"expected a 2-D (n, d) array, got shape {arr.shape}")
    if arr.shape[0] == 0:
        raise ValueError("empty input: no points to quantize")
    return arr


def _kmeanspp_init(x: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Deterministic (seeded) k-means++ seeding."""
    n = x.shape[0]
    first = int(rng.integers(n))
    centroids = [x[first]]
    closest_sq = np.sum((x - centroids[0]) ** 2, axis=1)
    for _ in range(1, k):
        cdf = np.cumsum(closest_sq)
        total = float(cdf[-1])
        if total == 0.0:  # all remaining points coincide with a chosen centroid
            centroids.append(x[int(rng.integers(n))])
            continue
        # inverse-CDF sample (D^2 weighting) — robust to float sum-to-1 drift
        nxt = int(np.searchsorted(cdf, rng.random() * total))
        nxt = min(nxt, n - 1)
        centroids.append(x[nxt])
        d_sq = np.sum((x - centroids[-1]) ** 2, axis=1)
        closest_sq = np.minimum(closest_sq, d_sq)
    return np.asarray(centroids, dtype=float)


def vq_codebook(x, k: int, *, n_iter: int = 50, seed: int = 0) -> VQCodebook:
    """Quantize points ``x`` (``(n, d)``) into ``k`` codewords via Lloyd's algorithm.

    Deterministic for a fixed ``seed``. Empty clusters are re-seeded to the point
    farthest from its assigned centroid so ``k`` codewords are always populated.
    """
    arr = _as_2d(x)
    n = arr.shape[0]
    if k < 1:
        raise ValueError("k must be >= 1")
    if k > n:
        raise ValueError(f"k={k} exceeds number of points n={n}")

    rng = np.random.default_rng(seed)
    centroids = _kmeanspp_init(arr, k, rng)
    labels = np.zeros(n, dtype=int)
    for _ in range(n_iter):
        # assign: nearest centroid by squared Euclidean distance
        d_sq = np.sum((arr[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
        new_labels = np.argmin(d_sq, axis=1)
        if np.array_equal(new_labels, labels) and _ > 0:
            labels = new_labels
            break
        labels = new_labels
        # update: mean of each cluster; re-seed empties to the worst-fit point
        for j in range(k):
            members = arr[labels == j]
            if members.shape[0] == 0:
                worst = int(np.argmax(np.min(d_sq, axis=1)))
                centroids[j] = arr[worst]
            else:
                centroids[j] = members.mean(axis=0)

    d_sq = np.sum((arr[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
    labels = np.argmin(d_sq, axis=1)
    inertia = float(d_sq[np.arange(n), labels].sum())
    return VQCodebook(centroids=centroids, labels=labels, inertia=inertia)


def _entropy_bits(counts: np.ndarray) -> float:
    total = float(counts.sum())
    if total == 0.0:
        return 0.0
    p = counts[counts > 0] / total
    return float(-(p * np.log(p)).sum() / _LOG2)


def assignment_entropy(labels) -> float:
    """Codebook rate ``H(T)`` in bits — the entropy of the codeword usage."""
    lab = np.asarray(labels)
    _, counts = np.unique(lab, return_counts=True)
    return _entropy_bits(counts)


def mutual_information_bits(labels, y) -> float:
    """``I(T; Y)`` in bits between codeword assignment ``T`` and relevance label ``Y``."""
    t = np.asarray(labels)
    yy = np.asarray(y)
    if t.shape[0] != yy.shape[0]:
        raise ValueError("labels and y must have the same length")
    if t.shape[0] == 0:
        raise ValueError("empty inputs")
    t_vals, t_idx = np.unique(t, return_inverse=True)
    y_vals, y_idx = np.unique(yy, return_inverse=True)
    joint = np.zeros((t_vals.size, y_vals.size), dtype=float)
    np.add.at(joint, (t_idx, y_idx), 1.0)
    n = joint.sum()
    p_ty = joint / n
    p_t = p_ty.sum(axis=1, keepdims=True)
    p_y = p_ty.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = p_ty / (p_t * p_y)
        terms = p_ty * np.log(ratio)
    return float(np.nansum(terms[p_ty > 0]) / _LOG2)


def compression_gain(labels, y) -> float:
    """MR-06 ``ΔH`` — the relevance information a codebook captures, ``I(T; Y)`` bits.

    This is the value fed to ``CompileMetrics.delta_h``; the compile certificate's
    ``compression_gain`` gate accepts only when ``ΔH > h*``.
    """
    return mutual_information_bits(labels, y)


@dataclass(frozen=True)
class CompressionResult:
    codebook: VQCodebook
    rate_bits: float          # H(T)
    relevance_bits: float     # I(T; Y) == compression gain ΔH
    inertia: float


def compress_region(x, y, k: int, *, n_iter: int = 50, seed: int = 0) -> CompressionResult:
    """Quantize an embedding and score it by IB relevance in one call.

    ``x`` are the region's diffusion coordinates ``(n, d)``; ``y`` is the per-point
    relevance label (length ``n``).
    """
    yy = np.asarray(y)
    arr = _as_2d(x)
    if yy.shape[0] != arr.shape[0]:
        raise ValueError("y must have one label per point in x")
    book = vq_codebook(arr, k, n_iter=n_iter, seed=seed)
    return CompressionResult(
        codebook=book,
        rate_bits=assignment_entropy(book.labels),
        relevance_bits=compression_gain(book.labels, yy),
        inertia=book.inertia,
    )
