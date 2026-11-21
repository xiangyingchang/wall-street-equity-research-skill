from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_model_task.py"
SPEC = importlib.util.spec_from_file_location("run_model_task", SCRIPT)
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)


class ModelRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_bytes("仅提取本段表格。\n".encode())

    def args(self, profile="sol", task="extract", out=None):
        return routing.parser().parse_args([
            "--profile", profile, "--task", task, "--input", str(self.prompt),
            "--out", str(out or self.root / profile), "--codex", "/custom/codex",
        ])

    @staticmethod
    def complete(argv, **kwargs):
        Path(argv[argv.index("-o") + 1]).write_text("candidate text")
        kwargs["stdout"].write(b"execution log\n")
        return subprocess.CompletedProcess(argv, 0)

    def test_profiles_new_session_exact_stdin_and_telemetry(self):
        for profile, expected in routing.PROFILES.items():
            with self.subTest(profile=profile), patch.object(routing.shutil, "which", return_value="/custom/codex") as which, patch.object(routing.subprocess, "run", side_effect=self.complete) as execute:
                args = self.args(profile)
                self.assertEqual(routing.run(args), 0)
                which.assert_called_once_with("/custom/codex")
                argv = execute.call_args.args[0]
                options = execute.call_args.kwargs
                self.assertEqual(argv[:2], ["/custom/codex", "exec"])
                self.assertEqual(argv[argv.index("--model") + 1], expected[0])
                self.assertIn(f'model_reasoning_effort="{expected[1]}"', argv)
                self.assertIn('web_search="disabled"', argv)
                self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
                self.assertIn("--ephemeral", argv)
                self.assertIn("--ignore-user-config", argv)
                self.assertNotIn("fork", argv)
                self.assertNotIn("resume", argv)
                self.assertEqual(argv[-1], "-")
                self.assertEqual(options["input"], self.prompt.read_bytes())
                self.assertNotEqual(Path(options["cwd"]), self.prompt.parent)
                self.assertIs(options["stderr"], subprocess.STDOUT)
                metrics_path = args.out / "run-metrics.jsonl"
                metrics = json.loads(metrics_path.read_text())
                self.assertEqual(metrics["model"], expected[0])
                self.assertEqual(metrics["effort"], expected[1])
                self.assertEqual(metrics["prompt_sha256"], hashlib.sha256(self.prompt.read_bytes()).hexdigest())
                self.assertEqual(metrics["exit_code"], 0)
                self.assertGreaterEqual(metrics["elapsed_seconds"], 0)
                self.assertFalse(metrics["accepted"])
                self.assertEqual(metrics["experimental"], profile != "sol")
                self.assertNotIn("candidate text", metrics_path.read_text())
                self.assertNotIn("仅提取", metrics_path.read_text())
                self.assertIn("execution log", (args.out / "run.log").read_text())
                filename = "output.md" if profile == "sol" else "candidate.md"
                self.assertTrue((args.out / filename).is_file())

    def test_judgment_cannot_use_lower_tiers(self):
        for profile in ("terra", "luna"):
            with patch.object(routing.subprocess, "run") as execute:
                with self.assertRaisesRegex(ValueError, "judgment requires sol"):
                    routing.run(self.args(profile, "judgment"))
                execute.assert_not_called()
                self.assertFalse((self.root / profile).exists())

    def test_existing_directory_file_and_symlink_are_preserved(self):
        directory = self.root / "existing"
        directory.mkdir()
        saved = directory / "candidate.md"
        saved.write_text("keep original")
        link = self.root / "link"
        link.symlink_to(self.root / "missing")
        for target in (directory, saved, link):
            with self.subTest(target=target), patch.object(routing.shutil, "which", return_value="/custom/codex"), patch.object(routing.subprocess, "run") as execute:
                with self.assertRaises(FileExistsError):
                    routing.run(self.args(out=target))
                execute.assert_not_called()
                self.assertEqual(saved.read_text(), "keep original")

    def test_failure_and_missing_final_message_are_recorded(self):
        for result, expected in ((subprocess.CompletedProcess([], 7), 7), (OSError("cannot start"), 127), (subprocess.CompletedProcess([], 0), 1)):
            out = self.root / f"failed-{expected}"
            with patch.object(routing.shutil, "which", return_value="/custom/codex"), patch.object(routing.subprocess, "run") as execute:
                if isinstance(result, OSError):
                    execute.side_effect = result
                else:
                    execute.return_value = result
                self.assertEqual(routing.run(self.args(out=out)), expected)
                metrics = json.loads((out / "run-metrics.jsonl").read_text())
                self.assertEqual(metrics["exit_code"], expected)
                self.assertFalse(metrics["accepted"])

    def test_missing_executable_and_invalid_input_create_no_output(self):
        with patch.object(routing.shutil, "which", return_value=None), patch.object(routing.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "executable not found"):
                routing.run(self.args())
            execute.assert_not_called()
        self.prompt.write_bytes(b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            routing.run(self.args())
        self.assertFalse((self.root / "sol").exists())

    def test_usage_requires_comparison_and_semantic_gate(self):
        help_text = routing.parser().format_help()
        self.assertIn("identical prompt bytes", help_text)
        self.assertIn("semantic gate", help_text)
        self.assertIn("experimental", help_text)
        self.assertEqual(routing.parser().get_default("profile"), "sol")


if __name__ == "__main__":
    unittest.main()
