"""
Простой чат с моделью gemma4 через llm.alem.ai.
Запусти файл, пиши вопрос в терминале и получай ответ.
Для выхода введи: exit / quit / выход
"""

import json
import urllib.request

URL = "https://llm.alem.ai/v1/chat/completions"
KEY = "sk-xrBIcjmrsjOBZP0ldbtzgg"
MODEL = "gemma4"


def ask(messages):
    data = json.dumps({"model": MODEL, "messages": messages}).encode("utf-8")
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
    return result["choices"][0]["message"]["content"]


def main():
    print("Чат с gemma4. Напиши вопрос (exit — выход).\n")
    history = []
    while True:
        try:
            question = input("Ты: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nПока!")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "выход"):
            print("Пока!")
            break

        history.append({"role": "user", "content": question})
        try:
            answer = ask(history)
        except Exception as e:
            print(f"Ошибка: {e}\n")
            history.pop()
            continue

        history.append({"role": "assistant", "content": answer})
        print(f"\nМодель: {answer}\n")


if __name__ == "__main__":
    main()
