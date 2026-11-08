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
- Supply it via environment variable `DEEPSEEK_TOKEN` or a local untracked file (e.g. `.env`).
- `.gitignore` excludes `.env`, `*.token`, `token.txt`, `cookies*.json`, and similar.
- Before every commit, verify with `git status` / `git diff --cached` that no token is staged.

## Usage

See `SKILL.md` for the skill contract. Scripts live under `scripts/`.

```bash
export DEEPSEEK_TOKEN='...'   # never commit this
python scripts/reader.py --list-sessions   # placeholder — see scripts/
```

## License

Private repo. All rights reserved.
