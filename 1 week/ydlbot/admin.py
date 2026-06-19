"""Streamlit админ-панель.
Запуск:  streamlit run admin.py
"""
import json

import pandas as pd
import streamlit as st

import config
from app import db, rag
from app.ingest import run_ingest

st.set_page_config(page_title="Yessenov AI — Админ-панель", page_icon="🤖", layout="wide")
db.init_db()


def load_kb_meta():
    if config.KB_META_PATH.exists():
        with open(config.KB_META_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


st.sidebar.title("🤖 Yessenov AI")
st.sidebar.caption("Админ-панель консультанта фонда")
page = st.sidebar.radio("Разделы", ["📊 Дашборд", "💬 Диалоги", "🔎 Поиск", "📚 База знаний"])

# ------------------------------------------------------------------ Дашборд
if page == "📊 Дашборд":
    st.header("📊 Дашборд")
    s = db.stats()
    meta = load_kb_meta()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Всего вопросов", s["total"])
    c2.metric("Уникальных пользователей", s["users"])
    c3.metric("Вопросов сегодня", s["today"])
    nf = round(100 * s["not_found"] / s["total"], 1) if s["total"] else 0
    c4.metric("Не найдено в базе, %", nf)

    c5, c6, c7 = st.columns(3)
    c5.metric("Документов в базе", meta.get("docs", "—"))
    c6.metric("Чанков в базе", meta.get("chunks", "—"))
    c7.metric("Обновлено", meta.get("updated_at", "—"))

    st.subheader("Динамика вопросов по дням")
    rows = db.fetch_messages(limit=5000)
    if rows:
        df = pd.DataFrame(rows)
        df["date"] = df["ts"].str.slice(0, 10)
        by_day = df.groupby("date").size().rename("Вопросы")
        st.bar_chart(by_day)
    else:
        st.info("Пока нет данных о диалогах.")

# ------------------------------------------------------------------ Диалоги
elif page == "💬 Диалоги":
    st.header("💬 История диалогов")
    rows = db.fetch_messages(limit=1000)
    if not rows:
        st.info("Пока нет диалогов.")
    else:
        df = pd.DataFrame(rows)[
            ["ts", "user_id", "username", "first_name", "question", "answer", "found"]
        ]
        df["found"] = df["found"].map({1: "✅", 0: "❌"})
        df = df.rename(columns={
            "ts": "Время", "user_id": "ID", "username": "Username",
            "first_name": "Имя", "question": "Вопрос", "answer": "Ответ",
            "found": "Найдено",
        })
        st.dataframe(df, use_container_width=True, height=600)

# ------------------------------------------------------------------ Поиск
elif page == "🔎 Поиск":
    st.header("🔎 Поиск по истории вопросов")
    query = st.text_input("Введите слово или фразу для поиска")
    if query:
        rows = db.fetch_messages(limit=1000, search=query)
        st.caption(f"Найдено записей: {len(rows)}")
        for r in rows:
            mark = "✅" if r["found"] else "❌"
            with st.expander(f"{mark} [{r['ts']}] {r['question'][:80]}"):
                st.markdown(f"**Пользователь:** {r['first_name']} (@{r['username']}, id={r['user_id']})")
                st.markdown(f"**Вопрос:** {r['question']}")
                st.markdown(f"**Ответ:** {r['answer']}")
                if r["sources"]:
                    st.markdown("**Источники:**")
                    for src in json.loads(r["sources"]):
                        st.markdown(f"- [{src['title']}]({src['url']}) — score {src.get('score')}")

# ------------------------------------------------------------------ База знаний
elif page == "📚 База знаний":
    st.header("📚 База знаний")
    meta = load_kb_meta()

    c1, c2, c3 = st.columns(3)
    c1.metric("Документов", meta.get("docs", "—"))
    c2.metric("Чанков", meta.get("chunks", "—"))
    c3.metric("Последнее обновление", meta.get("updated_at", "—"))
    st.caption(f"Источник: {meta.get('base_url', config.SCRAPE_BASE_URL)}")

    st.divider()
    st.subheader("Обновление базы знаний")
    st.write("Повторно скачивает сайт фонда, пересоздаёт чанки и FAISS-индекс. "
             "Может занять несколько минут.")

    if st.button("🔄 Обновить базу знаний", type="primary"):
        log_box = st.empty()
        logs = []

        def progress(msg):
            logs.append(msg)
            log_box.code("\n".join(logs[-25:]))

        with st.spinner("Идёт обновление базы знаний…"):
            result = run_ingest(progress=progress)
            rag.reload_index()
        st.success(f"Готово ✅  Документов: {result['docs']}, чанков: {result['chunks']}")
