from __future__ import annotations

import unittest

from app.nlp_service import analyze_batch, get_demo_batch


class NLPServiceTests(unittest.TestCase):
    def test_demo_batch_and_training_corpus_are_available(self) -> None:
        demo = get_demo_batch()
        self.assertGreaterEqual(len(demo["messages"]), 1)
        self.assertGreaterEqual(demo["training_corpus_rows"], 20)
        self.assertIn("synthetic", demo["notice"].lower())

    def test_batch_returns_predictions_and_holdout_validation(self) -> None:
        result = analyze_batch(
            [
                "Great teamwork, thanks for the match.",
                "You are useless and should leave the game.",
            ],
            threshold=0.5,
        )
        self.assertEqual(result["total_messages"], 2)
        self.assertEqual(len(result["predictions"]), 2)
        self.assertIn("holdout_rows", result["validation"])
        self.assertIn("confusion_matrix", result["validation"])
        self.assertEqual(result["training_corpus"]["source"], "Curated synthetic NexusMatch demonstration corpus")
        self.assertTrue(any("synthetic" in item.lower() for item in result["limitations"]))

    def test_batch_rejects_empty_and_oversized_inputs(self) -> None:
        with self.assertRaises(ValueError):
            analyze_batch(["", "   "])
        with self.assertRaises(ValueError):
            analyze_batch(["x"] * 501)
        with self.assertRaises(ValueError):
            analyze_batch(["valid"], threshold=0.95)


if __name__ == "__main__":
    unittest.main()
