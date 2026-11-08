---
name: deepseek-chat-read
description: Read-only GET /api/v0 session reader for DeepSeek chat via unofficial API. Use when fetching conversation/message lists from a logged-in DeepSeek session without performing any write operation.
---

# deepseek-chat-read

Read-only reader for DeepSeek chat sessions over the unofficial `GET /api/v0` API.
Backed by `scripts/deepseek_read.py` (stdlib only — no third-party packages).

## Scope

- READ-ONLY. Only `GET` requests. Never `POST`, `PUT`, `DELETE`, or otherwise mutate chat state.
- Session-scoped: operate only on the authenticated user's own sessions.
- No sending messages, no generating, no editing, no deleting.

## Procedure

1. Get the token from your logged-in `chat.deepseek.com` session, either
   way (never into a file in this repo):
   - **Preferred — automatic, from your own Firefox profile.** The script
     reads `userToken` in memory from Firefox's per-origin localStorage
     DB (`storage/default/https+++chat.deepseek.com/ls/data.sqlite`,
     falling back to old `webappsstore.sqlite`). It opens the DB
     read-only/immutable — no copy, no print, no write:
     ```bash
     python scripts/deepseek_read.py list --count 20 --from-firefox
     ```
   - **Fallback — environment variable.** Copy `userToken` from
     DevTools → Application → Local Storage yourself:
     ```bash
     export DEEPSEEK_WEB_TOKEN='...'   # secret — never commit, print, or paste it anywhere
     ```
   Requires Firefox to have visited/logged in to chat.deepseek.com.
   `--firefox-profile <dir>` overrides profile auto-detection.
2. List sessions:
   ```bash
   python scripts/deepseek_read.py list --count 20
   # or: python scripts/deepseek_read.py list --count 20 --format md -o sessions.md
   ```
3. Read one session by id:
   ```bash
   python scripts/deepseek_read.py read --chat-session-id <id>
   # formats: --format json (default) | messages | md
   # or:      python scripts/deepseek_read.py read --chat-session-id <id> --format md -o chat.md
   ```
4. Read a public share (no token needed, no auth header is sent):
   ```bash
   python scripts/deepseek_read.py share --share-id <id> --format md
   ```

Endpoints used (all `GET`, base `https://chat.deepseek.com`):

| Command | Endpoint |
|---|---|
| `list` | `/api/v0/chat_session/fetch_page?count=N` |
| `read` | `/api/v0/chat/history_messages?chat_session_id=<id>` |
| `share` | `/api/v0/share/content?share_id=<id>` (no auth) |

Output formats: `json` (raw payload), `messages` (plain-text transcript),
`md` (Markdown). Without `-o/--output`, output goes to stdout.

## Token handling

- The token comes from `--from-firefox` (your own Firefox profile) or
  the `DEEPSEEK_WEB_TOKEN` environment variable. There is no `--token`
  flag and no token file option.
- Firefox extraction opens the localStorage DB read-only/immutable and
  keeps the token in memory only; it is never copied, printed, logged,
  or written to disk. `.gitignore` blocks
  `.env`, `*.token`, `token.txt`, `cookies*.json`, and similar.
- Missing token: the script exits with an error naming the variable only.

## Safety

- Treat the token as a credential: do not log it, do not include it in URLs
  that get logged, do not paste it into issues/PRs.
- If the unofficial API changes shape or returns 401/403, stop and report —
  do not retry with write methods or scrape with automated login.
- Unofficial API: not affiliated with or endorsed by DeepSeek; may break
  without notice. Respect DeepSeek's Terms of Service.
