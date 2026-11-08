"""Offline tests for scripts/deepseek_read.py — no network, stdlib only.

Run:  python3 -m unittest discover -s tests -v
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from email.message import Message
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "deepseek-chat-read" / "scripts" / "deepseek_read.py"
FIXTURES = ROOT / "tests" / "fixtures"

spec = importlib.util.spec_from_file_location("deepseek_read", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["deepseek_read"] = mod
spec.loader.exec_module(mod)


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestEnvelopeParsing(unittest.TestCase):
    def test_data_unwraps_envelope(self):
        payload = load_fixture("share_envelope.json")
        self.assertIs(mod._data(payload), payload["data"])

    def test_data_passthrough_without_envelope(self):
        payload = load_fixture("odd_shapes.json")["no_envelope"]
        self.assertIs(mod._data(payload), payload)

    def test_sessions_from_chat_sessions_key(self):
        sessions = mod._sessions(load_fixture("sessions_envelope.json"))
        self.assertEqual([s.get("title") or s.get("name") for s in sessions],
                         ["Alpha", "Beta"])

    def test_sessions_bare_list(self):
        self.assertEqual(mod._sessions([{"id": "x"}]), [{"id": "x"}])

    def test_sessions_unknown_shape_returns_empty(self):
        self.assertEqual(mod._sessions(load_fixture("odd_shapes.json")["empty"]), [])

    def test_messages_from_chat_messages_key(self):
        msgs = mod._messages(load_fixture("share_envelope.json"))
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["content"], "Hello from fixture")

    def test_messages_from_bare_list_in_data(self):
        msgs = mod._messages(load_fixture("history_envelope.json"))
        self.assertEqual(len(msgs), 2)

    def test_messages_nested_chat_session(self):
        payload = load_fixture("odd_shapes.json")["nested"]
        msgs = mod._messages(payload)
        self.assertEqual(len(msgs), 3)

    def test_messages_unknown_shape_returns_empty(self):
        self.assertEqual(mod._messages(load_fixture("odd_shapes.json")["empty"]), [])

    def test_messages_under_biz_data(self):
        # Live share shape: data.biz_data.messages
        msgs = mod._messages(load_fixture("share_biz_data.json"))
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "USER")


class TestRoleAndContent(unittest.TestCase):
    def test_role_fallback_chain(self):
        self.assertEqual(mod._message_role_and_content({"type": "assistant", "text": "hi"}),
                         ("assistant", "hi"))
        self.assertEqual(mod._message_role_and_content({"sender": "user", "content": "yo"}),
                         ("user", "yo"))
        self.assertEqual(mod._message_role_and_content({"content": "x"}), ("unknown", "x"))

    def test_content_dict_unwrapped(self):
        role, content = mod._message_role_and_content(
            {"sender": "user", "content": {"content": "Nested hello"}})
        self.assertEqual((role, content), ("user", "Nested hello"))

    def test_non_string_content_json_encoded(self):
        _, content = mod._message_role_and_content({"role": "assistant", "content": 42})
        self.assertEqual(content, "42")

    def test_non_dict_message(self):
        role, content = mod._message_role_and_content("plain string message")
        self.assertEqual((role, content), ("unknown", "plain string message"))

    def test_fragments_joined_and_think_skipped(self):
        msgs = mod._messages(load_fixture("share_biz_data.json"))
        role, content = mod._message_role_and_content(msgs[1])
        self.assertEqual(role, "ASSISTANT")
        self.assertIn("Here is my review.", content)
        self.assertNotIn("internal reasoning", content)

    def test_fragments_file_only_gives_empty_content(self):
        _, content = mod._message_role_and_content(
            {"role": "USER", "fragments": [{"type": "FILE", "files": []}]})
        self.assertEqual(content, "")


class TestRender(unittest.TestCase):
    def setUp(self):
        self.msgs = mod._messages(load_fixture("share_envelope.json"))

    def test_render_json_round_trips(self):
        out = mod.render_messages(self.msgs, "json")
        self.assertEqual(json.loads(out), self.msgs)

    def test_render_messages_plain(self):
        out = mod.render_messages(self.msgs, "messages")
        self.assertIn("[user]\nHello from fixture", out)
        self.assertIn("[assistant]\nHi there", out)

    def test_render_md_headings(self):
        out = mod.render_messages(self.msgs, "md")
        self.assertIn("## User\n\nHello from fixture", out)
        self.assertIn("## Assistant\n\nHi there", out)

    def test_render_md_with_odd_shapes(self):
        msgs = mod._messages(load_fixture("odd_shapes.json")["nested"])
        out = mod.render_messages(msgs, "md")
        self.assertIn("Nested hello", out)
        self.assertIn("plain string message", out)

    def test_render_md_live_share_shape(self):
        msgs = mod._messages(load_fixture("share_biz_data.json"))
        out = mod.render_messages(msgs, "md")
        self.assertIn("## User\n\nPlease review this code.", out)
        self.assertIn("## Assistant\n\nHere is my review.", out)
        self.assertNotIn("internal reasoning", out)


class TestCommandsOffline(unittest.TestCase):
    """Commands with _get_json mocked out; asserts URL + auth wiring."""

    def _run(self, argv, payload, env_token=None):
        args = mod.build_parser().parse_args(argv)
        captured = {}

        def fake_get_json(url, token):
            captured["url"] = url
            captured["token"] = token
            return payload

        env = {} if env_token is None else {"DEEPSEEK_WEB_TOKEN": env_token}
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(mod, "_get_json", side_effect=fake_get_json):
            if env_token is None:
                os.environ.pop("DEEPSEEK_WEB_TOKEN", None)
            out = io.StringIO()
            with redirect_stdout(out):
                rc = args.func(args)
        return rc, out.getvalue(), captured

    def test_share_sends_no_token_and_needs_no_env(self):
        payload = load_fixture("share_envelope.json")
        rc, out, cap = self._run(["share", "--share-id", "abc123", "--format", "md"],
                                 payload, env_token=None)
        self.assertEqual(rc, 0)
        self.assertIsNone(cap["token"])
        self.assertIn("/api/v0/share/content?share_id=abc123", cap["url"])
        self.assertIn("## User", out)

    def test_list_sends_token_and_builds_md(self):
        payload = load_fixture("sessions_envelope.json")
        rc, out, cap = self._run(["list", "--count", "1", "--format", "md"],
                                 payload, env_token="dummy-token-for-test")
        self.assertEqual(rc, 0)
        self.assertEqual(cap["token"], "dummy-token-for-test")
        self.assertIn("count=1", cap["url"])
        self.assertIn("- Alpha — `sess-1`", out)
        self.assertIn("- Beta — `sess-2`", out)

    def test_read_messages_format(self):
        payload = load_fixture("history_envelope.json")
        rc, out, cap = self._run(
            ["read", "--chat-session-id", "s1", "--format", "messages"],
            payload, env_token="dummy-token-for-test")
        self.assertEqual(rc, 0)
        self.assertIn("chat_session_id=s1", cap["url"])
        self.assertIn("[assistant]\nFirst answer", out)

    def test_list_without_token_exits_2_without_leaking(self):
        args = mod.build_parser().parse_args(["list"])
        err = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                args.func(args)
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("DEEPSEEK_WEB_TOKEN", err.getvalue())

    def test_output_written_to_file(self):
        payload = load_fixture("share_envelope.json")
        with tempfile.TemporaryDirectory() as td:
            target = os.path.join(td, "out.md")
            rc, _, _ = self._run(
                ["share", "--share-id", "abc", "--format", "md", "-o", target],
                payload, env_token=None)
            self.assertEqual(rc, 0)
            self.assertIn("Hello from fixture",
                          Path(target).read_text(encoding="utf-8"))


class TestGetJsonErrors(unittest.TestCase):
    def test_http_error_exits_1_and_hides_token(self):
        req_url = "https://chat.deepseek.com/api/v0/chat_session/fetch_page?count=1"
        err = urllib.error.HTTPError(req_url, 401, "Unauthorized", Message(), None)
        with mock.patch.object(mod.urllib.request, "urlopen", side_effect=err):
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as ctx:
                    mod._get_json(req_url, "super-secret-token")
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("HTTP 401", stderr.getvalue())
        self.assertNotIn("super-secret-token", stderr.getvalue())

    def test_get_json_sends_bearer_only_when_token_given(self):
        seen = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"ok": true}'

        def fake_urlopen(request, timeout=None):
            seen["auth"] = request.get_header("Authorization")
            seen["method"] = request.get_method()
            return FakeResponse()

        with mock.patch.object(mod.urllib.request, "urlopen", side_effect=fake_urlopen):
            self.assertEqual(mod._get_json("https://example.invalid/x", "tok123"),
                             {"ok": True})
        self.assertEqual(seen["auth"], "Bearer tok123")
        self.assertEqual(seen["method"], "GET")

        with mock.patch.object(mod.urllib.request, "urlopen", side_effect=fake_urlopen):
            mod._get_json("https://example.invalid/x", None)
        self.assertIsNone(seen["auth"])


class TestFirefoxTokenExtraction(unittest.TestCase):
    def _make_profile(self, root, stored):
        import sqlite3
        ls_dir = Path(root) / "storage" / "default" / "https+++chat.deepseek.com" / "ls"
        ls_dir.mkdir(parents=True)
        db = ls_dir / "data.sqlite"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE data (key TEXT, value BLOB)")
        dummy = "dummy-" + "token-for-test"
        wrapper = json.dumps({"value": dummy, "__version": "0"})
        con.execute("INSERT INTO data VALUES (?, ?)", ("userToken", stored or wrapper))
        con.commit()
        con.close()
        return dummy

    def test_parse_stored_token_unwraps_json(self):
        dummy = "dummy-" + "token-for-test"
        raw = json.dumps({"value": dummy, "__version": "0"})
        self.assertEqual(mod._parse_stored_token(raw), dummy)
        self.assertEqual(mod._parse_stored_token(raw.encode()), dummy)
        self.assertEqual(mod._parse_stored_token("  plain  "), "plain")

    def test_extract_from_modern_ls_db(self):
        with tempfile.TemporaryDirectory() as td:
            dummy = self._make_profile(td, None)
            self.assertEqual(mod.extract_user_token_from_firefox(td), dummy)

    def test_missing_profile_exits_2_without_value(self):
        with tempfile.TemporaryDirectory() as td:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as ctx:
                    mod.extract_user_token_from_firefox(td)
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("DEEPSEEK_WEB_TOKEN", stderr.getvalue())


class TestTokenPrecedence(unittest.TestCase):
    """DEEPSEEK_WEB_TOKEN always wins; Firefox is explicit opt-in only."""

    def test_env_wins_over_firefox_when_both_present(self):
        # Fake Firefox DB present + env set + --from-firefox passed:
        # env must win and Firefox extraction must not even run.
        import sqlite3
        with tempfile.TemporaryDirectory() as td:
            ls_dir = Path(td) / "storage" / "default" / \
                "https+++chat.deepseek.com" / "ls"
            ls_dir.mkdir(parents=True)
            con = sqlite3.connect(ls_dir / "data.sqlite")
            con.execute("CREATE TABLE data (key TEXT, value BLOB)")
            con.execute("INSERT INTO data VALUES (?, ?)", (
                "userToken", json.dumps(
                    {"value": "firefox-token-for-test", "__version": "0"})))
            con.commit()
            con.close()
            args = mod.build_parser().parse_args(
                ["list", "--from-firefox", "--firefox-profile", td])
            with mock.patch.dict(
                    os.environ, {"DEEPSEEK_WEB_TOKEN": "env-token-for-test"},
                    clear=False), \
                 mock.patch.object(
                    mod, "extract_user_token_from_firefox",
                    side_effect=AssertionError("firefox must not run")) as ff:
                self.assertEqual(mod._get_token(args), "env-token-for-test")
                ff.assert_not_called()

    def test_env_wins_without_flag(self):
        args = mod.build_parser().parse_args(["list"])
        with mock.patch.dict(
                os.environ, {"DEEPSEEK_WEB_TOKEN": "env-token-for-test"},
                clear=False):
            self.assertEqual(mod._get_token(args), "env-token-for-test")

    def test_firefox_only_when_no_env_and_flag_passed(self):
        args = mod.build_parser().parse_args(["list", "--from-firefox"])
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(mod, "extract_user_token_from_firefox",
                               return_value="firefox-token-for-test") as ff:
            self.assertEqual(mod._get_token(args), "firefox-token-for-test")
            ff.assert_called_once()

    def test_no_env_no_flag_exits_2(self):
        args = mod.build_parser().parse_args(["list"])
        err = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), \
             redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                mod._get_token(args)
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("DEEPSEEK_WEB_TOKEN", err.getvalue())

    def test_help_names_env_first(self):
        help_text = mod.build_parser().format_help()
        self.assertLess(help_text.index("DEEPSEEK_WEB_TOKEN always wins"),
                        help_text.index("opt-in"))


if __name__ == "__main__":
    unittest.main()
