import asyncio
import logging
import random as rn

from telegram import Update, User as TgUser, Message
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest
from telegram.ext import CallbackContext, Application as TgApplication

import python_telegram_broadcast as ptb

from typing import Optional, Tuple
import config as cfg
import library.filesystem as fs
# services
import service
from const import *
from library.validation import check_and_update_quota, is_valid_username
from service import ServiceFactory

sf = ServiceFactory(cfg.mongodb_uri, database_name=cfg.db_name)
subscriber_service: service.subscriber_service.SubscriberService = sf.get_service("subscriber")

logger = logging.getLogger(__name__)

available_commands = [
    ("/follow", "👥 社交平臺"),
    ("/feedback", "✉️ 回饋"),
    ("/rename", "✏️ 更換名字"),
    ("/subscribe", "🌟 訂閱"),
    ("/unsubscribe", "🔕 取消訂閱"),
    ("/help", "🆘 顯示幫助"),
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
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message

    subscriber: TgUser = message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode != MODE_SUBSCRIBED:
        await message.reply_text(
            "You are not subscribed to this Bot. Please click /subscribe to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    help_message = ""
    for command in available_commands:
        help_message += f"{command[0]} - {command[1]}\n"
    await message.reply_text(help_message, parse_mode=ParseMode.HTML)


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


async def middleware_function(update: Update, context: CallbackContext):
    """
    Middleware function to capture every incoming request.

    Save every request to the log file.

    Args:
        update: Update
        context: CallbackContext

    Returns:
        None

    Todos:
    ----------------
    * Find out steps to replicate the scenario where context.user_data is None
    """
    message: Optional[Message] = getattr(update, "message", None)
    if context.user_data is None:
        context.bot_data["not_user"] = True
        logger.warning(f"Non-User Request: {update}")
    else:
        context.bot_data["not_user"] = False
        context.user_data['is_edit'] = False
        if message is None:
            context.user_data['is_edit'] = True
            message: Optional[Message] = getattr(update, "edited_message", None)
        user: TgUser = message.from_user
        logger.info(f"User: {user.username} | Chat: {message.chat_id} | Message: {message.text}")


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
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message

    subscriber: TgUser = message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await message.reply_text("You are not subscribed to this Bot.", parse_mode=ParseMode.HTML)
        return None

    await subscriber_service.set_attribute(subscriber.id, mode=MODE_UNSUBSCRIBED, status=STATUS_INACTIVE)
    await message.reply_text(cfg.bot_line["UNSUBSCRIBE_MSG"], parse_mode=ParseMode.HTML,)


async def message_handler(update: Update, context: CallbackContext) -> None:
    """This is triggered whenever subscriber send text directly to the bot"""
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    subscriber: TgUser = message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    message_str = message.text
    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode not in [MODE_SUBSCRIBE, MODE_FEEDBACK]:
        await message.reply_text(cfg.bot_line["SORRY_NOREPLY"], parse_mode=ParseMode.HTML)
        return None

    if mode == MODE_SUBSCRIBE:
        success, response_str = await subscribe(subscriber.id, message_str)
        await message.reply_text(response_str, parse_mode=ParseMode.HTML)
        if success:
            await asyncio.sleep(1)
            await help_handler(update, context)
    elif mode == MODE_FEEDBACK:
        await feedback(update, context)
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
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message

    telegram_user: TgUser = message.from_user
    await register_user_if_not_exists(
        telegram_user.id,
        message.chat_id,
        telegram_user.username,
    )
    mode: str = await subscriber_service.get_attribute(telegram_user.id, "mode")
    if mode in [MODE_UNSUBSCRIBED, MODE_FEEDBACK]:
        await subscriber_service.set_attribute(telegram_user.id, mode=MODE_SUBSCRIBED, status=STATUS_ACTIVE)
        output_message = "You are now subscribed to our bot"
    elif mode == MODE_SUBSCRIBE:
        output_message = cfg.bot_line["SUBSCRIBE_MSG"]
    else:
        output_message = "You are already subscribed to our bot"
    await message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def subscribe(subscriber_id: int, subscriber_name: str) -> Tuple[bool, str]:
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
    is_valid, output_message = is_valid_username(subscriber_name)
    if is_valid:
        await subscriber_service.set_attribute(
            subscriber_id, username=subscriber_name, mode=MODE_SUBSCRIBED, status=STATUS_ACTIVE
        )
        output_message = cfg.bot_line["GREETING_2_MSG"].replace("username", subscriber_name)
    return is_valid, output_message


async def start_handler(update: Update, context: CallbackContext):
    """
    This is triggered when user first `START` the bot

    1. `Send` user `GREETING`
    1. `Init` the subscription process
    """
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message

    await message.reply_text(cfg.bot_line["GREETING_1_MSG"], parse_mode=ParseMode.HTML)
    await init_subscribe_handler(update, context)


async def get_follow_information_handler(update: Update, context: CallbackContext) -> None:
    """Send subscribers the urls to our social media platform."""
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message

    subscriber: TgUser = message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode != MODE_SUBSCRIBED:
        await message.reply_text(
            "You are not subscribed to this Bot. Please click /subscribe to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    await subscriber_service.tick_usage(subscriber.id, "follow_us")
    follow_us_msg = [
        "1. [Facebook 慈濟馬來西亞分會 Tzu-Chi Merits Society Malaysia](https://www.facebook.com/tcmsia/)",
        "2. [Official Site 佛教慈濟基金會馬來西亞分會 Buddhist Tzu-Chi Merits Society Malaysia](https://www.tzuchi.org.my/)",
        "3. [Jing-Si Books & Cafe 靜思書軒](https://www.jingsibooksncafe.com)"
    ]
    for msg in follow_us_msg:
        await message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False
        )
    return None


FEEDBACK_GREETING = "期盼您的回饋。\nWe look forward to your feedback.😊"


async def start_feedback_handler(update: Update, context: CallbackContext) -> None:
    """Set bot to accept subscriber's feedback."""
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message

    subscriber: TgUser = message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await message.reply_text(
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
    await message.reply_text(output_message, parse_mode=ParseMode.HTML)
    return None


async def feedback(update: Update, context: CallbackContext):
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    user_id = message.from_user.id
    await subscriber_service.tick_usage(user_id, "n_feedback")

    original_msg: str = await subscriber_service.get_attribute(user_id, "feedback")
    feedback_msg = message.text
    feedback_msg = f"{original_msg}||{feedback_msg}"
    if len(feedback_msg) > 2048:
        output_message = ("看起來您發送的回饋太多或者回饋內容過長了。\n"
                          "Seems like you have sent too much feedback or the feedback is too long.")
        await message.reply_text(output_message, parse_mode=ParseMode.HTML)
        await subscriber_service.set_attribute(user_id, mode=MODE_SUBSCRIBED)
    else:
        await subscriber_service.set_attribute(user_id, feedback=feedback_msg, mode=MODE_SUBSCRIBED)
        await message.reply_text(
            "感恩回饋\nThank you for your feedback", parse_mode=ParseMode.HTML
        )


async def rename_handler(update: Update, context: CallbackContext) -> None:
    if context.bot_data["not_user"]:
        return None
    
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message

    subscriber: TgUser = message.from_user
    is_exists: bool = await subscriber_service.exists(subscriber.id, False)
    if not is_exists:
        await message.reply_text(
            "You are not subscribed to this Bot. Please click /start to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    mode: str = await subscriber_service.get_attribute(subscriber.id, "mode")
    if mode != MODE_SUBSCRIBED:
        await message.reply_text(
            "You are not subscribed to this Bot. Please click /subscribe to continue.",
            parse_mode=ParseMode.HTML
        )
        return None

    prompt = message.text
    prompt = prompt.replace("/rename", "")
    prompt = prompt.strip()
    new_username = prompt
    try:
        is_valid, error_message = is_valid_username(new_username)
        if not is_valid:
            await message.reply_text(error_message, parse_mode=ParseMode.HTML)
            return None

        old_username = await subscriber_service.get_attribute(subscriber.id, "username")
        await subscriber_service.set_attribute(subscriber.id, username=new_username)
        output_message = f"Rename successful\n更換成功\n{old_username} => {new_username}"
        await message.reply_text(output_message, parse_mode=ParseMode.HTML)
    except Exception as err:
        logger.error(f"[/rename] => {err}")
        await message.reply_text("Fail to rename. Please contact developer.", parse_mode=ParseMode.HTML)
