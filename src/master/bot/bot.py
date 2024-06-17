import logging
import time

import telegram
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    AIORateLimiter,
    filters,
)
from typing import Any, Callable, Coroutine, Tuple

import config
import my_utils as mu
import telegram_utils as tu

logging.basicConfig(
    filename="/error/master.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_bot(bot: telegram.ext.Application) -> None:
    bot.add_handler(MessageHandler(filters.ALL, tu.middleware_function), group=0)
    bot.add_handler(CommandHandler("start", tu.start_handler), group=1)
    bot.add_handler(CommandHandler("subscribe", tu.init_subscribe_handler), group=1)
    bot.add_handler(CommandHandler("unsubscribe", tu.unsubscribe_handler), group=1)
    bot.add_handler(CommandHandler("help", tu.help_handler), group=1)
    bot.add_handler(CommandHandler("follow", tu.get_follow_information_handler), group=1)
    bot.add_handler(CommandHandler("feedback", tu.start_feedback_handler), group=1)
    bot.add_handler(CommandHandler("rename", tu.rename_handler), group=1)
    bot.add_handler(MessageHandler(filters.TEXT, tu.message_handler), group=1)

    bot.add_error_handler(mu.error_handle)
    # start the bot
    bot.run_polling(poll_interval=0)


def build(
    token: str,
    _connect_timeout: float,
    _read_timeout: float,
    _write_timeout: float,
    _media_write_timeout: float,
    _pool_timeout: float,
    rate_limiter: AIORateLimiter,
    post_init_callback: Callable[[telegram.ext.Application], Coroutine[Any, Any, None]]
) -> telegram.ext.Application:
    return (
        ApplicationBuilder()
        .token(token).concurrent_updates(True)
        .connect_timeout(_connect_timeout)
        .read_timeout(_read_timeout).write_timeout(_write_timeout).media_write_timeout(_media_write_timeout)
        .pool_timeout(_pool_timeout)
        .rate_limiter(rate_limiter)
        .post_init(post_init_callback)
        .build()
    )


def update_timeout_factor(tf: float, mf: float = 1.2, _max: float = 10) -> float:
    return round(min(tf * mf, _max), 1)


def update_delay(d: float, mf: float = 1.2, _max: float = 60.0) -> float:
    """Update delay time. (seconds)"""
    return round(min(d * mf, _max), 1)


def update_timeout(
    factor: float,
    _connect_timeout: float,
    _read_timeout: float,
    _write_timeout: float,
    _media_write_timeout: float,
    _pool_timeout: float
) -> Tuple[float, float, float, float, float]:
    return (
        _connect_timeout * factor,
        _read_timeout * factor,
        _write_timeout * factor,
        _media_write_timeout * factor,
        _pool_timeout * factor
    )


if __name__ == "__main__":
    connect_timeout, pool_timeout = 5.0, 1.0
    read_timeout, write_timeout, media_write_timeout = 5.0, 5.0, 20.0
    timeout_factor = 1.2
    delay, delay_factor = 5.0, 1.5
    while True:
        try:
            aio_rate_limiter = AIORateLimiter(
                overall_max_rate=10,
                overall_time_period=1,
                max_retries=config.max_retry
            )
            application = build(
                config.token,
                connect_timeout, read_timeout, write_timeout, media_write_timeout, pool_timeout,
                aio_rate_limiter, tu.post_init
            )
            run_bot(application)
            break
        except telegram.error.TimedOut as error:
            logger.error(f"{type(error).__name__}: {str(error)}")
            # Update timeout
            timeout_factor = update_timeout_factor(timeout_factor)
            connect_timeout, read_timeout, write_timeout, media_write_timeout, pool_timeout = update_timeout(
                timeout_factor,
                connect_timeout, read_timeout, write_timeout, media_write_timeout, pool_timeout
            )
            # Update delay
            delay = update_delay(delay, delay_factor)
            time.sleep(delay)
