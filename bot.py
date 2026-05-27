import os
from datetime import time
from telegram import InputPollOption, Update
from telegram.ext import Application, PollHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN").strip()
CHAT_ID = int(os.getenv("CHAT_ID").strip())

DAYS = [
    "Non posso", "Lunedì", "Martedì", "Mercoledì", "Giovedì",
    "Venerdì", "Sabato", "Domenica"
]

EXCLUDED_OPTION = "Non posso"
POLL_DURATION = 8 * 60 * 60


async def start_poll(app: Application, options, question):
    message = await app.bot.send_poll(
        chat_id=CHAT_ID,
        question=question,
        options=[InputPollOption(text=option) for option in options],
        is_anonymous=False,
        allows_multiple_answers=False,
        open_period=POLL_DURATION,
    )

    app.bot_data[message.poll.id] = {
        "chat_id": CHAT_ID,
        "message_id": message.message_id,
        "latest_poll": message.poll,
    }

    app.job_queue.run_once(
        close_and_check_poll,
        when=POLL_DURATION + 5,
        data={"poll_id": message.poll.id},
    )


async def poll_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.poll.id in context.bot_data:
        context.bot_data[update.poll.id]["latest_poll"] = update.poll


async def close_and_check_poll(context: ContextTypes.DEFAULT_TYPE):
    poll_id = context.job.data["poll_id"]
    poll_data = context.bot_data.get(poll_id)

    if not poll_data:
        return

    try:
        poll = await context.bot.stop_poll(
            chat_id=poll_data["chat_id"],
            message_id=poll_data["message_id"],
        )
    except Exception:
        poll = poll_data["latest_poll"]

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
        await start_poll(
            context.application,
            tied_options,
            "Ex aequo: quale giorno scegliamo?"
        )


async def scheduled_poll(context: ContextTypes.DEFAULT_TYPE):
    await start_poll(
        context.application,
        DAYS,
        "Che giorno preferite?"
    )


async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(PollHandler(poll_update))

    app.job_queue.run_daily(
        scheduled_poll,
        time=time(hour=11, minute=0),
        days=(6,),  # 0 = lunedì
    )

    await app.run_polling(allowed_updates=["poll"])


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())