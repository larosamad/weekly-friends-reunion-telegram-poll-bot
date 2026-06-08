import os
import json
import asyncio
from telegram import Bot, InputPollOption

BOT_TOKEN = os.getenv("BOT_TOKEN").strip()
CHAT_ID   = int(os.getenv("CHAT_ID").strip())
MODE      = os.getenv("MODE").strip()

OPTIONS = [
    "Non posso",
    "Lunedì sera",
    "Martedì sera",
    "Mercoledì sera",
    "Giovedì sera",
    "Venerdì sera",
    "Sabato pomeriggio",
    "Sabato sera",
    "Domenica pomeriggio",
    "Domenica sera",
]
EXCLUDED_OPTION = "Non posso"
POLL_FILE = "poll_info.json"


async def create_poll(bot, options, question, multiple_answers, poll_type):
    message = await bot.send_poll(
        chat_id=CHAT_ID,
        question=question,
        options=[InputPollOption(text=o) for o in options],
        is_anonymous=True,
        allows_multiple_answers=multiple_answers,
    )
    with open(POLL_FILE, "w") as f:
        json.dump({"message_id": message.message_id, "poll_type": poll_type}, f)
    print(f"Sondaggio creato: poll_type={poll_type} message_id={message.message_id}")


async def send_winner_message(bot, winner):
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"Ciccini del {winner} palesatevi con la vostra id reaction e proponete eventuali film nei commenti",
    )
    print(f"Messaggio vincitore inviato: {winner}")


async def close_poll(bot):
    if not os.path.exists(POLL_FILE):
        print("ERRORE: poll_info.json non trovato")
        return []

    with open(POLL_FILE) as f:
        data = json.load(f)

    print(f"Chiudo sondaggio message_id={data['message_id']}")
    poll = await bot.stop_poll(chat_id=CHAT_ID, message_id=data["message_id"])

    valid = [
        opt for opt in poll.options
        if opt.text != EXCLUDED_OPTION and opt.voter_count > 0
    ]
    print(f"Opzioni valide: {[(o.text, o.voter_count) for o in valid]}")

    if not valid:
        print("Nessun voto valido")
        return []

    max_votes = max(o.voter_count for o in valid)
    tied = [o.text for o in valid if o.voter_count == max_votes]
    print(f"In parità ({max_votes} voti): {tied}")
    return tied


async def main():
    bot = Bot(BOT_TOKEN)

    if MODE == "start":
        await create_poll(bot, OPTIONS, "Che giorno preferite?",
                          multiple_answers=True, poll_type="first")

    elif MODE == "close_first":
        tied = await close_poll(bot)
        if len(tied) == 1:
            await send_winner_message(bot, tied[0])
        elif len(tied) > 1:
            print(f"Ex aequo: {tied} → avvio secondo sondaggio")
            await create_poll(bot, tied, "Ex aequo: quale giorno scegliamo?",
                              multiple_answers=False, poll_type="tiebreak")
        else:
            print("Nessun voto — nessuna azione")

    elif MODE == "close_tiebreak":
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
            await send_winner_message(bot, tied[0])


if __name__ == "__main__":
    asyncio.run(main())
