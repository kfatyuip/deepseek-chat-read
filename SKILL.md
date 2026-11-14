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

1. Get the token from the `DEEPSEEK_WEB_TOKEN` environment variable
   (never into a file in this repo). It **always wins** when set — even
   if `--from-firefox` is also passed, the env var is used and Firefox
   is not read at all:
   ```bash
   export DEEPSEEK_WEB_TOKEN='...'   # secret — never commit, print, or paste it anywhere
   ```
2. **Explicit opt-in only — Firefox extraction.** `--from-firefox`
   runs *only* when you explicitly pass it *and* the env var is unset.
   Without the flag, Firefox is never touched, even if a profile exists.
   With it, the script reads `userToken` in memory from Firefox's
   per-origin localStorage DB (`storage/default/https+++chat.deepseek.com/ls/data.sqlite`,
   falling back to old `webappsstore.sqlite`). It opens the DB
   read-only/immutable — no copy, no print, no write. Requires Firefox
   to have visited/logged in to chat.deepseek.com.
   `--firefox-profile <dir>` overrides profile auto-detection.
   ```bash
   python scripts/deepseek_read.py list --count 20 --from-firefox
   ```
3. List sessions:
   ```bash
   python scripts/deepseek_read.py list --count 20
   # or: python scripts/deepseek_read.py list --count 20 --format md -o sessions.md
   ```
4. Read one session by id:
   ```bash
   python scripts/deepseek_read.py read --chat-session-id <id>
   # formats: --format json (default) | messages | md
   # or:      python scripts/deepseek_read.py read --chat-session-id <id> --format md -o chat.md
   ```
5. Read a public share (no token needed, no auth header is sent):
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

- The token comes from the `DEEPSEEK_WEB_TOKEN` environment variable,
  which always wins when set. Only when it is unset and you explicitly
  pass `--from-firefox` is the token extracted from your own Firefox
  profile. There is no `--token` flag and no token file option.
- Firefox extraction (explicit opt-in only) opens the localStorage DB
  read-only/immutable and
  keeps the token in memory only; it is never copied, printed, logged,
  or written to disk. `.gitignore` blocks
  `.env`, `*.token`, `token.txt`, `cookies*.json`, and similar.
- Missing token (no env var and no `--from-firefox`): the script exits 2
  with an error naming the variable only.

## Safety

- Treat the token as a credential: do not log it, do not include it in URLs
  that get logged, do not paste it into issues/PRs.
- If the unofficial API changes shape or returns 401/403, stop and report —
  do not retry with write methods or scrape with automated login.
- Unofficial API: not affiliated with or endorsed by DeepSeek; may break
  without notice. Respect DeepSeek's Terms of Service.
