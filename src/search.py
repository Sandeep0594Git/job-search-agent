"""Search job portals via JobSpy and return new, keyword-matched jobs."""
import logging

import pandas as pd
from jobspy import scrape_jobs

from . import store

log = logging.getLogger("agent.search")


def _matches_filters(title: str, description: str, filters: dict) -> bool:
    title_l = (title or "").lower()
    desc_l = (description or "").lower()
    haystack = title_l + " " + desc_l

    for bad in filters.get("exclude_title_keywords") or []:
        if bad.lower() in title_l:
            return False

    any_kw = filters.get("any_keywords") or []
    if not any_kw:
        return True
    return any(kw.lower() in haystack for kw in any_kw)


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
                job = _row_to_job(row)
                if not job["url"] or job["id"] in seen:
                    continue
                seen.add(job["id"])  # mark even if filtered, so we never re-check
                if not _matches_filters(job["title"], job["description"], filters):
                    continue
                catalog[job["id"]] = job
                new_jobs.append(job)

    store.save_seen(seen)
    store.save_catalog(catalog)
    log.info("found %d new matching jobs", len(new_jobs))
    return new_jobs
