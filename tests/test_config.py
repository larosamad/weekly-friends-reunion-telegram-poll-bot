import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

from config import load_config

ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_existing_defaults_are_preserved(self):
        config = load_config()
        self.assertEqual(len(config["OPTIONS"]), 10)
        self.assertEqual(config["MIN_TIEBREAK_VOTES"], 3)
        self.assertEqual(config["GROUP_NAME"], "Ciccini")
        self.assertEqual(config["FIRST_POLL_QUESTION"], "Che giorno preferite?")

    def test_validation_matches_app_constraints(self):
        for change in ({"OPTIONS": ["One"]}, {"OPTIONS": ["One", " One "]},
                       {"OPTIONS": ["One", " "]}, {"OPTIONS": ["a" * 101, "b"]},
                       {"EXCLUDED_OPTION": "missing"}, {"MIN_TIEBREAK_VOTES": True},
                       {"MIN_TIEBREAK_VOTES": 0}, {"MIN_TIEBREAK_VOTES": 1.5},
                       {"FIRST_POLL_QUESTION": " "}, {"GROUP_NAME": "a" * 101},
                       {"TIEBREAK_QUESTION": "a" * 301}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "config.json"
                path.write_text(json.dumps({**load_config(), **change}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_saved_unicode_settings_are_read_again(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            config = load_config()
            path.write_text(json.dumps(config), encoding="utf-8")
            self.assertEqual(load_config(path)["GROUP_NAME"], "Ciccini")
            config["GROUP_NAME"] = "Amici 🍿"
            path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(load_config(path)["GROUP_NAME"], "Amici 🍿")


class BotIntegrationTests(unittest.TestCase):
    def setUp(self):
        config = load_config()
        config.update(GROUP_NAME="Amici", FIRST_POLL_QUESTION="Quando usciamo?",
                      TIEBREAK_QUESTION="Quale scegliamo?", MIN_TIEBREAK_VOTES=5,
                      OPTIONS=["Non posso", "Venerdì", "Sabato"])
        self.config = config
        telegram = types.ModuleType("telegram")
        telegram.Bot = Mock()
        telegram.InputPollOption = lambda text: types.SimpleNamespace(text=text)
        spec = importlib.util.spec_from_file_location("tested_bot", ROOT / "bot.py")
        self.bot = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"telegram": telegram}), patch.dict(os.environ, {
            "BOT_TOKEN": "test-only", "CHAT_ID": "-123", "MODE": "start",
        }), patch("config.load_config", return_value=config):
            spec.loader.exec_module(self.bot)

    def test_custom_options_and_question_reach_telegram(self):
        client = types.SimpleNamespace(send_poll=AsyncMock(return_value=types.SimpleNamespace(message_id=42)))
        self.bot.Bot.return_value = client
        with tempfile.TemporaryDirectory() as folder:
            self.bot.POLL_FILE = str(Path(folder) / "poll_info.json")
            asyncio.run(self.bot.main())
            sent = client.send_poll.call_args.kwargs
            self.assertEqual(sent["question"], "Quando usciamo?")
            self.assertEqual([o.text for o in sent["options"]], self.config["OPTIONS"])
            self.assertTrue(sent["allows_multiple_answers"])
            self.assertEqual(json.loads(Path(self.bot.POLL_FILE).read_text())["message_id"], 42)

    def test_group_name_reaches_winner_message(self):
        client = types.SimpleNamespace(send_message=AsyncMock())
        asyncio.run(self.bot.send_winner_message(client, "Venerdì"))
        self.assertTrue(client.send_message.call_args.kwargs["text"].startswith("Amici del Venerdì"))

    def test_threshold_and_tiebreak_question(self):
        self.bot.MODE = "close_first"
        self.bot.create_poll = AsyncMock()
        self.bot.delete_poll_info = AsyncMock()
        for votes, expected in ((4, False), (5, True)):
            with self.subTest(votes=votes):
                self.bot.create_poll.reset_mock()
                self.bot.close_poll = AsyncMock(return_value=[
                    types.SimpleNamespace(text="Venerdì", voter_count=votes),
                    types.SimpleNamespace(text="Sabato", voter_count=votes),
                ])
                asyncio.run(self.bot.main())
                self.assertEqual(self.bot.create_poll.called, expected)
                if expected:
                    self.assertEqual(self.bot.create_poll.call_args.args[2], "Quale scegliamo?")

    def test_excluded_option_does_not_win(self):
        client = types.SimpleNamespace(stop_poll=AsyncMock(return_value=types.SimpleNamespace(options=[
            types.SimpleNamespace(text="Non posso", voter_count=10),
            types.SimpleNamespace(text="Venerdì", voter_count=2),
        ])))
        with tempfile.TemporaryDirectory() as folder:
            self.bot.POLL_FILE = str(Path(folder) / "poll_info.json")
            Path(self.bot.POLL_FILE).write_text('{"message_id": 1, "poll_type": "first"}')
            winners = asyncio.run(self.bot.close_poll(client))
            self.assertEqual([o.text for o in winners], ["Venerdì"])


if __name__ == "__main__":
    unittest.main()
