import logging
import time

import telegram
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    AIORateLimiter,
    filters,
    CallbackQueryHandler,
)
from typing import Any, Callable, Coroutine, Tuple

import config

import handlers

# setup logging
logging.basicConfig(
    filename=f"/error/worker_{config.bot_id}.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_bot(bot: telegram.ext.Application, ) -> None:
    sysadmin_filter = filters.ALL
    if len(config.sysadmin_tid) > 0:
        sysadmin_filter = filters.User(user_id=config.sysadmin_tid)

    # regular-admin
    bot.add_handler(MessageHandler(filters.ALL, handlers.middleware_function), group=0)
    bot.add_handler(CommandHandler("start", handlers.start_handler), group=1)
    bot.add_handler(CommandHandler("broadcast", handlers.try_broadcast_handler), group=1)
    bot.add_handler(CommandHandler("upload", handlers.add_file_type_handle), group=1)
    bot.add_handler(CommandHandler("release", handlers.release_handler), group=1)
    bot.add_handler(CommandHandler("help", handlers.help_handler), group=1)
    bot.add_handler(CommandHandler("metrics", handlers.query_nos_button), group=1)
    bot.add_handler(CommandHandler("terminate", handlers.terminate_handler), group=1)
    bot.add_handler(CommandHandler("export", handlers.export_subscribers_button), group=1)

    bot.add_handler(CommandHandler("photo", handlers.get_photo), group=1)
    bot.add_handler(CommandHandler("video", handlers.get_video), group=1)
    bot.add_handler(CommandHandler("document", handlers.get_document), group=1)
    bot.add_handler(CommandHandler("reset_file_tracking", handlers.clearTaskLog), group=1)
    
    # sys-admin
    bot.add_handler(CommandHandler("grant", handlers.grant_handler, filters=sysadmin_filter), group=1)
    bot.add_handler(CommandHandler("revoke", handlers.revoke_handler, filters=sysadmin_filter), group=1)
    bot.add_handler(
        CommandHandler("show_superuser", handlers.list_superuser_handler, filters=sysadmin_filter),
        group=1
    )
    bot.add_handler(
        CommandHandler("who_has_this_file", handlers.who_has_this_file, filters=sysadmin_filter), 
        group=1
    )
    bot.add_handler(MessageHandler(filters.TEXT, handlers.message_handler), group=1)
    bot.add_handler(MessageHandler(filters.ATTACHMENT, handlers.attachment_handler), group=1)
    
    # callback
    bot.add_handler(CallbackQueryHandler(handlers.set_broadcast_mode_handler, pattern="^set_broadcast_mode"))
    bot.add_handler(CallbackQueryHandler(handlers.set_file_type_handle, pattern="^set_file_type"))
    bot.add_error_handler(handlers.error_handler)
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
            aio_rate_limiter = AIORateLimiter(max_retries=config.max_retry)
            application = build(
                config.token,
                connect_timeout, read_timeout, write_timeout, media_write_timeout, pool_timeout,
                aio_rate_limiter, handlers.post_init
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
