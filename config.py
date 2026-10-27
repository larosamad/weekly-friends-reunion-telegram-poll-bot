"""Legge e valida le impostazioni condivise con l’app Friends Reunion."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("bot_config.json")


def load_config(path=CONFIG_PATH):
    with Path(path).open(encoding="utf-8") as file:
        config = json.load(file)
    if not isinstance(config, dict):
        raise ValueError("La configurazione deve essere un oggetto JSON.")
    options = config.get("OPTIONS")
    if not isinstance(options, list) or not 2 <= len(options) <= 10:
        raise ValueError("Inserisci da 2 a 10 opzioni.")
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
    return config
