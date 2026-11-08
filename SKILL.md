---
name: deepseek-chat-read
description: Read-only GET /api/v0 session reader for DeepSeek chat via unofficial API. Use when fetching conversation/message lists from a logged-in DeepSeek session without performing any write operation.
---

# deepseek-chat-read

Read-only reader for DeepSeek chat sessions over the unofficial `GET /api/v0` API.

## Scope

- READ-ONLY. Only `GET` requests. Never POST, PUT, DELETE, or otherwise mutate chat state.
- Session-scoped: operate only on the authenticated user's own sessions.
- No sending messages, no generating, no editing, no deleting.

## Prerequisites

- A valid session token / cookie for `chat.deepseek.com` (never committed to git — see README).
- Network access to `https://chat.deepseek.com`.

## Usage

```bash
# Placeholder — real call proven by the reader script / test run.
# Example (to be wired to scripts/reader.py):
#   python scripts/reader.py --token "$DEEPSEEK_TOKEN" --list-sessions
```

Token handling:

- Pass via environment variable (`DEEPSEEK_TOKEN`) or a local untracked file.
- Never hardcode, echo, or commit the token. `.gitignore` blocks `.env` and token files.

## Safety

- Treat the token as a credential: do not log it, do not include it in URLs that get logged, do not paste it into issues/PRs.
- If the unofficial API changes shape or returns 401/403, stop and report — do not retry with write methods or scrape with automated login.

## Status

Skeleton. The read-only GET call is implemented and proven separately (see run goal / handoff); this file defines the skill contract.
