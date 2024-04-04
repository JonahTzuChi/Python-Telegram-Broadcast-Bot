import asyncio
import logging
import random as rn
import re

import charade
from telegram import Update, User as TgUser
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CallbackContext, Application as TgApplication

import api
import config as cfg
import library.filesystem as fs
# services
import service
from const import *
from library.validation import check_and_update_quota
from service import ServiceFactory

sf = ServiceFactory(cfg.mongodb_uri, cfg.mongodb_database)

subscriber_service: service.subscriber_service.SubscriberService = sf.get_service("subscriber")

logger = logging.getLogger(__name__)

available_commands = [
    ("/follow", "👉 Follow me on GitHub"),
    ("/feedback", "✉️ Provide feedback"),
    ("/rename", "✏️ Change username"),
    ("/subscribe", "🌟 Subscribe to the bot"),
    ("/unsubscribe", "🔕 Unsubscribe from the bot"),
    ("/help", "📋 Get command menu"),
]


async def help_handler(update: Update, context: CallbackContext):
    """
        Asynchronous handler to retrieve the command menu.

        Args:
            update: Update
            context: CallbackContext

        Returns:
            None
    """
    subscriber: TgUser = update.message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode != MODE_SUBSCRIBED:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /subscribe to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    help_message = ""
    for command in available_commands:
        help_message += f"{command[0]} - {command[1]}\n"
    await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)


async def post_init(application: TgApplication) -> None:
    """
    Asynchronous handler to initialize the bot.

    Args:
        application: Application

    Returns:
        None

    Steps:
    1. Set the available commands
    """
    await application.bot.set_my_commands(available_commands)


async def register_user_if_not_exists(
    user_id: int, chat_id: int, username: str
) -> None:
    """
        Register an admin if they do not already exist.

        Args:
            user_id (int): The ID of the user.
            chat_id (int): The ID of the chat.
            username (str): The username of the user.

        Returns:
            None: This function does not return anything.
    """
    is_exists: bool = await subscriber_service.exists(user_id, False)
    if not is_exists:
        subscriber_object = service.subscriber_service.Subscriber(
            user_id, chat_id, username, MODE_SUBSCRIBE, STATUS_INACTIVE
        )
        await subscriber_service.add(subscriber_object)


async def unsubscribe_handler(update: Update, context: CallbackContext) -> None:
    """
    Complete the un-subscription process

    Args:
        - update: Update
        - context: CallbackContext

    Remarks:
        - does not remove user from DB
        - Skip if the subscriber is not exists
    """
    subscriber: TgUser = update.message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await update.message.reply_text("You are not subscribed to this Bot.", parse_mode=ParseMode.HTML)
        return None

    await subscriber_service.set_attribute(subscriber.id, mode=MODE_UNSUBSCRIBED, status=STATUS_INACTIVE)
    await update.message.reply_text(cfg.unsubscribe_msg, parse_mode=ParseMode.HTML,)


async def message_handler(update: Update, context: CallbackContext) -> None:
    """This is triggered whenever subscriber send text directly to the bot"""
    subscriber: TgUser = update.message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    message = update.message.text
    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode not in [MODE_SUBSCRIBE, MODE_FEEDBACK]:
        await update.message.reply_text(cfg.sorry_noreply, parse_mode=ParseMode.HTML)
        return None

    if mode == MODE_SUBSCRIBE:
        await subscribe(subscriber.id, message)
    elif mode == MODE_FEEDBACK:
        await feedback(update)
        await help_handler(update, context)
    else:
        # expect nothing from here!!!
        print("BOOM!!!")
    return None


async def init_subscribe_handler(update: Update, context: CallbackContext):
    """
    Handles the initiation of the subscription process for a Telegram user.

    This asynchronous function checks the subscription status of a user when they attempt to subscribe to the bot. It
    utilizes `register_user_if_not_exists` to ensure the user is added to the database with default parameters
    (mode=MODE_SUBSCRIBE, status=STATUS_INACTIVE) if they don't already exist. This function accounts for users who may
    have interacted with the bot previously but did not explicitly unsubscribe before stopping the use of the bot.

    If a user is found to be in `MODE_UNSUBSCRIBED` or `MODE_FEEDBACK`, indicating they were previously subscribed,
    their status is updated to active, and their mode is set to `MODE_SUBSCRIBED`. If the user's mode is already
    `MODE_SUBSCRIBE`, indicating a current subscription attempt or ongoing process, they receive a specific message
    configured for this state. Otherwise, the function confirms their active subscription status without altering their
    existing database record.

    Remarks:
        - The subscription process is directly triggered by the user.
        - Ensures no duplicate subscription records are created for users, handling previously subscribed users
          appropriately.
        - Responds to the user with a message reflecting their subscription status post-invocation, which includes
          confirmation of a new or existing subscription, or a special message for users actively trying to subscribe.
    """
    telegram_user: TgUser = update.message.from_user
    await register_user_if_not_exists(
        telegram_user.id,
        update.message.chat_id,
        telegram_user.username,
    )
    mode: str = await subscriber_service.get_attribute(telegram_user.id, "mode")
    if mode in [MODE_UNSUBSCRIBED, MODE_FEEDBACK]:
        await subscriber_service.set_attribute(telegram_user.id, mode=MODE_SUBSCRIBED, status=STATUS_ACTIVE)
        output_message = "You are now subscribed to our bot"
    elif mode == MODE_SUBSCRIBE:
        output_message = cfg.subscribe_msg
    else:
        output_message = "You are already subscribed to our bot"
    await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def subscribe(subscriber_id: int, subscriber_name: str) -> str:
    """
    Complete the subscription process

    Args:
        - subscriber_id (int): Telegram user ID
        - subscriber_name (str): Name provided by subscriber (Not directly from Telegram)

    Returns:
        - reminder (str): If both ascii and utf-8 is detected
        - named_greeting (str): If only utf-8 or ascii is detected

    Remarks:
        - Validate whether the `subscriber_name` only consist either `Mandarin` or `English`
    """
    # Ensure only one language
    if (
        charade.detect(subscriber_name.encode())["encoding"] != "ascii"
        and re.search("[a-zA-Z]", subscriber_name) is not None
    ):
        return cfg.sorry_single_language_only

    await subscriber_service.set_attribute(
        subscriber_id, username=subscriber_name, mode=MODE_SUBSCRIBED, status=STATUS_ACTIVE
    )

    named_greeting = cfg.greeting_2_msg.replace("username", subscriber_name)
    return named_greeting


async def start_handler(update: Update, context: CallbackContext):
    """
    This is triggered when user first `START` the bot

    1. `Send` user `GREETING`
    1. `Init` the subscription process
    """
    await update.message.reply_text(cfg.greeting_1_msg, parse_mode=ParseMode.HTML)
    await init_subscribe_handler(update, context)


async def get_follow_information_handler(update: Update, context: CallbackContext) -> None:
    """Send subscribers the urls to our social media platform."""
    subscriber: TgUser = update.message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode != MODE_SUBSCRIBED:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /subscribe to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    await subscriber_service.tick_usage(subscriber.id, "follow_us")
    follow_us_msg = [
        "1. [GitHub](https://github.com/JonahTzuChi)",
        "2. [GitLab](https://gitlab.com/JonahYeoh)"
    ]
    for msg in follow_us_msg:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False
        )
    return None


FEEDBACK_GREETING = """
期盼您的回饋，請留下姓名、來自何處，身份，也請留下聯絡號碼以進行聯繫。
感恩！最後，目前程序尚未能處理照片，僅能傳送文字。
We look forward to your feedback. Please leave your name, where you are from, and your identity. 
Please also leave your contact number to get in touch with you.  
Thank you.  Finally, this program is currently not capable of processing photos, but can only send text messages. 😊
"""


async def start_feedback_handler(update: Update, context: CallbackContext) -> None:
    """Set bot to accept subscriber's feedback."""
    subscriber: TgUser = update.message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode != MODE_SUBSCRIBED:
        output_message = "You are not subscribed to this Bot. Please click /subscribe to continue."
    else:
        await subscriber_service.set_attribute(subscriber.id, mode=MODE_FEEDBACK)
        output_message = FEEDBACK_GREETING
    await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)
    return None


async def feedback(update: Update):
    await subscriber_service.tick_usage(update.message.from_user.id, "n_feedback")
    user_id = update.message.from_user.id

    original_msg: str = await subscriber_service.get_attribute(user_id, "feedback")
    feedback_msg = update.message.text
    feedback_msg = f"{original_msg}||{feedback_msg}"
    if len(feedback_msg) > 2048:
        output_message = ("看起來您發送的回饋太多或者回饋內容過長了。\n"
                          "Seems like you have sent too much feedback or the feedback is too long.")
        await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)
        await subscriber_service.set_attribute(user_id, mode=MODE_SUBSCRIBED)
    else:
        await subscriber_service.set_attribute(user_id, feedback=feedback_msg, mode=MODE_SUBSCRIBED)
        await update.message.reply_text(
            "感恩回饋\nThank you for your feedback", parse_mode=ParseMode.HTML
        )


async def rename_handler(update: Update, context: CallbackContext) -> None:
    subscriber: TgUser = update.message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode != MODE_SUBSCRIBED:
        await update.message.reply_text(
            "You are not subscribed to this Bot. Please click /subscribe to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    prompt = update.message.text
    prompt = prompt.replace("/rename", "")
    prompt = prompt.strip()
    new_username = prompt
    try:
        # validation - ensure non-empty string
        if len(new_username) == 0:
            await update.message.reply_text(
                "New name missing. Please follow format /rename new_name",
                parse_mode=ParseMode.HTML
            )
            return None
        # validation - ensure only one language
        if (
                charade.detect(new_username.encode())["encoding"] != "ascii"
                and re.search("[a-zA-Z]", new_username) is not None
        ):
            output_message = cfg.sorry_single_language_only
        else:
            old_username = await subscriber_service.get_attribute(subscriber.id, "username")
            await subscriber_service.set_attribute(subscriber.id, username=new_username)
            output_message = f"Rename successful\n更換成功\n{old_username} => {new_username}"
        await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)
    except Exception as err:
        logger.error(f"[/rename] => {err}")
        await update.message.reply_text("Fail to rename. Please contact developer.", parse_mode=ParseMode.HTML)
