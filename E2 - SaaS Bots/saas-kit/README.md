# BoardKit — sell the WerkNL machine to other cities/sectors

Each customer gets **their own bot** (the WerkNL machine with their name and city) plus their own job database. One laptop runs all boards.

## How a new customer goes live (≈30 minutes)

1. **Customer creates a bot** in Telegram: chat with @BotFather → `/newbot` → name + username → they get a token. (2 minutes.)
2. **Customer creates a public channel** (or uses an existing one) and adds their new bot as **admin** with "Post Messages".
3. You run:

```
python3 kit.py add rotterdam "Rotterdam Werkt" Rotterdam <TOKEN> <CHANNEL_ID> <CUSTOMER_TELEGRAM_ID> --username @rotterdam_werkt
```

4. Start it (and everything else): `python3 kit.py run`
5. Tell them the subscription: `/paid` tracking —

```
python3 kit.py paid rotterdam 30      # +30 days
python3 kit.py suspend rotterdam      # stop digest/posting
python3 kit.py activate rotterdam     # resume
python3 kit.py list                   # everything at a glance
python3 kit.py stop rotterdam         # stop one board
```

## Every-day commands

| Command | What it does |
|---|---|
| `kit.py run` | starts every active, paid board that isn't running (safe to re-run — it skips running ones) |
| `kit.py list` | status, paid-until, running or not |
| `kit.py paid <slug> <days>` | extend the subscription |
| `kit.py stop all` | stop everything (laptop reboot prep, etc.) |

## How it works inside

- Each board = a folder `boards/<slug>/` with its own `.env` (token, channel, brand, city), `data/board.db` (its own jobs/workers/employers), and a generated `main.py`.
- The generated `main.py` points at the shared WerkNL code (`I2 - Job Board NL/werknl`) — one codebase, many boards. WerkNL itself keeps running exactly as before (defaults untouched).
- Payment is manual: `kit.py paid` writes the date; `run` skips unpaid/suspended boards. No automatic billing yet.

## Notes / honest limits

- **The customer brings the audience.** We run the machine; they promote their city's channel and sell placements (their pricing, their income).
- The laptop is the infrastructure — it must stay on and plugged in (same as WerkNL).
- Seeding a new board: the board starts empty. Seed it like WerkNL — real public listings for that city via `web_extract` → JSON → the seed CLI inside the werknl folder, pointed at the board's database.
- A board's bot must be an admin of its channel **before** the first post, or posting fails silently into boot.log.
