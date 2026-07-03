"""Job Search Agent — one cycle:
1. Answer any Telegram commands received since last run (/tailor, /recent, /help)
2. Search portals for new jobs matching the configured keywords
3. Alert via Telegram (per job) + WhatsApp digest

Designed to run on a GitHub Actions cron every ~30 minutes (free), or locally.
"""
import logging
import sys

from src.commands import process_commands
from src.config import Secrets, load_config
from src.notify import notify_new_jobs
from src.search import run_search

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("agent")


def main() -> int:
    cfg = load_config()

    if not Secrets.telegram_ready():
        log.warning("Telegram secrets missing - alerts and commands disabled.")
    if not Secrets.whatsapp_ready():
        log.info("CallMeBot secrets missing - WhatsApp mirror disabled.")

    only_commands = "--commands-only" in sys.argv
    skip_commands = "--search-only" in sys.argv

    if not skip_commands:
        log.info("processing Telegram commands...")
        process_commands(cfg)

    if not only_commands:
        log.info("searching job portals...")
        jobs = run_search(cfg)
        notify_new_jobs(jobs, cfg)
        log.info("cycle complete: %d new job(s) alerted", len(jobs))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
