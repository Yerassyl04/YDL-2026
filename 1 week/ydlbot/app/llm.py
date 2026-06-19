"""Клиент для чата (Gemma 4) и эмбеддингов через alem.ai.

Использует только OpenAI-совместимый API alem.ai (ключи из creds.txt):
  - чат:        https://llm.alem.ai/v1/chat/completions   (model: gemma4)
  - эмбеддинги: https://llm.alem.ai/v1/embeddings          (model: text-1024)
"""
import time

import numpy as np
import requests

import config


def chat(messages, temperature=0.2, max_tokens=800):
    """Запрос к чат-модели. messages — список {role, content}."""
    url = f"{config.LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = _post_with_retry(url, headers, payload)
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def embed(texts):
    """Возвращает np.ndarray (n, dim) с эмбеддингами. texts — str или список."""
    if isinstance(texts, str):
        texts = [texts]
    url = f"{config.EMBED_BASE_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {config.EMBED_API_KEY}",
        "Content-Type": "application/json",
    }
    vectors = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = {"model": config.EMBED_MODEL, "input": batch}
        resp = _post_with_retry(url, headers, payload)
        data = resp.json()
        # сохраняем исходный порядок
        items = sorted(data["data"], key=lambda x: x.get("index", 0))
        for item in items:
            vectors.append(item["embedding"])
    return np.array(vectors, dtype="float32")


def _post_with_retry(url, headers, payload, retries=3, timeout=120):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                return r
            last_err = RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        except requests.RequestException as e:
            last_err = e
        time.sleep(1.5 * (attempt + 1))
    raise last_err
