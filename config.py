"""Legge e valida le impostazioni condivise con l’app Friends Reunion."""
import json
import re
from pathlib import Path

MAX_POLL_OPTIONS = 12
DEFAULT_SCHEDULE = {
    "weekday": 6, "time": "11:07", "timezone": "Europe/Rome",
    "first_poll_hours": 22, "tiebreak_hours": 8,
}
CONFIG_PATH = Path(__file__).with_name("bot_config.json")


def load_config(path=CONFIG_PATH):
    with Path(path).open(encoding="utf-8") as file:
        config = json.load(file)
    if not isinstance(config, dict):
        raise ValueError("La configurazione deve essere un oggetto JSON.")
    options = config.get("OPTIONS")
    if not isinstance(options, list) or not 2 <= len(options) <= MAX_POLL_OPTIONS:
        raise ValueError(f"Inserisci da 2 a {MAX_POLL_OPTIONS} opzioni.")
    if any(not isinstance(option, str) or not option.strip() or len(option) > 100 for option in options):
        raise ValueError("Ogni opzione deve contenere da 1 a 100 caratteri.")
    if len({option.strip() for option in options}) != len(options):
        raise ValueError("Le opzioni devono essere univoche.")
    if config.get("EXCLUDED_OPTION") not in options:
        raise ValueError("L’opzione esclusa deve corrispondere a una delle opzioni.")
    threshold = config.get("MIN_TIEBREAK_VOTES")
    if type(threshold) is not int or not 1 <= threshold <= 9007199254740991:
        raise ValueError("La soglia deve essere un intero positivo.")
    for key, limit in (("FIRST_POLL_QUESTION", 300), ("TIEBREAK_QUESTION", 300), ("GROUP_NAME", 100)):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{key}: inserisci da 1 a {limit} caratteri.")
    schedule = config.get("SCHEDULE", DEFAULT_SCHEDULE)
    if not isinstance(schedule, dict):
        raise ValueError("La programmazione deve essere un oggetto.")
    schedule = {**DEFAULT_SCHEDULE, **schedule}
    if type(schedule["weekday"]) is not int or not 0 <= schedule["weekday"] <= 6:
        raise ValueError("Scegli un giorno della settimana valido.")
    if not isinstance(schedule["time"], str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", schedule["time"]):
        raise ValueError("Inserisci l’ora nel formato HH:mm, es. 11:07.")
    if schedule["timezone"] != "Europe/Rome":
        raise ValueError("Il fuso orario supportato è Europe/Rome.")
    durations = [schedule["first_poll_hours"], schedule["tiebreak_hours"]]
    if any(type(hours) is not int or not 1 <= hours <= 167 for hours in durations) or sum(durations) >= 168:
        raise ValueError("Le durate devono essere ore intere positive, per un totale inferiore a 168 ore.")
    config["SCHEDULE"] = schedule
    return config
