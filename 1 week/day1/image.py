"""
Генерация картинки через text-to-image модель на llm.alem.ai.
Промпт задаётся ниже в переменной PROMPT.
Результат сохраняется в PNG-файл в этой же папке (day1).
"""

import base64
import json
import os
import urllib.request

URL = "https://llm.alem.ai/v1/images/generations"
KEY = "sk-XRaYv_GiYxr7YB0vHmKvsw"
MODEL = "text-to-image"

# --- ПРОМПТ: меняй текст здесь ---
PROMPT = "A kazakh woman in traditional clothing, standing in a field of tulips, yurts, with a clear blue sky in the background."
SIZE = "256x256"
OUTPUT = "output.png"
# ---------------------------------


def generate(prompt, size):
    data = json.dumps({"model": MODEL, "prompt": prompt, "size": size}).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def save_image(item, path):
    """Сохраняет картинку: поддерживает и base64 (b64_json), и ссылку (url)."""
    if item.get("b64_json"):
        with open(path, "wb") as f:
            f.write(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        urllib.request.urlretrieve(item["url"], path)
    else:
        raise ValueError(f"Не нашёл картинку в ответе: {item}")


def main():
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT)
    print(f"Промпт: {PROMPT}")
    print("Генерирую...")

    result = generate(PROMPT, SIZE)
    item = result["data"][0]
    save_image(item, out_path)

    print(f"Готово! Сохранено: {out_path}")


if __name__ == "__main__":
    main()
