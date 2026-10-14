"""TF-IDF retrieval plus topic discovery (clusters labelled by key terms)."""
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import MAX_TOPICS, MIN_SCORE, TOP_K
from .ingest import Unit


class KnowledgeBase:
    def __init__(self):
        self.units: list[Unit] = []
        self.topics: list[dict] = []
        self._vec = None
        self._matrix = None

    def add(self, units: list[Unit]):
        self.units += units
        self._build()

    def _build(self):
        texts = [u.text for u in self.units]
        self._vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self._matrix = self._vec.fit_transform(texts)
        self._find_topics()

    def _find_topics(self):
        k = max(1, min(MAX_TOPICS, len(self.units) // 3))
        labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(self._matrix)
        terms = np.array(self._vec.get_feature_names_out())
        self.topics = []
        for t in range(k):
            members = [i for i, l in enumerate(labels) if l == t]
            centroid = np.asarray(self._matrix[members].mean(axis=0)).ravel()
            name = ", ".join(terms[centroid.argsort()[::-1][:3]])
            first = min(members)  # earlier material is treated as a prerequisite
            self.topics.append({"id": t, "name": name, "size": len(members), "order": first})
            for i in members:
                self.units[i].topic = t
        self.topics.sort(key=lambda t: t["order"])
        for rank, t in enumerate(self.topics):
            t["prerequisites"] = [self.topics[rank - 1]["id"]] if rank else []

    def search(self, query: str, topic: int | None = None):
        """Return (hits, covered). `covered` is False when nothing is close enough."""
        if not self.units:
            return [], False
        scores = cosine_similarity(self._vec.transform([query]), self._matrix).ravel()
        order = [i for i in scores.argsort()[::-1] if topic is None or self.units[i].topic == topic]
        hits = [(self.units[i], float(scores[i])) for i in order[:TOP_K]]
        return hits, bool(hits) and hits[0][1] >= MIN_SCORE
