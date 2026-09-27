"""Offline checks for the scripts that updated-workflow.md §12 tells you to run.

No network. These pin the arithmetic that §4.1 quotes and the HTTP-status
classification that the existence checker relies on. Run with:

    python -m unittest discover -s tests -v
"""
import importlib.util
import io
import pathlib
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


kv = load("kv_cache")
existence = load("check_model_existence")
test_tools = load("test_tools")

GiB = 1024 ** 3


def run_kv(argv):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = kv.main(argv)
    return rc, out.getvalue()


class KVCacheArithmetic(unittest.TestCase):
    """Numbers quoted in updated-workflow.md §4.1."""

    def test_qwen38_full_attention_is_exactly_64kib_per_token(self):
        per_tok = kv.kv_bytes_per_token(16, 4, 256, 2.0)
        self.assertEqual(per_tok, 64 * 1024)
        self.assertEqual(per_tok * 65536, 4 * GiB)  # 4.00 GiB at 64K

    def test_llama70b_is_20gib_at_64k(self):
        self.assertEqual(kv.kv_bytes_per_token(80, 8, 128, 2.0) * 65536, 20 * GiB)

    def test_hermes36b_is_16gib_at_64k(self):
        self.assertEqual(kv.kv_bytes_per_token(64, 8, 128, 2.0) * 65536, 16 * GiB)

    def test_qwen3_coder_30b_is_6gib_at_64k(self):
        self.assertEqual(kv.kv_bytes_per_token(48, 4, 128, 2.0) * 65536, 6 * GiB)

    def test_presets_match_workflow_geometry(self):
        q = kv.PRESETS["qwen3.8-27b"]
        self.assertEqual((q["full_layers"], q["kv_heads"], q["head_dim"]), (16, 4, 256))
        self.assertEqual(q["linear_state"]["layers"], 48)
        g = kv.PRESETS["gemma4-26b-a4b"]
        self.assertEqual(g["sliding"]["layers"] + g["global"]["layers"], 30)
        self.assertEqual(g["sliding"]["window"], 1024)
        self.assertEqual(g["global"]["head_dim"], 512)

    def test_gemma_range_matches_section_4_1(self):
        g = kv.PRESETS["gemma4-26b-a4b"]
        s, gl = g["sliding"], g["global"]
        sliding = s["layers"] * s["k_and_v"] * s["kv_heads"] * s["head_dim"] * 2.0 * s["window"]
        global_unified = gl["layers"] * gl["k_and_v_unified"] * gl["kv_heads"] * gl["head_dim"] * 2.0 * 65536
        # Script's range: low = sliding halved (unified K=V on sliding too) + unified global;
        # high = separate-K+V sliding + doubled global.
        low = sliding * 0.5 + global_unified
        high = sliding + 2 * global_unified
        self.assertAlmostEqual(low / GiB, 0.7227, places=3)
        self.assertAlmostEqual(high / GiB, 1.4453, places=3)

    def test_every_preset_prints_without_error(self):
        for name in kv.PRESETS:
            with self.subTest(preset=name):
                rc, text = run_kv(["--preset", name])
                self.assertEqual(rc, 0)
                self.assertIn("GiB", text)

    def test_qwen_linear_state_uses_qkv_conv_channels(self):
        # Gated DeltaNet convolves Q, K and V: 2 * 16*128 + 48*128.
        state = kv.PRESETS["qwen3.8-27b"]["linear_state"]
        self.assertEqual(state["conv_channels"], 10240)
        recurrent, conv = kv.linear_state_bytes(state)
        self.assertEqual(recurrent, 48 * 48 * 128 * 128 * 4)
        self.assertAlmostEqual((recurrent + conv) / GiB, 0.1479, places=4)

    def test_fit_line_matches_section_4_1_table(self):
        # §4.1: UD-Q4_K_M 16.5 GB + 4.00 GiB KV + ~0.15 GiB state = 19.5 GiB, ~4.5 headroom.
        rc, text = run_kv(["--preset", "qwen3.8-27b", "--weights-gb", "16.5"])
        self.assertEqual(rc, 0)
        self.assertIn("weights 16.5 GB decimal = 15.37 GiB", text)
        self.assertIn("sum = 19.51 GiB of 24.0 GiB", text)

    def test_fit_line_flags_llama70b(self):
        rc, text = run_kv(["--preset", "llama-3.3-70b", "--weights-gb", "19.0"])
        self.assertEqual(rc, 0)
        self.assertIn("DOES NOT FIT", text)


class KVCacheFromConfig(unittest.TestCase):
    """--config on the real Qwen3.8-27B geometry must agree with the preset."""

    def test_hybrid_config_counts_only_full_attention_layers(self):
        rc, text = run_kv(["--config", str(FIXTURES / "qwen3.8-27b-config.json")])
        self.assertEqual(rc, 0)
        # Previously this counted all 64 layers and printed 16 GiB.
        self.assertIn("at 65536 tokens: 4294967296 bytes = 4.0000 GiB", text)
        self.assertIn("combined: 158859264 bytes", text)

    def test_full_attn_only_override_still_wins(self):
        rc, text = run_kv(["--config", str(FIXTURES / "qwen3.8-27b-config.json"), "--full-attn-only", "8"])
        self.assertEqual(rc, 0)
        self.assertIn("2 * 8 layers", text)

    def test_config_missing_geometry_is_a_usage_error(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{}")
        try:
            with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
                kv.main(["--config", f.name])
            self.assertEqual(cm.exception.code, 2)
        finally:
            pathlib.Path(f.name).unlink()


class ExistenceClassifier(unittest.TestCase):
    """The Hub's anonymous not-found answer is 401, not 404."""

    def test_404_is_missing(self):
        self.assertEqual(existence.classify_http_error(404, "")["status"], "missing")

    def test_anonymous_401_not_found_is_missing(self):
        r = existence.classify_http_error(401, '{"error":"Invalid username or password."}')
        self.assertEqual(r["status"], "missing")
        self.assertIn("private", r["detail"])

    def test_other_401_is_not_missing(self):
        r = existence.classify_http_error(401, '{"error":"Access to model X is restricted"}')
        self.assertEqual(r["status"], "http_error")

    def test_5xx_is_not_missing(self):
        self.assertEqual(existence.classify_http_error(503, "")["status"], "http_error")

    def test_transport_error_is_incomplete_not_missing(self):
        lines, incomplete, unexpected = existence.evaluate(
            "Qwen/Qwen3.8-27B", True, {"status": "transport_error", "detail": "URLError: EOF"}
        )
        self.assertTrue(incomplete)
        self.assertFalse(unexpected)
        self.assertTrue(lines[0].startswith("INCOMPLETE"))

    def test_known_false_id_missing_is_expected(self):
        _, incomplete, unexpected = existence.evaluate(
            "Qwen/Qwen3-Coder-32B-Instruct", False, {"status": "missing", "detail": "HTTP 401 anonymous not-found"}
        )
        self.assertFalse(incomplete)
        self.assertFalse(unexpected)

    def test_recommended_id_missing_is_unexpected(self):
        _, _, unexpected = existence.evaluate("Qwen/Qwen3.8-27B", True, {"status": "missing", "detail": "HTTP 404"})
        self.assertTrue(unexpected)

    def test_sha_move_is_unexpected(self):
        _, _, unexpected = existence.evaluate(
            "Qwen/Qwen3.8-27B", True, {"status": "exists", "sha": "deadbeef", "last_modified": None}
        )
        self.assertTrue(unexpected)

    def test_pinned_sha_match_is_fine(self):
        for model_id, sha in existence.PINNED_SHA.items():
            with self.subTest(model=model_id):
                _, incomplete, unexpected = existence.evaluate(
                    model_id, True, {"status": "exists", "sha": sha, "last_modified": None}
                )
                self.assertFalse(incomplete or unexpected)

    def test_every_recommended_model_has_a_pin(self):
        for model_id, expect_exists, _ in existence.MODELS:
            if expect_exists:
                self.assertIn(model_id, existence.PINNED_SHA)


class ToolProbeDryRun(unittest.TestCase):
    """The planner probe must not send anything unless --send is given."""

    def test_dry_run_builds_request_for_each_provider(self):
        for provider, model in (("anthropic", "claude-sonnet-5"), ("openai", "gpt-6-sol"), ("gemini", "gemini-3.8-flash")):
            with self.subTest(provider=provider):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = test_tools.main(["--provider", provider, "--model", model])
                self.assertEqual(rc, 0)
                text = out.getvalue()
                self.assertIn(model, text)
                self.assertIn("Dry run", text)
                self.assertNotIn("Bearer ", text)  # never print a key or auth header value


class ToolCallDetection(unittest.TestCase):
    """Parse the provider's response shape; do not substring-match the body."""

    def test_anthropic_tool_use(self):
        body = {"content": [{"type": "tool_use", "name": "add", "input": {"a": 2, "b": 3}}], "stop_reason": "tool_use"}
        self.assertEqual(test_tools.find_tool_call("anthropic", body), (True, True))

    def test_anthropic_prose_mentioning_tool_is_not_a_call(self):
        # The old substring check passed this: it contains "add" and "tool_use".
        body = {"content": [{"type": "text", "text": "I would add 2 and 3 via tool_use."}], "stop_reason": "end_turn"}
        self.assertEqual(test_tools.find_tool_call("anthropic", body), (False, False))

    def test_openai_tool_calls_with_string_arguments(self):
        body = {"choices": [{"message": {"tool_calls": [
            {"type": "function", "function": {"name": "add", "arguments": "{\"a\": 2, \"b\": 3}"}}]}}]}
        self.assertEqual(test_tools.find_tool_call("openai", body), (True, True))

    def test_openai_wrong_arguments(self):
        body = {"choices": [{"message": {"tool_calls": [
            {"type": "function", "function": {"name": "add", "arguments": "{\"a\": 5, \"b\": 3}"}}]}}]}
        self.assertEqual(test_tools.find_tool_call("openai", body), (True, False))

    def test_openai_null_tool_calls(self):
        body = {"choices": [{"message": {"content": "5", "tool_calls": None}}]}
        self.assertEqual(test_tools.find_tool_call("openai", body), (False, False))

    def test_gemini_function_call(self):
        body = {"candidates": [{"content": {"parts": [{"functionCall": {"name": "add", "args": {"a": 2, "b": 3}}}]}}]}
        self.assertEqual(test_tools.find_tool_call("gemini", body), (True, True))

    def test_other_tool_name_is_not_add(self):
        body = {"content": [{"type": "tool_use", "name": "address_lookup", "input": {}}]}
        self.assertEqual(test_tools.find_tool_call("anthropic", body), (False, False))

    def test_send_without_key_does_not_send(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}), \
                mock.patch.object(test_tools.urllib.request, "urlopen") as urlopen, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = test_tools.main(["--provider", "openai", "--model", "gpt-6-sol", "--send"])
        self.assertEqual(rc, 2)
        urlopen.assert_not_called()

    def test_auth_error_is_incomplete_not_a_tools_verdict(self):
        import os
        import urllib.error
        from unittest import mock
        err = urllib.error.HTTPError("https://x", 401, "Unauthorized", {}, io.BytesIO(b'{"error":"invalid key, tool"}'))
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}), \
                mock.patch.object(test_tools.urllib.request, "urlopen", side_effect=err), \
                redirect_stdout(io.StringIO()) as out:
            rc = test_tools.main(["--provider", "openai", "--model", "gpt-6-sol", "--send"])
        self.assertEqual(rc, 2)
        self.assertNotIn("Route rejected tools", out.getvalue())
        self.assertNotIn("sk-test", out.getvalue())


if __name__ == "__main__":
    unittest.main()
