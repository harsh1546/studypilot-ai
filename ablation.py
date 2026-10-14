"""Ablation: random quizzing vs adaptive quizzing vs adaptive + root-cause tutoring.

Simulated students have hidden knowledge per topic. Answering well on a topic depends on
knowing its prerequisite, so a gap early in the chain hurts everything after it.
Usage (from backend/):  python -m eval.ablation
"""
import random
import statistics

from app.diagnosis import root_cause
from app.learner import Learner

TOPICS = [{"id": i, "prerequisites": [i - 1] if i else []} for i in range(8)]
CONDITIONS = ("random", "adaptive", "adaptive + root-cause")


def p_correct(know: dict, t: int) -> float:
    prereq = know[t - 1] if t else 1.0
    return 0.2 + 0.7 * know[t] * min(1.0, prereq + 0.3)


def run_student(condition: str, steps: int = 60, seed: int = 0) -> float:
    rng = random.Random(seed)
    know = {t["id"]: rng.uniform(0.0, 0.4) for t in TOPICS}
    start = statistics.mean(know.values())
    learner = Learner()
    for _ in range(steps):
        ids = [t["id"] for t in TOPICS]
        t = rng.choice(ids) if condition == "random" else learner.weakest(ids, 1)[0]
        ok = rng.random() < p_correct(know, t)
        learner.update(t, ok)
        prereq = know[t - 1] if t else 1.0                       # learning is slower without the prerequisite
        know[t] += 0.10 * (1 - know[t]) * min(1.0, prereq + 0.1)
        if not ok and condition == "adaptive + root-cause":
            gap = root_cause(t, TOPICS, learner.mastery)
            if gap is not None:                                  # teach the prerequisite first
                know[gap] += 0.25 * (1 - know[gap])
                learner.update(gap, True)
    return statistics.mean(know.values()) - start


if __name__ == "__main__":
    for c in CONDITIONS:
        gains = [run_student(c, seed=s) for s in range(50)]
        print(f"{c:<24} mean mastery gain {statistics.mean(gains):.3f} (sd {statistics.stdev(gains):.3f})")
