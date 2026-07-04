"""Turn a pasted job URL (or raw pasted JD text) into a job dict the
tailoring pipeline understands."""
import html as htmllib
import logging
import re

import requests

from . import store

log = logging.getLogger("agent.jd_fetch")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _html_to_text(html: str) -> str:
    html = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", htmllib.unescape(html)).strip()


def _page_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    return re.sub(r"\s+", " ", htmllib.unescape(m.group(1))).strip()[:120] if m else ""


def job_from_url(url: str) -> dict:
    """Fetch a job posting page and extract its text. Raises ValueError with
    a user-friendly message if the page can't be read."""
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=30,
                            allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"couldn't fetch that link ({e.__class__.__name__}). "
                         "The site may block bots - paste the JD text instead.")

    text = _html_to_text(resp.text)
    if len(text) < 300:
        raise ValueError("that page returned almost no readable text (likely "
                         "JavaScript-only or login-walled). Paste the JD text instead.")

    job = {
        "id": store.job_id(url),
        "title": _page_title(resp.text) or "(from your link)",
        "company": "",  # Gemini infers it from the description
        "location": "",
        "site": "link",
        "url": url,
        "date_posted": "",
        "is_remote": False,
        "description": text[:20000],
    }
    catalog = store.load_catalog()
    catalog[job["id"]] = job
    store.save_catalog(catalog)
    return job


def job_from_text(jd_text: str) -> dict:
    """Wrap raw pasted JD text as a job dict."""
    job = {
        "id": store.job_id(jd_text[:500]),
        "title": "(from pasted JD)",
        "company": "",
        "location": "",
        "site": "pasted",
        "url": "",
        "date_posted": "",
        "is_remote": False,
        "description": jd_text[:20000],
    }
    catalog = store.load_catalog()
    catalog[job["id"]] = job
    store.save_catalog(catalog)
    return job
