# App architecture

This document is for whoever runs the app, not whoever develops it. It covers what each file does, how the app reaches the database, which port it listens on, every setting, and how `/health` works.

## What the app is

It's one Python process. The web framework is **FastAPI**, and **Uvicorn** is the web server that runs it. The app builds plain HTML pages on the server (using **Jinja2** templates) and sends them to the browser. There's no separate frontend, no JavaScript build step and no static files. The only thing it depends on is a **PostgreSQL** database.

```
Browser ──HTTP──▶ Uvicorn + FastAPI (APP_PORT, default 8000) ──TCP──▶ PostgreSQL (from DATABASE_URL)
                         │
                         └──▶ stdout (JSON logs, one line per event)
```

The app keeps no state on disk. Everything lives in the database, so you can stop, replace or restart the container at any time.

## Files

| File | What it does |
|---|---|
| `main.py` | The app itself. It defines the web pages and `/health`, creates the tables on startup, and logs every request. Run `python main.py` to start the web server. |
| `config.py` | Reads every setting from environment variables. If `DATABASE_URL` is missing or a number setting isn't a number, the app refuses to start and says why. |
| `database.py` | Opens the database connection (the "engine"), hands out one connection per request, provides the "is the database reachable?" check used by `/health`, and creates the tables. |
| `models.py` | Defines the `referrals` table: its columns and the allowed values for priority and status. |
| `logging_config.py` | Turns all logs into JSON on stdout. It only lets a fixed list of safe fields through (event names, IDs, statuses, HTTP method/path/status code), so referral details can't end up in the logs. |
| `seed.py` | Inserts 15 made-up referrals (SYN-1001 to SYN-1015) so the board has something on it. Safe to run more than once: it skips any references that already exist. |
| `templates/` | The HTML pages: `base.html` (shared layout), `board.html`, `new.html` (add form) and `edit.html` (change status). |
| `tests/` | Automated tests (pytest). They use a temporary SQLite file instead of PostgreSQL, so no database server is needed to run them. |
| `pytest.ini` | Tells pytest where the tests are. |
| `requirements.txt` | Python packages the app needs to run, with exact versions. Install these in the image. |
| `requirements-dev.txt` | Everything in `requirements.txt` plus the test tools. You don't need it in production. |
| `.env.example` | A template listing every environment variable. Copy it to `.env` (which git ignores) and fill it in. |

## Pages and endpoints

| Method + path | Purpose |
|---|---|
| `GET /` | The board. Urgent referrals come first, then the longest waits. Overdue rows are highlighted. |
| `GET /referrals/new` | The form for adding a referral. |
| `POST /referrals/new` | Saves a new referral, then redirects to the board. References must look like `SYN-1234` (synthetic only). |
| `GET /referrals/{id}` | The page for changing a referral's status. |
| `POST /referrals/{id}/status` | Saves the new status, then redirects to the board. |
| `GET /health` | The health check (see below). |

A referral counts as overdue when it isn't `seen` yet and has waited longer than its threshold: `URGENT_THRESHOLD_DAYS` for urgent referrals, `ROUTINE_THRESHOLD_DAYS` for routine ones. "Days waiting" means today's date minus the date received.

## Port

The app listens on `APP_HOST:APP_PORT`, which is `0.0.0.0:8000` by default. Leave `APP_HOST` as `0.0.0.0` inside a container. If you change it to `127.0.0.1`, nothing outside the container can reach the app. The app speaks plain HTTP. HTTPS should end at the load balancer.

**Start command** (run it from the `app/` folder, after the environment variables are set):

```
python main.py
```

## Database connection

- The app gets its connection details from **`DATABASE_URL`**, in this format:
  `postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME`
  (`postgresql+psycopg` means "PostgreSQL, using the psycopg driver".) Characters such as `@`, `:` or `/` in the password must be URL-encoded, for example `@` becomes `%40`.
- The connection library (SQLAlchemy) keeps a small **pool** of open connections and reuses them. It checks that a pooled connection still works before using it ("pre-ping"), so the app recovers by itself after a database restart.
- Connecting gives up after **`DB_CONNECT_TIMEOUT`** seconds. Without this limit, a database that's down could make requests and health checks hang.
- Database error messages never include the values the app was saving (SQLAlchemy's `hide_parameters` is on), so referral details can't leak into logs through errors.
- **Tables are created on startup.** There's no migration tool. If the `referrals` table doesn't exist yet, the app creates it. If it already exists, the app leaves it alone (it never drops or changes it). The database user therefore needs permission to create tables in that database.
- **If the database isn't up yet at startup**, the app tries 5 times, 2 seconds apart (about 10 seconds in total). If it still can't connect, it logs `startup_failed` and exits with an error. Pair this with a container restart policy (for example `restart: unless-stopped` / `--restart unless-stopped`) so it keeps retrying until the database is ready.

## Environment variables

| Variable | Required? | Default | What it does |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | none (the app won't start without it) | PostgreSQL connection string (see above). It contains the password, so treat it as a secret. |
| `APP_HOST` | No | `0.0.0.0` | The network interface to listen on. |
| `APP_PORT` | No | `8000` | The TCP port to listen on. |
| `URGENT_THRESHOLD_DAYS` | No | `14` | How many days an urgent referral can wait before it's flagged. |
| `ROUTINE_THRESHOLD_DAYS` | No | `42` | How many days a routine referral can wait before it's flagged. |
| `DB_CONNECT_TIMEOUT` | No | `3` | How many seconds to wait for a database connection before giving up. |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |

The app does **not** read the `.env` file itself. Something else has to load it:
- Docker: `docker run --env-file .env ...`, or `env_file:` in compose.
- A local shell: `set -a; source .env; set +a` before `python main.py`.

## How `/health` works

1. The load balancer (or you) sends `GET /health`.
2. The app borrows a database connection and runs `SELECT 1`, the simplest query there is.
3. If that works, the response is **HTTP 200** with `{"status":"ok"}`.
4. If it fails for any reason (the database is down, the password is wrong, the network is blocked, or there's no reply within `DB_CONNECT_TIMEOUT` seconds), the response is **HTTP 503** with `{"status":"unavailable","database":"unreachable"}`, and the app logs a `health_db_unreachable` warning.

As a result, a 503 means "the app is running but can't reach its database". If you get no response at all, the app process itself is down or unreachable. Keep the load balancer's health check timeout higher than `DB_CONNECT_TIMEOUT`. The defaults (5 s for the ALB, 3 s for the app) are fine together.

## Logging

- Everything goes to **stdout**, one JSON object per line, ready for Docker's log driver and CloudWatch Logs.
- Each line has `timestamp` (UTC), `level`, `logger` and `message`, plus some of: `event`, `referral_id`, `old_status`, `new_status`, `priority`, `method`, `path`, `status_code`, `duration_ms`, `count`, `attempt`, `error`.
- Main events: `app_started`, `startup_tables_ready`, `startup_db_unavailable`, `startup_failed`, `http_request`, `referral_created`, `referral_status_updated`, `health_db_unreachable`, `seed_complete`.
- **Referral details are never logged.** The reference and the referring practice never appear. Request logs record only the path (such as `/referrals/7/status`), never the query string or form contents. When an error occurs, the log records only the exception type, not its message. This rule is enforced in `logging_config.py`, and a test checks it.

Example line:

```json
{"timestamp": "2026-11-22T10:15:03.120000+00:00", "level": "INFO", "logger": "referral_tracker", "message": "referral status updated", "event": "referral_status_updated", "referral_id": 7, "old_status": "triaged", "new_status": "booked"}
```

## Common tasks

Run all of these from the `app/` folder.

```
pip install -r requirements.txt          # install the app's packages
python main.py                           # start the app (needs the env vars set)
python seed.py                           # add the 15 synthetic referrals
pip install -r requirements-dev.txt      # install the test tools
pytest                                   # run the tests (no database needed)
```

## Known limitations

- **No authentication.** Anyone who can reach the port can view and change referrals. Restrict access at the network level.
- No audit history: the app records the latest status and `updated_at`, but not who made a change or what the earlier statuses were.
- No migrations: if a column changes in future, you'll have to update the existing table by hand.
- Synthetic data only: the reference format (`SYN-` followed by digits) is enforced, and every page shows a banner saying so.
