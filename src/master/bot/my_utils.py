import logging

from telegram.constants import ParseMode
from telegram.ext import CallbackContext

import config

logger = logging.getLogger(__name__)


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i: i + chunk_size]


async def error_handle(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    await context.bot.send_message(
        config.dummy_id,
        "Please try again or contact developer.",
        parse_mode=ParseMode.HTML
    )
