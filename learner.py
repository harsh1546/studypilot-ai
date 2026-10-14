"""Per-topic mastery using Bayesian Knowledge Tracing."""
from dataclasses import dataclass, field

P_INIT, P_LEARN, P_SLIP, P_GUESS = 0.30, 0.15, 0.10, 0.20


def bkt_update(p: float, correct: bool) -> float:
    """Posterior that the skill is known after one observation, then apply learning."""
    if correct:
        post = p * (1 - P_SLIP) / (p * (1 - P_SLIP) + (1 - p) * P_GUESS)
    else:
        post = p * P_SLIP / (p * P_SLIP + (1 - p) * (1 - P_GUESS))
    return post + (1 - post) * P_LEARN


@dataclass
class Learner:
    mastery: dict = field(default_factory=dict)    # topic id -> probability known
    attempts: dict = field(default_factory=dict)   # topic id -> [correct, total]
    wrong: list = field(default_factory=list)      # recent mistakes for misconception notes

    def update(self, topic: int, correct: bool, note: str = ""):
        self.mastery[topic] = bkt_update(self.mastery.get(topic, P_INIT), correct)
        c, n = self.attempts.get(topic, [0, 0])
        self.attempts[topic] = [c + correct, n + 1]
        if not correct and note:
            self.wrong.append({"topic": topic, "note": note})

    def weakest(self, topics: list[int], n: int = 3):
        return sorted(topics, key=lambda t: self.mastery.get(t, P_INIT))[:n]

    def is_new(self) -> bool:
        return not self.attempts
