import unittest

import numpy as np

from meshrush.omni.compression import (
    assignment_entropy,
    compress_region,
    compression_gain,
    mutual_information_bits,
    vq_codebook,
)


def _two_blobs(n=30, sep=10.0, seed=1):
    rng = np.random.default_rng(seed)
    a = rng.normal(0.0, 0.3, size=(n, 2))
    b = rng.normal(0.0, 0.3, size=(n, 2)) + np.array([sep, 0.0])
    x = np.vstack([a, b])
    y = np.array([0] * n + [1] * n)  # relevance label = which blob
    return x, y


class VQCodebookTests(unittest.TestCase):
    def test_recovers_two_separated_clusters(self):
        x, y = _two_blobs()
        book = vq_codebook(x, 2, seed=0)
        # each true blob should map to a single (consistent) codeword
        self.assertEqual(len(np.unique(book.labels[y == 0])), 1)
        self.assertEqual(len(np.unique(book.labels[y == 1])), 1)
        self.assertNotEqual(book.labels[0], book.labels[-1])

    def test_deterministic_for_fixed_seed(self):
        x, _ = _two_blobs()
        b1 = vq_codebook(x, 3, seed=7)
        b2 = vq_codebook(x, 3, seed=7)
        self.assertTrue(np.array_equal(b1.labels, b2.labels))
        self.assertTrue(np.allclose(b1.centroids, b2.centroids))

    def test_more_codewords_reduce_distortion(self):
        x, _ = _two_blobs()
        self.assertGreater(vq_codebook(x, 1).inertia, vq_codebook(x, 2).inertia)

    def test_all_k_codewords_populated(self):
        x, _ = _two_blobs()
        book = vq_codebook(x, 5, seed=3)
        self.assertEqual(len(np.unique(book.labels)), 5)

    def test_validation(self):
        x, _ = _two_blobs(n=3)
        with self.assertRaises(ValueError):
            vq_codebook(x, 0)
        with self.assertRaises(ValueError):
            vq_codebook(x, 999)  # k > n
        with self.assertRaises(ValueError):
            vq_codebook(np.zeros((0, 2)), 1)
        with self.assertRaises(ValueError):
            vq_codebook(np.zeros(5), 1)  # not 2-D


class InformationTests(unittest.TestCase):
    def test_assignment_entropy_uniform_two_clusters_is_one_bit(self):
        labels = np.array([0, 0, 1, 1])
        self.assertAlmostEqual(assignment_entropy(labels), 1.0, places=9)

    def test_assignment_entropy_single_cluster_is_zero(self):
        self.assertAlmostEqual(assignment_entropy(np.zeros(10, dtype=int)), 0.0, places=9)

    def test_mi_perfect_alignment_equals_h_y(self):
        t = np.array([0, 0, 1, 1])
        y = np.array([5, 5, 9, 9])  # T determines Y exactly
        self.assertAlmostEqual(mutual_information_bits(t, y), 1.0, places=9)  # H(Y)=1 bit

    def test_mi_independent_is_zero(self):
        t = np.array([0, 1, 0, 1])
        y = np.array([0, 0, 1, 1])  # orthogonal patterns -> I=0
        self.assertAlmostEqual(mutual_information_bits(t, y), 0.0, places=9)

    def test_mi_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            mutual_information_bits(np.array([0, 1]), np.array([0]))


class CompressionGainTests(unittest.TestCase):
    def test_gain_high_when_codebook_tracks_relevance(self):
        x, y = _two_blobs()
        aligned = compress_region(x, y, 2, seed=0)
        # random relevance uncorrelated with geometry -> ~0 gain
        rng = np.random.default_rng(0)
        y_rand = rng.integers(0, 2, size=y.shape[0])
        noisy = compress_region(x, y_rand, 2, seed=0)
        self.assertGreater(aligned.relevance_bits, 0.9)  # ~1 bit, tracks the blobs
        self.assertGreater(aligned.relevance_bits, noisy.relevance_bits)

    def test_single_codeword_has_zero_gain(self):
        x, y = _two_blobs()
        res = compress_region(x, y, 1, seed=0)
        self.assertAlmostEqual(res.relevance_bits, 0.0, places=9)
        self.assertAlmostEqual(res.rate_bits, 0.0, places=9)

    def test_compression_gain_matches_mutual_information(self):
        x, y = _two_blobs()
        book = vq_codebook(x, 2, seed=0)
        self.assertEqual(compression_gain(book.labels, y),
                         mutual_information_bits(book.labels, y))

    def test_compress_region_length_mismatch_raises(self):
        x, _ = _two_blobs()
        with self.assertRaises(ValueError):
            compress_region(x, np.array([0, 1, 2]), 2)


if __name__ == "__main__":
    unittest.main()
