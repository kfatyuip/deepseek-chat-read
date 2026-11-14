# deepseek-chat-read

Read-only `GET /api/v0` session reader for DeepSeek chat.

## Name rationale

- `deepseek-chat-read` — short, no slash, describes exactly what it does (read DeepSeek chat).
- Checked free at creation time: `gh repo view kfatyuip/deepseek-chat-read` returned not-found before creation, and no clone existed at `/home/kfatyuip/ss/deepseek-chat-read`.
- Alternatives considered and rejected:
  - `deepseek/chat-reader` — slash in the name is not suitable for this repo/skill naming (rejected per no-slash convention).
  - `deepseek-reader` — too generic; collides conceptually with unrelated DeepSeek readers.
  - `deepseek-api-reader` — longer, less specific to chat sessions.
  - `ds-chat-read` — abbreviation `ds` is ambiguous.

## Unofficial API disclaimer

This project uses the **unofficial** DeepSeek chat web API (`https://chat.deepseek.com/api/v0/...`).
It is not affiliated with, endorsed by, or supported by DeepSeek.
The API may change or break without notice. Use at your own risk; respect DeepSeek's Terms of Service.

## Token handling — never committed

- Authentication token / session cookie is a secret. It must **never be committed**.
- Supply it via the `DEEPSEEK_WEB_TOKEN` environment variable
  (for example `export DEEPSEEK_WEB_TOKEN='...'` in your shell), which **always wins** when set.
  `--from-firefox` is an explicit opt-in fallback only: it runs only when
  you pass it *and* the env var is unset, extracting the token in memory
  from your own Firefox localStorage (never copied/printed/written).
  Without the flag, Firefox is never read. There is no `--token` flag or token-file option.
- `.gitignore` excludes `.env`, `*.token`, `token.txt`, `cookies*.json`, and similar.
- Before every commit, verify with `git status` / `git diff --cached` that no token is staged.

## Usage

See `skills/deepseek-chat-read/SKILL.md` for the skill contract. Scripts live under `skills/deepseek-chat-read/scripts/`.

```bash
export DEEPSEEK_WEB_TOKEN='...'
python skills/deepseek-chat-read/scripts/deepseek_read.py list --count 20
python skills/deepseek-chat-read/scripts/deepseek_read.py read --chat-session-id <id> --format md
# Explicit opt-in Firefox fallback (only when DEEPSEEK_WEB_TOKEN is unset):
python skills/deepseek-chat-read/scripts/deepseek_read.py list --count 20 --from-firefox
```

## License

Public repo. All rights reserved.

## Layout

The skill itself lives at `skills/deepseek-chat-read/` (SKILL.md + `scripts/`; tests live at repo root `tests/`) so Hermes hub taps can discover it; this README is repo-level docs.
