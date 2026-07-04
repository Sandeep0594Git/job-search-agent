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
    "/apply &lt;job-id&gt; — full application pack: fit analysis, tailored "
    "resume + cover letter (.docx), and the apply link\n"
    "/tailor &lt;job-id&gt; — tailored resume + fit analysis only\n"
    "/recent — list the last 10 jobs found\n"
    "/help — this message\n\n"
    "Job ids are shown in every alert. New jobs are checked every ~30 min."
)


def _handle_tailor(job_ref: str, cfg: dict, full_pack: bool = False):
    catalog = store.load_catalog()
    job = catalog.get(job_ref.strip())
    if not job:
        tg_send(f"⚠️ Job id <code>{html.escape(job_ref)}</code> not found. "
                "Use /recent to list available ids.")
        return
    what = "application pack" if full_pack else "resume"
    tg_send(f"⏳ Preparing your {what} for <b>{html.escape(job['title'])}</b> "
            f"@ {html.escape(job['company'])} …")
    try:
        analysis, resume_path, cover_path = tailor_resume(job, cfg)
    except Exception as e:
        log.exception("tailoring failed")
        tg_send(f"❌ Tailoring failed: {html.escape(str(e))}")
        return
    if analysis:
        tg_send(f"📊 <b>Fit analysis</b>\n{html.escape(analysis)}")
    tg_send_document(resume_path,
                     caption=f"Tailored resume — {job['title']} @ {job['company']}")
    if full_pack:
        if cover_path:
            tg_send_document(cover_path,
                             caption=f"Cover letter — {job['title']} @ {job['company']}")
        tg_send(
            "🚀 <b>Ready to apply</b>\n"
            f"1. Review both documents (30 sec sanity check)\n"
            f"2. <a href=\"{html.escape(job['url'])}\">Open the application page</a>\n"
            "3. Upload, submit, done.\n\n"
            "I don't submit for you — portals ban bot accounts, and your "
            "profile is worth more than two saved clicks."
        )


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
        if text.startswith(("/tailor", "/apply")):
            cmd = "/apply" if text.startswith("/apply") else "/tailor"
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                _handle_tailor(parts[1], cfg, full_pack=(cmd == "/apply"))
            else:
                tg_send(f"Usage: <code>{cmd} &lt;job-id&gt;</code>")
        elif text.startswith("/recent"):
            _handle_recent()
        elif text.startswith(("/help", "/start")):
            tg_send(HELP)
        else:
            # anything else: don't leave the user hanging in silence
            tg_send("🤖 I only understand commands, not chat.\n\n" + HELP)

    store.save_offset(offset)
