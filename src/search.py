"""Search job portals via JobSpy and return new, keyword-matched jobs."""
import logging

import pandas as pd
from jobspy import scrape_jobs

from . import store
from .adzuna import search_adzuna

log = logging.getLogger("agent.search")


def _matches_filters(title: str, description: str, filters: dict) -> bool:
    title_l = (title or "").lower()

    for bad in filters.get("exclude_title_keywords") or []:
        if bad.lower() in title_l:
            return False

    # Title gate: the job TITLE itself must contain a role keyword. This is
    # what keeps loosely-related portal results (Analyst, Sales...) out.
    title_any = filters.get("title_any_keywords") or []
    if title_any and not any(kw.lower() in title_l for kw in title_any):
        return False

    any_kw = filters.get("any_keywords") or []
    if any_kw:
        haystack = title_l + " " + (description or "").lower()
        if not any(kw.lower() in haystack for kw in any_kw):
            return False
    return True


def _row_to_job(row) -> dict:
    url = str(row.get("job_url") or "")
    return {
        "id": store.job_id(url),
        "title": str(row.get("title") or "").strip(),
        "company": str(row.get("company") or "").strip(),
        "location": str(row.get("location") or "").strip(),
        "site": str(row.get("site") or "").strip(),
        "url": url,
        "date_posted": str(row.get("date_posted") or ""),
        "is_remote": bool(row.get("is_remote") or False),
        "description": str(row.get("description") or ""),
    }


def run_search(cfg: dict) -> list:
    """Scrape all configured term x location combos, dedupe against history,
    apply keyword filters. Returns list of new job dicts (also catalogued)."""
    s = cfg["search"]
    filters = cfg.get("filters") or {}
    seen = store.load_seen()
    catalog = store.load_catalog()

    def ingest(job: dict):
        if not job["url"] or job["id"] in seen:
            return
        seen.add(job["id"])  # mark even if filtered, so we never re-check
        if not _matches_filters(job["title"], job["description"], filters):
            return
        catalog[job["id"]] = job
        new_jobs.append(job)

    new_jobs = []
    for term in s["terms"]:
        for location in s["locations"]:
            try:
                df = scrape_jobs(
                    site_name=s["sites"],
                    search_term=term,
                    location=location,
                    results_wanted=s.get("results_per_search", 10),
                    hours_old=s.get("lookback_hours", 6),
                    country_indeed=s.get("country_indeed", "india"),
                    is_remote=False,  # don't restrict; remote included by default
                    linkedin_fetch_description=True,
                    verbose=0,
                )
            except Exception as e:  # portals rate-limit / block sporadically
                log.warning("scrape failed for %r @ %r: %s", term, location, e)
                continue

            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                continue

            for _, row in df.iterrows():
                ingest(_row_to_job(row))

    # Adzuna: career-portal aggregator via official API (one call per cycle)
    for job in search_adzuna(cfg):
        ingest(job)

    store.save_seen(seen)
    store.save_catalog(catalog)
    log.info("found %d new matching jobs", len(new_jobs))
    return new_jobs
