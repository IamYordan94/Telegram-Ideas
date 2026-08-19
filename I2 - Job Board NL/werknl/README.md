# WerkNL — Amsterdam job board bot

A Telegram bot + channel that connects international workers in Amsterdam with
real jobs in **moving**, **horeca**, and **cleaning**.

- **Workers join free** — pick their sectors, get job alerts.
- **Employers pay** to post jobs (€5/post, €35/10-pack, €59/mo unlimited).
- **You (admin) approve** every job before it goes live — no fake jobs, no junk.

## What the bot does

| Who | What |
|-----|------|
| Worker | `/start` → pick sectors → get job alerts |
| Worker | `/jobs` → today's jobs in their sectors |
| Worker | `/premium` → €1.99/mo instant alerts |
| Employer | `/post` → guided flow to submit a job |
| Employer | `/pricing`, `/myjobs` |
| Admin | `/admin`, `/approve`, `/reject`, `/fill`, `/stats`, `/grant`, `/setpremium`, `/broadcast` |

Every approved job is posted to the channel **and** DM'd instantly to premium
workers in that sector. A daily digest goes out to all workers at the configured
hour.

## Setup (one time, ~5 minutes)

1. **Create the bot** — open https://t.me/BotFather → `/newbot` → give it a name
   (e.g. "WerkNL") and username (e.g. `werknl_bot`). Copy the token.
2. **Create the channel** — in Telegram, New Channel → name it "WerkNL" → set it
   public (get an @username). Then add your bot to the channel as **Admin**.
3. **Get your user id** — message https://t.me/userinfobot and copy your id.
4. **Fill in `.env`** — copy `.env.example` to `.env` and paste the three values.
5. **Run it**:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

Keep the process running (on a machine that stays on) so the bot can receive
messages and send alerts. See "running 24/7" below.

## Seed jobs (make the channel look alive on day 1)

The scraper pulls real public vacancies from RSS feeds so the channel has jobs
before any employer has paid. Feeds live in `data/seed_sources.json`.

```bash
python -m werknl.seed --dry-run   # preview what it finds
python -m werknl.seed             # insert as PENDING (you approve each)
```

Seeded jobs always land as **pending** — you approve them with `/approve <id>`,
so nothing fake ever reaches the channel.

## Tests

```bash
python -m pytest tests/                # if pytest is installed
python3 tests/verify_changes.py        # canonical: plain python, no deps — 18 checks
```

`verify_changes.py` covers contact/button formatting, cmd_jobs buttons, /post
contact validation, seed dedupe, seed_jobs.json, and the db job lifecycle.

## Running 24/7

For now the bot is a single `python main.py` process. Keep it alive on a machine
that stays on (your laptop, plugged in and lid open). Hermes can start and watch
it. (A dedicated server / systemd unit / PM2 is a later upgrade.)
