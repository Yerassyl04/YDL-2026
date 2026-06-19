"""Скрейпер сайта фонда. Обходит внутренние страницы одного домена
и извлекает текстовое содержимое (программы, гранты, FAQ, контакты и т.д.).
"""
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import config

HEADERS = {"User-Agent": "Mozilla/5.0 (YessenovFoundation KB crawler)"}
SKIP_EXT = re.compile(
    r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|rar|docx?|xlsx?|pptx?|mp4|mp3|avi|ico|css|js)(\?|$)",
    re.I,
)
# Языковые дубли: одна и та же страница доступна как /, /ru/, /en/, /kk/.
# Краулим только канонические URL без префикса (это русская версия),
# чтобы не тратить бюджет страниц на копии того же контента.
LANG_PREFIX = re.compile(r"^https?://[^/]+/(ru|en|kk|kz)(/|$)", re.I)


def _clean_url(url):
    url, _, _ = url.partition("#")
    return url.rstrip("/")


def scrape_site(base_url=None, max_pages=None, delay=None, progress=None):
    """Возвращает список документов: [{url, title, text}, ...]."""
    base_url = base_url or config.SCRAPE_BASE_URL
    max_pages = max_pages or config.SCRAPE_MAX_PAGES
    delay = config.SCRAPE_DELAY if delay is None else delay

    start = _clean_url(base_url)
    parsed = urlparse(start)
    root = f"{parsed.scheme}://{parsed.netloc}"

    to_visit = [start]
    visited = set()
    docs = []
    contact_doc = None  # отдельный документ с контактами из подвала сайта

    while to_visit and len(docs) < max_pages:
        url = to_visit.pop(0)
        cu = _clean_url(url)
        if cu in visited:
            continue
        visited.add(cu)

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException:
            continue
        if r.status_code != 200 or "text/html" not in r.headers.get("Content-Type", ""):
            continue

        soup = BeautifulSoup(r.text, "lxml")
        # Сначала вытащим контакты из footer (он есть только на главной),
        # затем удалим повторяющийся «обвес»: меню/шапку/навигацию, иначе
        # одно и то же меню попадает в каждый чанк и портит поиск.
        # footer удаляем уже ПОСЛЕ извлечения контактов (ниже).

        # Один раз собираем контакты из подвала (footer) как отдельный документ.
        if contact_doc is None:
            footer = soup.find("footer")
            if footer:
                ftext = re.sub(r"\n{2,}", "\n", footer.get_text("\n")).strip()
                has_email = "@" in ftext
                has_phone = re.search(r"\+?7[\s\-\(]?\d{3}", ftext)
                if has_email or has_phone:
                    contact_doc = {
                        "url": cu,
                        "title": "Контакты фонда Шахмардана Есенова",
                        "text": "Контакты фонда Шахмардана Есенова "
                                "(адрес, телефон, email, социальные сети):\n" + ftext,
                    }

        # Ссылки собираем ДО удаления меню — навигация ведёт к страницам программ.
        for a in soup.find_all("a", href=True):
            link = _clean_url(urljoin(url, a["href"]))
            if (link.startswith(root)
                    and link not in visited
                    and not SKIP_EXT.search(link)
                    and not LANG_PREFIX.match(link)):
                to_visit.append(link)

        # Теперь убираем повторяющийся «обвес»: меню, шапку, навигацию, подвал —
        # чтобы в текст страницы не попадало одинаковое меню сайта.
        for tag in soup(["script", "style", "noscript", "svg", "iframe",
                         "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        title = soup.title.string.strip() if (soup.title and soup.title.string) else cu
        text = re.sub(r"\n{2,}", "\n", soup.get_text("\n")).strip()

        if len(text) > 200:
            docs.append({"url": cu, "title": title, "text": text})
            if progress:
                progress(len(docs), cu)

        time.sleep(delay)

    if contact_doc is not None:
        docs.append(contact_doc)
        if progress:
            progress(len(docs), contact_doc["url"] + " (контакты)")

    return docs
