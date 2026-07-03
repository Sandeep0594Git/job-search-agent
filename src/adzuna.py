"""Adzuna - official free job-search API (https://developer.adzuna.com).
Aggregates postings from company career portals and job boards that
LinkedIn/Indeed often miss. No scraping, so it never gets blocked.
Enabled automatically when ADZUNA_APP_ID + ADZUNA_APP_KEY are set."""
import logging
import os
import re

import requests

from . import store

log = logging.getLogger("agent.adzuna")
API = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def _clean(text: str) -> str:
    return re.sub(r"</?strong>", "", text or "").strip()


def search_adzuna(cfg: dict) -> list:
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not (app_id and app_key):
        return []

    acfg = (cfg.get("search") or {}).get("adzuna") or {}
    params = {
        "app_id": app_id,
        "app_key": app_key,
        # what_or matches ANY of these words - one API call covers all roles;
        # the shared any_keywords filter still applies downstream.
        "what_or": acfg.get("what_or", "presales solution consultant cloud"),
        "where": acfg.get("where", "India"),
        "max_days_old": acfg.get("max_days_old", 1),
        "results_per_page": min(int(acfg.get("results", 50)), 50),
        "sort_by": "date",
        "content-type": "application/json",
    }
    try:
        resp = requests.get(API.format(country=acfg.get("country", "in")),
                            params=params, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results") or []
    except Exception as e:
        log.warning("adzuna search failed: %s", e)
        return []

    jobs = []
    for item in results:
        url = item.get("redirect_url") or ""
        if not url:
            continue
        jobs.append({
            "id": store.job_id(url),
            "title": _clean(item.get("title")),
            "company": (item.get("company") or {}).get("display_name", ""),
            "location": (item.get("location") or {}).get("display_name", ""),
            "site": "adzuna",
            "url": url,
            "date_posted": (item.get("created") or "")[:10],
            "is_remote": False,
            "description": item.get("description") or "",
        })
    log.info("adzuna returned %d jobs", len(jobs))
    return jobs
