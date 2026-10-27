from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from config import DEFAULT_SCHEDULE, load_config
from scheduler import (choose_mode, cycle_week, latest_occurrence, prepare_mode,
                       read_scoped, record_start, write_json)

UTC = timezone.utc
SCOPE = {"repository": "owner/bot", "chat_id": "-123"}


def at(value):
    return datetime.fromisoformat(value).astimezone(UTC)


def config(**schedule):
    return {"SCHEDULE": {**DEFAULT_SCHEDULE, **schedule}}


class SchedulerTests(unittest.TestCase):
    def test_waits_until_local_time_and_handles_late_runs(self):
        # Sunday 11:07 in Italy is 10:07 UTC in winter.
        c = config()
        self.assertEqual(choose_mode(c, None, None, at("2026-11-01T10:06:00Z")), "")
        self.assertEqual(choose_mode(c, None, None, at("2026-11-01T10:07:00Z")), "start")
        self.assertEqual(choose_mode(c, None, None, at("2026-11-01T12:30:00Z")), "start")
        self.assertEqual(choose_mode(c, None, None, at("2026-11-02T08:07:00Z")), "")

    def test_does_not_repeat_a_completed_week_after_settings_change(self):
        now = at("2026-11-01T12:30:00Z")
        week = cycle_week(latest_occurrence(DEFAULT_SCHEDULE, now), DEFAULT_SCHEDULE)
        state = {"last_cycle_week": week}
        self.assertEqual(choose_mode(config(), None, state, now), "")
        self.assertEqual(choose_mode(config(time="13:00"), None, state, now), "")
        self.assertEqual(choose_mode(config(), None, state, now + timedelta(days=7)), "start")

    def test_active_deadlines_are_absolute_and_take_priority(self):
        active = {"poll_type": "first", "close_at": "2026-11-02T08:15:00Z"}
        self.assertEqual(choose_mode(config(first_poll_hours=1), active, None, at("2026-11-02T08:14:00Z")), "")
        self.assertEqual(choose_mode(config(first_poll_hours=1), active, None, at("2026-11-02T08:15:00Z")), "close_first")
        active["poll_type"] = "tiebreak"
        self.assertEqual(choose_mode(config(), active, None, at("2026-11-02T09:00:00Z")), "close_tiebreak")
        self.assertEqual(choose_mode(config(), active, None, at("2026-11-08T10:07:00Z")), "close_tiebreak")

    def test_manual_dispatch_keeps_duplicate_and_phase_guards(self):
        now = at("2026-11-03T12:00:00Z")
        self.assertEqual(choose_mode(config(), None, None, now, "start"), "start")
        self.assertEqual(choose_mode(config(), {"poll_type": "first"}, None, now, "start"), "")
        self.assertEqual(choose_mode(config(), {"poll_type": "first"}, None, now, "close_tiebreak"), "")
        self.assertEqual(choose_mode(config(), {"poll_type": "first"}, None, now, "close_first"), "close_first")
        self.assertEqual(choose_mode(config(), None, None, now, "close_first"), "")

    def test_italian_daylight_saving_time(self):
        c = config()
        self.assertEqual(latest_occurrence(c["SCHEDULE"], at("2026-07-05T09:07:00Z")), at("2026-07-05T09:07:00Z"))
        self.assertEqual(latest_occurrence(c["SCHEDULE"], at("2026-11-01T10:07:00Z")), at("2026-11-01T10:07:00Z"))
        c = config(time="02:30")
        # Spring: 02:30 does not exist, so shift past the gap to 03:30.
        self.assertEqual(latest_occurrence(c["SCHEDULE"], at("2026-03-29T01:30:00Z")), at("2026-03-29T01:30:00Z"))
        # Autumn: use the first 02:30; the second must not start another cycle.
        self.assertEqual(latest_occurrence(c["SCHEDULE"], at("2026-10-25T01:30:00Z")), at("2026-10-25T00:30:00Z"))

    def test_progress_survives_active_file_deletion_and_another_checkout(self):
        now = at("2026-11-01T10:07:00Z")
        with tempfile.TemporaryDirectory() as folder:
            active = Path(folder) / "poll.json"
            state = Path(folder) / "schedule.json"
            record_start(config(), SCOPE, now, state)
            self.assertEqual(prepare_mode(config(), SCOPE, now + timedelta(hours=1), poll_file=active, state_file=state), "")
            self.assertEqual(prepare_mode(config(), SCOPE, now + timedelta(days=7), poll_file=active, state_file=state), "start")
            self.assertIsNone(read_scoped(state, {**SCOPE, "repository": "fork/bot"}))
            self.assertIsNone(read_scoped(state, {**SCOPE, "chat_id": "-999"}))

    def test_legacy_active_poll_is_adopted_once_instead_of_replaced(self):
        now = at("2026-11-01T10:07:00Z")
        with tempfile.TemporaryDirectory() as folder:
            active = Path(folder) / "poll.json"
            state = Path(folder) / "schedule.json"
            write_json(active, {"message_id": 42, "poll_type": "first"})
            self.assertEqual(prepare_mode(config(), SCOPE, now, poll_file=active, state_file=state), "")
            saved = json.loads(active.read_text())
            self.assertEqual(saved["close_at"], (now + timedelta(hours=22)).isoformat())
            self.assertEqual(saved["scope"], SCOPE)
            self.assertEqual(prepare_mode(config(), SCOPE, now + timedelta(hours=22), poll_file=active, state_file=state), "close_first")
            self.assertEqual(json.loads(active.read_text())["close_at"], saved["close_at"])

    def test_invalid_schedule_is_rejected_and_legacy_config_gets_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            value = load_config()
            del value["SCHEDULE"]
            path.write_text(json.dumps(value))
            self.assertEqual(load_config(path)["SCHEDULE"], DEFAULT_SCHEDULE)
            for patch in ({"weekday": 7}, {"weekday": True}, {"time": "24:00"},
                          {"time": "8:00"}, {"first_poll_hours": 0}, {"first_poll_hours": 1.5},
                          {"first_poll_hours": 160, "tiebreak_hours": 8}, {"timezone": "UTC"}):
                with self.subTest(patch=patch):
                    path.write_text(json.dumps({**value, "SCHEDULE": {**DEFAULT_SCHEDULE, **patch}}))
                    with self.assertRaises(ValueError):
                        load_config(path)
