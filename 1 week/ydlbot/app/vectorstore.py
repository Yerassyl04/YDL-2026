"""Векторное хранилище на FAISS (косинусная близость через нормализацию + IndexFlatIP)."""
import pickle

import faiss
import numpy as np

import config


def _normalize(vectors):
    vectors = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def build_index(vectors, chunks):
    """Строит и сохраняет FAISS-индекс и метаданные чанков."""
    vectors = _normalize(vectors)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    faiss.write_index(index, str(config.FAISS_INDEX_PATH))
    with open(config.CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)
    return index


def load_index():
    """Загружает индекс и чанки. Возвращает (None, []) если базы ещё нет."""
    if not config.FAISS_INDEX_PATH.exists() or not config.CHUNKS_PATH.exists():
        return None, []
    index = faiss.read_index(str(config.FAISS_INDEX_PATH))
    with open(config.CHUNKS_PATH, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks


def search(index, chunks, query_vec, top_k):
    """Возвращает top_k наиболее похожих чанков со score (косинус)."""
    q = _normalize(np.asarray([query_vec], dtype="float32"))
    scores, idx = index.search(q, min(top_k, len(chunks)))
    results = []
    for score, i in zip(scores[0], idx[0]):
        if i < 0:
            continue
        results.append({**chunks[i], "score": float(score)})
    return results
