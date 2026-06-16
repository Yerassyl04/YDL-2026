"""
Интерактивная генерация картинки через text-to-image на llm.alem.ai.
Скрипт спрашивает описание (промпт) и имя файла,
затем сохраняет картинку с этим именем в папку day1.
"""

import base64
import json
import os
import re
import urllib.request

URL = "https://llm.alem.ai/v1/images/generations"
KEY = "sk-XRaYv_GiYxr7YB0vHmKvsw"
MODEL = "text-to-image"
SIZE = "256x256"


def slugify(text):
    """Делает из описания безопасное имя файла, напр. 'red car' -> 'red_car'."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)   # убрать пунктуацию (поддерживает Unicode/кириллицу)
    text = re.sub(r"[\s-]+", "_", text)    # пробелы -> _
    text = text.strip("_")
    if len(text) > 50:                     # не делать слишком длинное имя
        text = text[:50].rstrip("_")
    return text or "image"


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
    folder = os.path.dirname(os.path.abspath(__file__))

    prompt = input("Опиши, что нарисовать: ").strip()
    if not prompt:
        print("Пустое описание — выхожу.")
        return

    # Имя файла формируется из самого описания.
    base = slugify(prompt)
    name = f"{base}.png"
    i = 1
    while os.path.exists(os.path.join(folder, name)):
        name = f"{base}{i}.png"
        i += 1

    out_path = os.path.join(folder, name)

    print("Генерирую...")
    result = generate(prompt, SIZE)
    item = result["data"][0]
    save_image(item, out_path)

    print(f"Готово! Сохранено: {out_path}")


if __name__ == "__main__":
    main()
