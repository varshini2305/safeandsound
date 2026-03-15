from __future__ import annotations

import math
from dataclasses import replace

from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from .extract import SwayEvent


def assign_topic_clusters(events: list[SwayEvent]) -> list[SwayEvent]:
    if not events:
        return events

    texts = [e.user_question for e in events]
    if len(texts) < 5:
        return [replace(e, topic_cluster_id=0) for e in events]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    X = vectorizer.fit_transform(texts)

    k = min(8, max(2, int(math.sqrt(len(texts)))))
    km = MiniBatchKMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = km.fit_predict(X)

    out = []
    for e, lab in zip(events, labels):
        out.append(replace(e, topic_cluster_id=int(lab)))
    return out

