# Troubleshooting Log

## 1. Empty folders missing from Git
- **Symptom:** `app/`, `infra/` and `scripts/` didn't appear in `git status`, while `docs/` did.
- **Cause:** Git tracks files, not folders. Empty directories are invisible to it.
- **Fix:** Added a `.gitkeep` placeholder file to each empty folder.
- **Lesson:** Git tracks content, not structure.
## 2. Secrets would have been copied into the image (prevented)
- **Risk:** `COPY . .` in the Dockerfile would have copied `app/.env`, including the database password, into the image.
- **Fix:** Added `app/.dockerignore` excluding `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/` and `tests/`.
- **Verified:** Listed the image contents (`docker run --rm referral-tracker:dev ls -la /app`) and confirmed `.env` was absent.
- **Lesson:** Secrets are passed in at runtime (`--env-file`), never baked in at build time.

## 3. App container couldn't reach the database ("connection refused")
- **Symptom:** App container exited: `connection to server at "127.0.0.1", port 5432 failed: Connection refused`.
- **Cause:** Inside a container, `localhost` means the container itself, not the host. Postgres runs in a different container.
- **Fix:** Created a user-defined Docker network (`referrals-net`), connected both containers to it, and changed the host in `DATABASE_URL` to the container name.
- **Lesson:** Read the last line of a traceback first. Always ask "localhost from whose point of view?"

## 4. Database hostname not found ("Name or service not known")
- **Symptom:** After the network fix, startup failed with `Name or service not known`.
- **Investigation:** Checked four suspects one at a time: container state (`docker ps -a`), network membership (`docker network inspect`), hostname in config (`grep` on `.env`), and DNS resolution from inside the network (`socket.gethostbyname`).
- **Cause:** Two faults: a typo in the hostname (`referral-db` instead of `referrals-db`), and the database container was stopped.
- **Fix:** Corrected the hostname and started the container.
- **Lesson:** A changed error message means progress. Check every suspect, because more than one can be true.
