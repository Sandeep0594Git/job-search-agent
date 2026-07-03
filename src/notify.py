"""Send alerts: Telegram (per-job, interactive) + WhatsApp via CallMeBot (digest)."""
import html
import logging
import urllib.parse
from pathlib import Path

import requests

from .config import Secrets

log = logging.getLogger("agent.notify")
TG_API = "https://api.telegram.org/bot{token}/{method}"


# ---------------- Telegram ----------------

def tg_call(method: str, payload: dict) -> dict:
    resp = requests.post(
        TG_API.format(token=Secrets.TELEGRAM_BOT_TOKEN, method=method),
        json=payload, timeout=30,
    )
    data = resp.json()
    if not data.get("ok"):
        log.warning("telegram %s failed: %s", method, data)
    return data


def tg_send(text: str, chat_id: str = None):
    if not Secrets.telegram_ready():
        return
    tg_call("sendMessage", {
        "chat_id": chat_id or Secrets.TELEGRAM_CHAT_ID,
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })


def tg_send_document(path: Path, caption: str = "", chat_id: str = None):
    if not Secrets.telegram_ready():
        return
    with open(path, "rb") as f:
        resp = requests.post(
            TG_API.format(token=Secrets.TELEGRAM_BOT_TOKEN, method="sendDocument"),
            data={"chat_id": chat_id or Secrets.TELEGRAM_CHAT_ID,
                  "caption": caption[:1024]},
            files={"document": (path.name, f)},
            timeout=120,
        )
    if not resp.json().get("ok"):
        log.warning("telegram sendDocument failed: %s", resp.text[:300])


def format_job_alert(job: dict) -> str:
    remote = " · 🏠 Remote" if job.get("is_remote") else ""
    return (
        f"🆕 <b>{html.escape(job['title'])}</b>\n"
        f"🏢 {html.escape(job['company'])} — {html.escape(job['location'])}{remote}\n"
        f"🌐 {html.escape(job['site'])}"
        f"{' · ' + html.escape(job['date_posted']) if job.get('date_posted') else ''}\n"
        f"🔗 <a href=\"{html.escape(job['url'])}\">Open job posting</a>\n\n"
        f"➡️ Reply <code>/tailor {job['id']}</code> for a tailored resume"
    )


# ---------------- WhatsApp (CallMeBot) ----------------

def whatsapp_send(text: str):
    if not Secrets.whatsapp_ready():
        return
    url = (
        "https://api.callmebot.com/whatsapp.php?phone="
        + urllib.parse.quote(Secrets.CALLMEBOT_PHONE)
        + "&text=" + urllib.parse.quote(text[:1500])
        + "&apikey=" + urllib.parse.quote(Secrets.CALLMEBOT_APIKEY)
    )
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            log.warning("callmebot failed (%s): %s", resp.status_code, resp.text[:200])
    except requests.RequestException as e:
        log.warning("callmebot error: %s", e)


# ---------------- Orchestration ----------------

def notify_new_jobs(jobs: list, cfg: dict):
    if not jobs:
        return
    ncfg = cfg.get("notify") or {}
    max_alerts = ncfg.get("max_telegram_alerts_per_run", 12)

    for job in jobs[:max_alerts]:
        tg_send(format_job_alert(job))
    if len(jobs) > max_alerts:
        extra = jobs[max_alerts:]
        lines = [f"…plus {len(extra)} more matches:"]
        lines += [f"• {j['title']} @ {j['company']} — /tailor {j['id']}" for j in extra[:20]]
        tg_send(html.escape("\n".join(lines)))

    if ncfg.get("whatsapp_digest", True):
        lines = [f"🔎 {len(jobs)} new job match(es):"]
        for j in jobs[:8]:
            lines.append(f"- {j['title']} @ {j['company']} ({j['site']}) {j['url']}")
        if len(jobs) > 8:
            lines.append(f"...and {len(jobs) - 8} more (see Telegram)")
        whatsapp_send("\n".join(lines))
