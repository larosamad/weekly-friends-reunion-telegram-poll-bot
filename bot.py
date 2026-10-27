import os
import json
import asyncio
from datetime import timedelta
from types import SimpleNamespace
from telegram import Bot, InputPollOption
from config import load_config
from scheduler import prepare_mode, read_scoped, record_start, utc_now, write_json


def get_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(
            f"Variabile d'ambiente '{name}' mancante o vuota. "
            f"Controlla i GitHub Secrets (BOT_TOKEN, CHAT_ID) e il MODE passato dal workflow."
        )
    return value.strip()


BOT_TOKEN = get_env("BOT_TOKEN")
CHAT_ID = int(get_env("CHAT_ID"))
MODE = get_env("MODE")

# Riletta a ogni avvio del bot, anche dopo le modifiche salvate dall’app.
CONFIG = load_config()
OPTIONS = CONFIG["OPTIONS"]
EXCLUDED_OPTION = CONFIG["EXCLUDED_OPTION"]
MIN_TIEBREAK_VOTES = CONFIG["MIN_TIEBREAK_VOTES"]
FIRST_POLL_QUESTION = CONFIG["FIRST_POLL_QUESTION"]
TIEBREAK_QUESTION = CONFIG["TIEBREAK_QUESTION"]
GROUP_NAME = CONFIG["GROUP_NAME"]
POLL_FILE = "poll_info.json"
SCHEDULE_STATE_FILE = "schedule_state.json"
SCOPE = {"repository": os.getenv("GITHUB_REPOSITORY", "local"), "chat_id": str(CHAT_ID)}


async def create_poll(bot, options, question, multiple_answers, poll_type):
    message = await bot.send_poll(
        chat_id=CHAT_ID,
        question=question,
        options=[InputPollOption(text=o) for o in options],
        is_anonymous=True,
        allows_multiple_answers=multiple_answers,
    )
    now = utc_now()
    previous = read_scoped(POLL_FILE, SCOPE, allow_legacy=True) or {}
    schedule = CONFIG["SCHEDULE"]
    tiebreak_hours = previous.get("tiebreak_hours", schedule["tiebreak_hours"])
    hours = schedule["first_poll_hours"] if poll_type == "first" else tiebreak_hours
    write_json(POLL_FILE, {
        "message_id": message.message_id, "poll_type": poll_type, "scope": SCOPE,
        "created_at": now.isoformat(), "close_at": (now + timedelta(hours=hours)).isoformat(),
        "tiebreak_hours": tiebreak_hours, "excluded_option": EXCLUDED_OPTION,
    })
    if poll_type == "first":
        record_start(CONFIG, SCOPE, now, SCHEDULE_STATE_FILE)
    print(f"Sondaggio creato: poll_type={poll_type} message_id={message.message_id}")


async def send_winner_message(bot, winner):
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"{GROUP_NAME} del {winner} palesatevi con la vostra id reaction e proponete eventuali film nei commenti",
    )
    print(f"Messaggio vincitore inviato: {winner}")


async def close_poll(bot):
    if not os.path.exists(POLL_FILE):
        print("ERRORE: poll_info.json non trovato")
        return []

    with open(POLL_FILE) as f:
        data = json.load(f)

    print(f"Chiudo sondaggio message_id={data['message_id']}")
    if "closed_options" in data:
        options = [SimpleNamespace(**option) for option in data["closed_options"]]
    else:
        poll = await bot.stop_poll(chat_id=CHAT_ID, message_id=data["message_id"])
        options = poll.options
        # Retrying a failed follow-up must not try to stop an already closed poll.
        data["closed_options"] = [{"text": option.text, "voter_count": option.voter_count} for option in options]
        write_json(POLL_FILE, data)

    valid = [
        opt for opt in options
        if opt.text != data.get("excluded_option", EXCLUDED_OPTION) and opt.voter_count > 0
    ]
    print(f"Opzioni valide: {[(o.text, o.voter_count) for o in valid]}")

    if not valid:
        print("Nessun voto valido")
        return []

    max_votes = max(o.voter_count for o in valid)
    tied_opts = [o for o in valid if o.voter_count == max_votes]
    print(f"In parità ({max_votes} voti): {[o.text for o in tied_opts]}")
    return tied_opts


async def delete_poll_info():
    if os.path.exists(POLL_FILE):
        os.remove(POLL_FILE)
        print("Removed poll info file")


async def main():
    mode = prepare_mode(CONFIG, SCOPE, utc_now(), MODE, POLL_FILE, SCHEDULE_STATE_FILE)
    if not mode:
        print("Nessuna operazione necessaria: orario non raggiunto o sondaggio già gestito.")
        return
    bot = Bot(BOT_TOKEN)

    if mode == "start":
        await create_poll(
            bot, OPTIONS, FIRST_POLL_QUESTION,
            multiple_answers=True, poll_type="first",
        )

    elif mode == "close_first":
        tied = await close_poll(bot)
        if len(tied) == 1:
            await send_winner_message(bot, tied[0].text)
            await delete_poll_info()
        elif len(tied) > 1:
            # La soglia viene configurata dall’app (valore iniziale: 3).
            if tied[0].voter_count >= MIN_TIEBREAK_VOTES:
                print(f"Ex aequo: {[o.text for o in tied]} → avvio secondo sondaggio")
                await create_poll(
                    bot, [o.text for o in tied], TIEBREAK_QUESTION,
                    multiple_answers=False, poll_type="tiebreak",
                )
            else:
                print(f"Ex aequo con partecipazione insufficiente ({tied[0].voter_count} voti) — nessuna azione")
                await delete_poll_info()
        else:
            print("Nessun voto — nessuna azione")
            await delete_poll_info()

    elif mode == "close_tiebreak":
        if not os.path.exists(POLL_FILE):
            print("Nessun tiebreak attivo — skip")
            return
        with open(POLL_FILE) as f:
            data = json.load(f)
        if data.get("poll_type") != "tiebreak":
            print("Nessun tiebreak attivo — skip")
            return
        tied = await close_poll(bot)
        if tied:
            await send_winner_message(bot, tied[0].text)
        await delete_poll_info()

    else:
        raise RuntimeError(f"MODE '{MODE}' non riconosciuto (atteso: start / close_first / close_tiebreak)")


if __name__ == "__main__":
    asyncio.run(main())
