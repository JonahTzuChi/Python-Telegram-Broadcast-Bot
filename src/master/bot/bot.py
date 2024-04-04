import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    AIORateLimiter,
    filters,
)

import config
import my_utils as mu
import telegram_utils as tu

logging.basicConfig(
    filename="/error/master.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def run_bot() -> None:
    """
    Setting an over `overall_max_rate` to prevent user interaction hitting the bound of rate limiting policy set by
    Telegram. The current bound is 30msg/1second, however, we should also reserve some capacity to the broadcast
    operation.
    """
    application = (
        ApplicationBuilder()
        .token(config.token)
        .read_timeout(30)
        .write_timeout(30)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(overall_max_rate=10, overall_time_period=1, max_retries=5))
        .post_init(tu.post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", tu.start_handler))
    application.add_handler(CommandHandler("subscribe", tu.init_subscribe_handler))
    application.add_handler(CommandHandler("unsubscribe", tu.unsubscribe_handler))
    application.add_handler(CommandHandler("help", tu.help_handler))
    application.add_handler(CommandHandler("follow", tu.get_follow_information_handler))
    application.add_handler(CommandHandler("feedback", tu.start_feedback_handler))
    application.add_handler(CommandHandler("rename", tu.rename_handler))
    application.add_handler(MessageHandler(filters.TEXT, tu.message_handler))

    application.add_error_handler(mu.error_handle)
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
