"""Offline checks for the scripts that updated-workflow.md §12 tells you to run.

No network. These pin the arithmetic that §4.1 quotes and the HTTP-status
classification that the existence checker relies on. Run with:

    python -m unittest discover -s tests -v
"""
import importlib.util
import io
import pathlib
import sys
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


kv = load("kv_cache")
existence = load("check_model_existence")
test_tools = load("test_tools")

GiB = 1024 ** 3


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
                out = io.StringIO()
                argv = sys.argv
                try:
                    sys.argv = ["kv_cache.py", "--preset", name]
                    with redirect_stdout(out):
                        rc = kv.main()
                finally:
                    sys.argv = argv
                self.assertIn(rc, (0, None))
                self.assertIn("GiB", out.getvalue())


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


if __name__ == "__main__":
    unittest.main()
