#!/usr/bin/env python3
"""Read-only GET client for the unofficial DeepSeek chat web API.

Stdlib only. Only GET requests are made; nothing is ever sent or mutated.

Endpoints used:
  - GET /api/v0/chat_session/fetch_page?count=N        (list sessions)
  - GET /api/v0/chat/history_messages?chat_session_id= (read one session)
  - GET /api/v0/share/content?share_id=                (public share, no auth)

Auth:
  The session token is read ONLY from the DEEPSEEK_WEB_TOKEN environment
  variable. It is sent as `Authorization: Bearer <token>` on authenticated
  calls, never printed, logged, or written to disk. The public-share call
  sends no Authorization header at all.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://chat.deepseek.com"
TOKEN_ENV_VAR = "DEEPSEEK_WEB_TOKEN"
USER_AGENT = "deepseek-chat-read/1.0 (read-only GET client)"


def _get_token() -> str:
    token = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if not token:
        print(
            f"error: {TOKEN_ENV_VAR} environment variable is not set",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return token


def _get_json(url: str, token: str | None) -> object:
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # Never include request headers (which carry the token) in output.
        print(f"error: HTTP {exc.code} from {url.split('?')[0]}", file=sys.stderr)
        raise SystemExit(1) from None
    except urllib.error.URLError as exc:
        print(f"error: request failed: {exc.reason}", file=sys.stderr)
        raise SystemExit(1) from None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print("error: response was not valid JSON", file=sys.stderr)
        raise SystemExit(1) from None


def _data(payload: object) -> object:
    """Return the `data` member of a DeepSeek envelope, else the payload."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _sessions(payload: object) -> list:
    data = _data(payload)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("chat_sessions", "sessions", "items", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def _messages(payload: object) -> list:
    data = _data(payload)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("chat_messages", "messages", "items", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        # Live share payloads nest under data.biz_data.messages, and
        # history payloads may nest under data.chat_session; search one
        # level of dict values before giving up.
        for value in data.values():
            if isinstance(value, dict):
                nested = _messages(value)
                if nested:
                    return nested
    return []


def _message_role_and_content(message: object) -> tuple[str, str]:
    if not isinstance(message, dict):
        return "unknown", str(message)
    role = (
        message.get("role")
        or message.get("type")
        or message.get("sender")
        or "unknown"
    )
    content = message.get("content", message.get("text", ""))
    if not content:
        # Live payloads carry text in fragments (REQUEST/RESPONSE/...).
        # THINK fragments are internal reasoning; skip them in transcripts.
        fragments = message.get("fragments")
        if isinstance(fragments, list):
            parts: list[str] = []
            for fragment in fragments:
                if not isinstance(fragment, dict) or fragment.get("type") == "THINK":
                    continue
                text = fragment.get("content")
                if isinstance(text, str):
                    parts.append(text)
            content = "\n\n".join(parts)
    if isinstance(content, dict):
        content = content.get("content") or content.get("text") or json.dumps(content, ensure_ascii=False)
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    return str(role), content


def render_messages(messages: list, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(messages, ensure_ascii=False, indent=2) + "\n"
    lines: list[str] = []
    for message in messages:
        role, content = _message_role_and_content(message)
        if fmt == "md":
            title = role.capitalize() if role else "Message"
            lines.append(f"## {title}\n\n{content}\n")
        else:  # messages: plain-text transcript
            lines.append(f"[{role}]\n{content}\n")
    return "\n".join(lines)


def _emit(text: str, output: str | None) -> None:
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)


def _base_url(args: argparse.Namespace) -> str:
    return (args.base_url or DEFAULT_BASE_URL).rstrip("/")


def cmd_list(args: argparse.Namespace) -> int:
    token = _get_token()
    query = urllib.parse.urlencode({"count": args.count})
    url = f"{_base_url(args)}/api/v0/chat_session/fetch_page?{query}"
    payload = _get_json(url, token)
    if args.format == "md":
        sessions = _sessions(payload)
        lines = ["# DeepSeek chat sessions\n"]
        for session in sessions:
            if isinstance(session, dict):
                title = session.get("title") or session.get("name") or "(untitled)"
                session_id = session.get("id") or session.get("chat_session_id") or ""
                lines.append(f"- {title} — `{session_id}`")
            else:
                lines.append(f"- {session}")
        text = "\n".join(lines) + "\n"
    elif args.format == "messages":
        sessions = _sessions(payload)
        text = "".join(
            f"{json.dumps(s, ensure_ascii=False)}\n" for s in sessions
        ) or json.dumps(_data(payload), ensure_ascii=False, indent=2) + "\n"
    else:  # json
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _emit(text, args.output)
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    token = _get_token()
    query = urllib.parse.urlencode({"chat_session_id": args.chat_session_id})
    url = f"{_base_url(args)}/api/v0/chat/history_messages?{query}"
    payload = _get_json(url, token)
    if args.format == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = render_messages(_messages(payload), args.format)
    _emit(text, args.output)
    return 0


def cmd_share(args: argparse.Namespace) -> int:
    # Public shares require no authentication: send no token at all.
    query = urllib.parse.urlencode({"share_id": args.share_id})
    url = f"{_base_url(args)}/api/v0/share/content?{query}"
    payload = _get_json(url, None)
    if args.format == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = render_messages(_messages(payload), args.format)
    _emit(text, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deepseek_read.py",
        description=(
            "Read-only GET client for DeepSeek chat sessions "
            "(unofficial API). Never sends or mutates anything."
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        help="API base URL (default: %(default)s)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument(
            "--format",
            choices=("json", "messages", "md"),
            default="json",
            help="output format (default: json)",
        )
        sub.add_argument(
            "-o", "--output",
            default=None,
            help="write output to this file instead of stdout",
        )

    p_list = subparsers.add_parser(
        "list", help="list chat sessions (GET /api/v0/chat_session/fetch_page)"
    )
    p_list.add_argument(
        "--count", type=int, default=20, help="number of sessions (default: 20)"
    )
    add_common(p_list)
    p_list.set_defaults(func=cmd_list)

    p_read = subparsers.add_parser(
        "read", help="read one session (GET /api/v0/chat/history_messages)"
    )
    p_read.add_argument(
        "--chat-session-id",
        "--session-id",
        dest="chat_session_id",
        required=True,
        help="id of the chat session to read",
    )
    add_common(p_read)
    p_read.set_defaults(func=cmd_read)

    p_share = subparsers.add_parser(
        "share", help="read a public share (GET /api/v0/share/content, no auth)"
    )
    p_share.add_argument(
        "--share-id", required=True, help="public share id"
    )
    add_common(p_share)
    p_share.set_defaults(func=cmd_share)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
