# Troubleshooting Log

## 1. Empty folders missing from Git
- **Symptom:** `app/`, `infra/` and `scripts/` didn't appear in `git status`, while `docs/` did.
- **Cause:** Git tracks files, not folders. Empty directories are invisible to it.
- **Fix:** Added a `.gitkeep` placeholder file to each empty folder.
- **Lesson:** Git tracks content, not structure.