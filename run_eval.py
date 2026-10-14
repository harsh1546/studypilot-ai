"""Evaluate retrieval and personalization.

Usage (from backend/):  python -m eval.run_eval path/to/course.pdf
Reports context recall@k, off-material refusal rate, and simulated-student
mastery gain and question repetition rate. For faithfulness and answer
relevancy, feed the same test set to RAGAS or DeepEval (see docs/ARCHITECTURE.md).
"""
import json
import random
import sys
from pathlib import Path

from app.ingest import ingest
from app.learner import Learner
from app.quiz import build, grade
from app.retrieval import KnowledgeBase


def retrieval_metrics(kb, tests):
    hit = precision = 0
    for t in tests["in_scope"]:
        hits, _ = kb.search(t["question"])
        ok = [u.source == t["expected_source"] and u.loc == t["expected_loc"] for u, _ in hits]
        hit += any(ok)
        precision += sum(ok) / max(len(ok), 1)
    n = max(len(tests["in_scope"]), 1)
    refused = sum(not kb.search(q)[1] for q in tests["off_material"])
    return {"context_recall": hit / n, "context_precision": precision / n,
            "off_material_refusal": refused / max(len(tests["off_material"]), 1)}


def simulate(kb, skill: float, sessions: int = 5, per_session: int = 8):
    """A simulated student answers correctly with probability `skill`, rising each session."""
    learner, asked, repeats, total = Learner(), set(), 0, 0
    for s in range(sessions):
        for _ in range(per_session):
            q = build(list(kb.units), kb.units, asked, "mcq")
            if q is None:
                continue
            total += 1
            repeats += q["id"] in asked
            asked.add(q["id"])
            learner.update(q["topic"], random.random() < min(skill + 0.08 * s, 0.95))
    gain = sum(learner.mastery.values()) / max(len(learner.mastery), 1) - 0.30
    return {"skill": skill, "mastery_gain": round(gain, 2), "repetition_rate": repeats / max(total, 1)}


if __name__ == "__main__":
    kb = KnowledgeBase()
    kb.add(ingest(Path(sys.argv[1])))
    tests = json.loads((Path(__file__).parent / "testset.json").read_text())
    print("Retrieval:", json.dumps(retrieval_metrics(kb, tests), indent=2))
    for skill in (0.3, 0.5, 0.7):
        print("Student:", simulate(kb, skill))
