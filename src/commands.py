"""Poll Telegram for commands the user sent since the last run and act on them.
Runs at the start of every scheduled cycle, so a '/tailor <id>' reply is
answered within one cron interval."""
import html
import logging

from . import store
from .config import Secrets
from .notify import tg_call, tg_send, tg_send_document
from .tailor import tailor_resume

log = logging.getLogger("agent.commands")

HELP = (
    "🤖 <b>Job Search Agent</b>\n\n"
    "/tailor &lt;job-id&gt; — analyze the JD and send back a tailored resume (.docx)\n"
    "/recent — list the last 10 jobs found\n"
    "/help — this message\n\n"
    "Job ids are shown in every alert. New jobs are checked every ~30 min."
)


def _handle_tailor(job_ref: str, cfg: dict):
    catalog = store.load_catalog()
    job = catalog.get(job_ref.strip())
    if not job:
        tg_send(f"⚠️ Job id <code>{html.escape(job_ref)}</code> not found. "
                "Use /recent to list available ids.")
        return
    tg_send(f"⏳ Tailoring your resume for <b>{html.escape(job['title'])}</b> "
            f"@ {html.escape(job['company'])} …")
    try:
        analysis, docx_path = tailor_resume(job, cfg)
    except Exception as e:
        log.exception("tailoring failed")
        tg_send(f"❌ Tailoring failed: {html.escape(str(e))}")
        return
    if analysis:
        tg_send(f"📊 <b>Fit analysis</b>\n{html.escape(analysis)}")
    tg_send_document(docx_path,
                     caption=f"Tailored resume — {job['title']} @ {job['company']}")


def _handle_recent():
    catalog = store.load_catalog()
    jobs = list(catalog.values())[-10:]
    if not jobs:
        tg_send("No jobs in the catalog yet.")
        return
    lines = ["🗂 <b>Recent jobs</b>"]
    for j in reversed(jobs):
        lines.append(f"• {html.escape(j['title'])} @ {html.escape(j['company'])} "
                     f"— <code>/tailor {j['id']}</code>")
    tg_send("\n".join(lines))


def process_commands(cfg: dict):
    if not Secrets.telegram_ready():
        return
    offset = store.load_offset()
    data = tg_call("getUpdates", {"offset": offset + 1, "timeout": 0})
    updates = data.get("result") or []

    for upd in updates:
        offset = max(offset, upd["update_id"])
        msg = upd.get("message") or upd.get("edited_message") or {}
        text = (msg.get("text") or "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if not text or chat_id != str(Secrets.TELEGRAM_CHAT_ID):
            continue  # ignore strangers and non-text updates

        log.info("command: %s", text)
        if text.startswith("/tailor"):
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                _handle_tailor(parts[1], cfg)
            else:
                tg_send("Usage: <code>/tailor &lt;job-id&gt;</code>")
        elif text.startswith("/recent"):
            _handle_recent()
        elif text.startswith(("/help", "/start")):
            tg_send(HELP)
        else:
            # anything else: don't leave the user hanging in silence
            tg_send("🤖 I only understand commands, not chat.\n\n" + HELP)

    store.save_offset(offset)
