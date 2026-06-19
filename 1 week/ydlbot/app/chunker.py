"""Разбиение текста на чанки с перекрытием для индексации в RAG."""
import re


def clean_text(text):
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text, chunk_size, overlap):
    """Режет текст на чанки ~chunk_size символов, упаковывая абзацы,
    с перекрытием overlap символов между соседними чанками."""
    text = clean_text(text)
    if not text:
        return []

    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    cur = ""
    for p in paras:
        if len(cur) + len(p) + 1 <= chunk_size:
            cur = f"{cur}\n{p}".strip()
        else:
            if cur:
                chunks.append(cur)
            if len(p) <= chunk_size:
                cur = p
            else:
                # очень длинный абзац — режем жёстко
                step = max(1, chunk_size - overlap)
                for i in range(0, len(p), step):
                    chunks.append(p[i:i + chunk_size])
                cur = ""
    if cur:
        chunks.append(cur)

    if overlap > 0 and len(chunks) > 1:
        merged = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            merged.append(f"{tail}\n{chunks[i]}".strip())
        chunks = merged

    return chunks
