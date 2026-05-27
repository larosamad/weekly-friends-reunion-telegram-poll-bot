import os
import json
import asyncio
from telegram import Bot, InputPollOption

BOT_TOKEN = os.getenv("BOT_TOKEN").strip()
CHAT_ID = int(os.getenv("CHAT_ID").strip())
MODE = os.getenv("MODE").strip()

DAYS = [
    "Non posso", "Lunedì", "Martedì", "Mercoledì", "Giovedì",
    "Venerdì", "Sabato", "Domenica"
]

EXCLUDED_OPTION = "Non posso"
POLL_FILE = "poll_info.json"


async def create_poll(bot, options, question):
    message = await bot.send_poll(
        chat_id=CHAT_ID,
        question=question,
        options=[InputPollOption(text=option) for option in options],
        is_anonymous=False,
        allows_multiple_answers=False,
        open_period=8 * 60 * 60,
    )

    with open(POLL_FILE, "w") as file:
        json.dump({"message_id": message.message_id}, file)


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

    if len(tied_options) > 1:
        await create_poll(
            bot,
            tied_options,
            "Ex aequo: quale giorno scegliamo?"
        )


async def main():
    bot = Bot(BOT_TOKEN)

    if MODE == "start":
        await create_poll(bot, DAYS, "Che giorno preferite?")
    elif MODE == "close":
        await close_poll(bot)


if __name__ == "__main__":
    asyncio.run(main())