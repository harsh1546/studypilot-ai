"""Root-cause diagnosis: when a student misses a question, find the earliest weak prerequisite."""
WEAK = 0.5


def prerequisite_chain(topic_id: int, topics: list[dict]) -> list[int]:
    """Prerequisites of a topic, nearest first."""
    by_id = {t["id"]: t for t in topics}
    chain, cur = [], topic_id
    while by_id[cur]["prerequisites"]:
        cur = by_id[cur]["prerequisites"][0]
        chain.append(cur)
    return chain


def root_cause(topic_id: int, topics: list[dict], mastery: dict, default: float = 0.3):
    """Deepest prerequisite whose mastery is below the weak threshold, or None."""
    gaps = [t for t in prerequisite_chain(topic_id, topics) if mastery.get(t, default) < WEAK]
    return gaps[-1] if gaps else None
