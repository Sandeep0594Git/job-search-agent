# 🔎 Job Search Agent (100% free stack)

An autonomous agent that:

1. **Searches** LinkedIn, Naukri and Indeed every 30 minutes for your target roles
2. **Filters** by your keywords (title + job description)
3. **Alerts you instantly** on Telegram (per job) and WhatsApp (digest)
4. **Tailors your resume** — reply `/tailor <job-id>` in Telegram and it analyzes
   the JD with Gemini and sends back a customized `.docx` resume + fit analysis

| Component | Service | Cost |
|---|---|---|
| Job scraping | [JobSpy](https://github.com/speedyapply/JobSpy) (open source) | Free |
| Scheduler / compute | GitHub Actions cron | Free |
| Alerts | Telegram Bot API | Free |
| WhatsApp mirror | CallMeBot | Free |
| JD analysis + resume tailoring | Google Gemini API free tier | Free |

---

## Setup (one time, ~15 minutes)

### 1. Telegram bot (2 min)
1. In Telegram, open **@BotFather** → send `/newbot` → pick a name → copy the **token**.
2. Open a chat with your new bot and send it any message (e.g. "hi").
3. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and
   copy the `"chat":{"id": ...}` number. That's your **chat id**.

### 2. WhatsApp via CallMeBot (2 min, optional)
1. Save **+34 644 66 32 62** in your phone contacts.
2. From WhatsApp, send it: `I allow callmebot to send me messages`
3. It replies with your **apikey**. Your phone number (with country code, e.g.
   `+9198...`) + this apikey are your credentials.

### 3. Gemini API key (1 min)
Get a free key at https://aistudio.google.com/apikey (no card required).

### 4. Baseline resume
Drop your resume (`.pdf` / `.docx` / `.md` / `.txt`) into the `resume/` folder.

### 5. Deploy to GitHub (5 min)
```bash
git init
git add -A
git commit -m "job search agent"
# create a PRIVATE repo on github.com, then:
git remote add origin https://github.com/<you>/job-search-agent.git
git push -u origin main
```
> **Private repo?** Also remove the `resume/*` line from `.gitignore` and commit
> your resume, so Actions can use it. Private repos get 2,000 free Actions
> minutes/month — at 30-min cadence that's tight, so either make the repo
> **public** (unlimited minutes; keep your resume out and use the `RESUME_B64`
> secret from `.env.example`) or relax the cron to hourly (`0 * * * *`).

Then in the repo: **Settings → Secrets and variables → Actions** → add:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | from BotFather |
| `TELEGRAM_CHAT_ID` | from getUpdates |
| `CALLMEBOT_PHONE` | your WhatsApp number, e.g. `+9198…` |
| `CALLMEBOT_APIKEY` | from CallMeBot |
| `GEMINI_API_KEY` | from AI Studio |
| `RESUME_B64` / `RESUME_EXT` | only for public repos (see `.env.example`) |

Finally: **Actions tab → Job Search Agent → Run workflow** to test. After that
it runs itself every 30 minutes.

---

## Daily use

- New matching jobs arrive in Telegram as they're found; WhatsApp gets a digest.
- Want to apply? Reply in Telegram:
  - `/tailor a1b2c3d4` → fit analysis + tailored `.docx` resume for that job
  - `/recent` → list the last 10 jobs with their ids
  - `/help` → command reference
- Commands are answered on the next cycle (within ~30 min). Trigger the
  workflow manually from the Actions tab if you want an answer right now.

## Tuning

Everything lives in [config.yaml](config.yaml): search terms, portals,
locations, keyword filters, lookback window, alert caps, Gemini model.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # then fill in your keys
.venv\Scripts\python main.py
```

## Honest limitations (free-tier physics)

- **"Real time" = every 30 min.** GitHub cron can also drift 5–15 min at busy hours.
- **Scraping isn't an official API.** LinkedIn/Naukri occasionally rate-limit a
  run; the agent logs it and catches those jobs on the next cycle. LinkedIn's
  ToS prohibits scraping — this is personal, low-volume use, but be aware.
- **True SMS is never free** — that's why Telegram/WhatsApp.
- **Gemini free tier** has daily limits; more than ~50 tailored resumes/day
  would need a paid key (you won't hit this).
