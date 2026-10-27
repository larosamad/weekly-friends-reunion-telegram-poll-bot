"""Exercise the actual workflow persistence script against a local Git remote."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def test_missing_secrets_fail_without_printing_values(self):
        workflow = (ROOT / ".github/workflows/telegram-poll.yml").read_text()
        step = workflow.split("      - name: Validate secrets\n", 1)[1].split("      - name:", 1)[0]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        for token, chat, success in (("", "-123", False), ("private-token", "  ", False), ("private-token", "-123", True)):
            result = subprocess.run(["bash", "-c", script], env={**os.environ, "BOT_TOKEN": token, "CHAT_ID": chat},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, success)
            self.assertNotIn("private-token", result.stdout + result.stderr)

    def test_persists_cycle_marker_after_closing_and_preserves_concurrent_config_edits(self):
        workflow = (ROOT / ".github/workflows/telegram-poll.yml").read_text()
        script = textwrap.dedent(workflow.split("      - name: Save poll state", 1)[1].split("        run: |\n", 1)[1])
        subprocess.run(["bash", "-n"], input=script, text=True, check=True)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            origin, seed, checkout = (folder / name for name in ("origin.git", "seed", "checkout"))
            env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "STATE_BRANCH": "custom-branch"}
            def git(cwd, *args, check=True):
                return subprocess.run(["git", *args], cwd=cwd, env=env, check=check, text=True, capture_output=True)
            git(folder, "init", "--bare", str(origin))
            git(folder, "init", "-b", "custom-branch", str(seed))
            for key, value in (("user.name", "Test"), ("user.email", "test@example.com"), ("commit.gpgsign", "false")):
                git(seed, "config", key, value)
            (seed / "bot_config.json").write_text('{"name": "original"}')
            (seed / "poll_info.json").write_text('{"message_id": 1}')
            git(seed, "add", ".")
            git(seed, "commit", "-m", "Initial")
            git(seed, "remote", "add", "origin", str(origin))
            git(seed, "push", "-u", "origin", "custom-branch")
            git(folder, "clone", "--branch", "custom-branch", str(origin), str(checkout))
            git(checkout, "config", "commit.gpgsign", "false")
            # Simulate an app save while Actions was processing a poll.
            (seed / "bot_config.json").write_text('{"name": "edited by app"}')
            git(seed, "commit", "-am", "App settings")
            git(seed, "push")
            (checkout / "schedule_state.json").write_text('{"last_cycle_week": "2026-10-26"}')
            subprocess.run(["bash", "-c", script], cwd=checkout, env=env, check=True, capture_output=True, timeout=20)
            self.assertEqual(json.loads((checkout / "bot_config.json").read_text())["name"], "edited by app")
            (checkout / "poll_info.json").unlink()
            subprocess.run(["bash", "-c", script], cwd=checkout, env=env, check=True, capture_output=True, timeout=20)
            self.assertNotEqual(git(origin, "cat-file", "-e", "custom-branch:poll_info.json", check=False).returncode, 0)
            marker = json.loads(git(origin, "show", "custom-branch:schedule_state.json").stdout)
            self.assertEqual(marker["last_cycle_week"], "2026-10-26")
