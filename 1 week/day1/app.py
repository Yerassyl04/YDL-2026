"""
Streamlit-интерфейс для генерации картинок через text-to-image на llm.alem.ai.

Запуск:
    streamlit run app.py
"""

import base64
import io
import json
import urllib.request

import streamlit as st

URL = "https://llm.alem.ai/v1/images/generations"
KEY = "sk-XRaYv_GiYxr7YB0vHmKvsw"
MODEL = "text-to-image"
SIZE = "256x256"


def generate(prompt, size=SIZE):
    """Отправляет промпт модели и возвращает байты картинки (PNG)."""
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
        result = json.load(resp)

    item = result["data"][0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        with urllib.request.urlopen(item["url"]) as r:
            return r.read()
    raise ValueError(f"Не нашёл картинку в ответе: {item}")


st.title("🎨 Генератор картинок")

prompt = st.text_input("Опиши, что нарисовать:", key="prompt")

col1, col2 = st.columns(2)
with col1:
    generate_clicked = st.button("Сгенерировать", type="primary")
with col2:
    refresh_clicked = st.button("🔄 Ещё раз")

# Любая из кнопок запускает генерацию по текущему описанию.
if generate_clicked or refresh_clicked:
    if not prompt.strip():
        st.warning("Сначала введи описание.")
    else:
        with st.spinner("Генерирую..."):
            try:
                image_bytes = generate(prompt.strip())
                st.session_state["image"] = image_bytes
                st.session_state["last_prompt"] = prompt.strip()
            except Exception as e:
                st.error(f"Ошибка: {e}")

# Показываем последнюю сгенерированную картинку.
if st.session_state.get("image"):
    st.image(st.session_state["image"], caption=st.session_state.get("last_prompt", ""))
    st.download_button(
        "💾 Скачать PNG",
        data=st.session_state["image"],
        file_name="image.png",
        mime="image/png",
    )
