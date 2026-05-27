import os
import json
import asyncio
from telegram import Bot, InputPollOption

BOT_TOKEN = os.getenv("BOT_TOKEN").strip()
CHAT_ID = int(os.getenv("CHAT_ID").strip())
MODE = os.getenv("MODE").strip()

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

FIRST_POLL_DURATION = 22 * 60 * 60
TIEBREAK_POLL_DURATION = 8 * 60 * 60


async def create_poll(bot, options, question, multiple_answers, duration, poll_type):
    message = await bot.send_poll(
        chat_id=CHAT_ID,
        question=question,
        options=[InputPollOption(text=option) for option in options],
        is_anonymous=True,
        allows_multiple_answers=multiple_answers,
        open_period=duration,
    )

    with open(POLL_FILE, "w") as file:
        json.dump(
            {
                "message_id": message.message_id,
                "poll_type": poll_type,
            },
            file,
        )


async def send_winner_message(bot, winner):
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"Ciccini del {winner} palesatevi con la vostra id reaction e proponete eventuali film nei commenti",
    )


async def close_poll(bot):
    with open(POLL_FILE, "r") as file:
        data = json.load(file)

    poll = await bot.stop_poll(
        chat_id=CHAT_ID,
        message_id=data["message_id"],
    )

    valid_options = [
        option for option in poll.options
        if option.text != EXCLUDED_OPTION
    ]

    max_votes = max(option.voter_count for option in valid_options)

    tied_options = [
        option.text for option in valid_options
        if option.voter_count == max_votes
    ]

    return tied_options


async def main():
    bot = Bot(BOT_TOKEN)

    if MODE == "start":
        await create_poll(
            bot,
            OPTIONS,
            "Che giorno preferite?",
            multiple_answers=True,
            duration=FIRST_POLL_DURATION,
            poll_type="first",
        )

    elif MODE == "close_first":
        tied_options = await close_poll(bot)

        if len(tied_options) == 1:
            await send_winner_message(bot, tied_options[0])
        else:
            await create_poll(
                bot,
                tied_options,
                "Ex aequo: quale giorno scegliamo?",
                multiple_answers=False,
                duration=TIEBREAK_POLL_DURATION,
                poll_type="tiebreak",
            )

    elif MODE == "close_tiebreak":
        tied_options = await close_poll(bot)

        if tied_options:
            await send_winner_message(bot, tied_options[0])


if __name__ == "__main__":
    asyncio.run(main())