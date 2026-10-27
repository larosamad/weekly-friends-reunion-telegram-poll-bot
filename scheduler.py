"""Weekly timing and durable progress. Uses only Python's standard library."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from config import DEFAULT_SCHEDULE, load_config

POLL_FILE = Path("poll_info.json")
SCHEDULE_STATE_FILE = Path("schedule_state.json")
UTC = timezone.utc


def utc_now():
    return datetime.now(UTC)


def parse_time(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Lo stato del sondaggio deve contenere un fuso orario.")
    return result.astimezone(UTC)


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_scoped(path, scope, allow_legacy=False):
    path = Path(path)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Stato non valido: {path.name}")
    if value.get("scope") == scope or (allow_legacy and "scope" not in value):
        return value
    return None


def latest_occurrence(schedule, now):
    """Most recent local weekly appointment, compared in UTC across DST folds."""
    zone = ZoneInfo(schedule["timezone"])
    local = now.astimezone(zone)
    date = local.date() - timedelta(days=(local.weekday() - schedule["weekday"]) % 7)
    hour, minute = map(int, schedule["time"].split(":"))
    candidate = datetime(date.year, date.month, date.day, hour, minute, tzinfo=zone)
    # Round-trip shifts a nonexistent spring-forward time past the DST gap.
    candidate = candidate.astimezone(UTC).astimezone(zone)
    if candidate.astimezone(UTC) > now.astimezone(UTC):
        date -= timedelta(days=7)
        candidate = datetime(date.year, date.month, date.day, hour, minute, tzinfo=zone)
        candidate = candidate.astimezone(UTC).astimezone(zone)
    return candidate.astimezone(UTC)


def cycle_week(occurrence, schedule):
    local = occurrence.astimezone(ZoneInfo(schedule["timezone"]))
    return (local.date() - timedelta(days=local.weekday())).isoformat()


def choose_mode(config, active, progress, now, requested="auto"):
    schedule = {**DEFAULT_SCHEDULE, **config.get("SCHEDULE", {})}
    if requested not in ("auto", "start", "close_first", "close_tiebreak"):
        raise ValueError("Modalità di esecuzione sconosciuta.")
    if active:
        poll_type = active.get("poll_type")
        if poll_type not in ("first", "tiebreak"):
            raise ValueError("Tipo del sondaggio attivo non valido.")
        expected = "close_first" if poll_type == "first" else "close_tiebreak"
        if requested != "auto":
            return expected if requested == expected else ""
        deadline = active.get("close_at")
        # A legacy poll is adopted by prepare_mode before this decision.
        return expected if deadline and now.astimezone(UTC) >= parse_time(deadline) else ""
    if requested != "auto":
        return "start" if requested == "start" else ""
    occurrence = latest_occurrence(schedule, now)
    week = cycle_week(occurrence, schedule)
    if (progress or {}).get("last_cycle_week", "") >= week:
        return ""
    # Do not publish an old poll if an entire first-poll window was missed.
    if now.astimezone(UTC) >= occurrence + timedelta(hours=schedule["first_poll_hours"]):
        return ""
    return "start"


def record_start(config, scope, now, state_file=SCHEDULE_STATE_FILE):
    schedule = {**DEFAULT_SCHEDULE, **config.get("SCHEDULE", {})}
    week = cycle_week(latest_occurrence(schedule, now), schedule)
    progress = read_scoped(state_file, scope) or {}
    write_json(state_file, {"scope": scope, "last_cycle_week": max(week, progress.get("last_cycle_week", ""))})


def prepare_mode(config, scope, now, requested="auto", poll_file=POLL_FILE, state_file=SCHEDULE_STATE_FILE):
    active = read_scoped(poll_file, scope, allow_legacy=True)
    progress = read_scoped(state_file, scope)
    schedule = {**DEFAULT_SCHEDULE, **config.get("SCHEDULE", {})}
    if active:
        if active.get("poll_type") not in ("first", "tiebreak"):
            raise ValueError("Tipo del sondaggio attivo non valido.")
        if not active.get("close_at"):
            # Preserve the existing poll during upgrade instead of sending a replacement.
            hours = schedule["first_poll_hours"] if active["poll_type"] == "first" else schedule["tiebreak_hours"]
            active.update(scope=scope, close_at=(now.astimezone(UTC) + timedelta(hours=hours)).isoformat(),
                          tiebreak_hours=schedule["tiebreak_hours"])
            write_json(poll_file, active)
        if not progress:
            record_start(config, scope, now, state_file)
            progress = read_scoped(state_file, scope)
    return choose_mode(config, active, progress, now, requested)


if __name__ == "__main__":
    config = load_config()
    scope = {"repository": os.environ["GITHUB_REPOSITORY"], "chat_id": os.environ["CHAT_ID"].strip()}
    mode = prepare_mode(config, scope, utc_now(), os.environ.get("REQUESTED_MODE", "auto"))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"mode={mode}\n")
    print(f"Prossima azione: {mode or 'nessuna, in attesa dell’orario configurato'}")
