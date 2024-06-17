import asyncio
import html
import json
import logging
import os
import re
import time
import traceback
import random
from datetime import datetime, timezone, timedelta
from multiprocessing.pool import Pool, ApplyResult
from typing import Any, Optional, Tuple
from queue import Queue

import requests
import telegram
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User as TgUser,
    Document,
    Message
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest
from telegram.ext import (
    CallbackContext,
)

import config
import library.filesystem as fs
import library.validation as val
from const import *
from library.unnamed import encode as custom_encode_fn
from my_functions import (
    JobTracker,
    extract_forwarded_sender_info,
    split_text_into_chunks,
    patch_extension
)
import service
from service import ServiceFactory

import python_telegram_broadcast as ptb

sf = ServiceFactory(config.mongodb_uri, config.bot_id, config.db_name)
admin_service: service.admin_service.AdminService = sf.get_service("admin")
subscriber_service: service.subscriber_service.SubscriberService = sf.get_service(
    "subscriber"
)
super_service: service.super_service.SuperService = sf.get_service("super")

logger = logging.getLogger(__name__)


async def init_superuser():
    """
    Load admin user into the allow list.
    Args: None

    Returns:
         None

    Note:
        This should be called at the very beginning of the program.
    """
    for tid, uname in zip(config.allowed_tid, config.allowed_username):
        not_in_the_list: bool = await super_service.not_in_allow_list(tid)
        if not_in_the_list:
            await super_service.grant(tid, uname)
            logger.info(f"[GRANT] => {tid} | {uname}")


async def is_banned(user_id: int) -> bool:
    """
    Asynchronously check whether the user is banned from using this bot.

    Args:
        user_id: int The telegram id of the user to be tested

    Returns:
        flag: bool If the user is banned return True, else return False.
    """
    return await super_service.not_in_allow_list(user_id)


available_commands = [
    ("/broadcast", "Enter broadcast mode"),
    ("/upload", "Upload file to backend"),
    ("/release", "Quit broadcast mode"),
    ("/help", "Help"),
    ("/count_subscribers", "Get No. Active Subscribers"),
    ("/export", "Export List of Subscribers"),
    ("/photo", "Get photo list"),
    ("/video", "Get video list"),
    ("/document", "Get document list"),
    ("/weather", "Get Current Weather"),
    ("/terminate", "Broadcast Termination Message"),
    ("/reset_file_tracking", "Reset file tracking"),
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
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    help_message = ""
    for command in available_commands:
        help_message += f"{command[0]} - {command[1]}\n"
    await message.reply_text(help_message, parse_mode=ParseMode.HTML)


async def post_init(application: telegram.ext.Application) -> None:
    """
    Asynchronous handler to initialize the bot.

    Args:
        application: Application

    Returns:
        None

    Steps:
    1. Set the available commands
    2. Set up the superuser allowed list
    """
    await application.bot.set_my_commands(available_commands)
    await init_superuser()


async def middleware_function(update: Update, context: CallbackContext):
    """
    Middleware function to capture every incoming request.

    Save every request to the log file and register admin if not exists.

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
        await context.bot.send_message(config.dummy_id, "context.user_data is None")
        raise TelegramError(f"context.user_data is None. Update={update}\nContext={context}\n")

    context.user_data['is_edit'] = False
    if message is None:
        context.user_data['is_edit'] = True
        message: Optional[Message] = getattr(update, "edited_message", None)
    admin: TgUser = message.from_user
    logger.info(f"[0] => {admin.id}, {message.text}, {message}")
    # msg = await message.reply_text("Processing...")
    # await asyncio.sleep(1)
    # await msg.edit_text(f"Elapsed time: 1 second.", parse_mode=ParseMode.HTML)
    # await asyncio.sleep(1)
    # await msg.edit_text("Updated!!!", parse_mode=ParseMode.HTML)
    await register_admin_if_not_exists(admin.id, message.chat.id, admin.username)


async def register_admin_if_not_exists(
        admin_id: int, chat_id: int, username: str
) -> None:
    """
    Register an admin if they do not already exist.

    Args:
        admin_id (int): The ID of the user.
        chat_id (int): The ID of the chat.
        username (str): The username of the admin.

    Returns:
        None: This function does not return anything.
    """
    is_exists: bool = await admin_service.exists(admin_id)
    if not is_exists:
        admin_object = service.admin_service.AdminUser(
            admin_id, chat_id, username, MODE_DEFAULT, ""
        )
        await admin_service.add(admin_object)


async def start_handler(update: Update, context: CallbackContext) -> None:
    """
    This is triggered when admin_user first `START` the bot

    Authentication:
    - whether the user is banned

    Processes:
    - send greeting message
    - send available commands
    """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot",
            parse_mode=ParseMode.HTML
        )
        return None

    greeting: str = f"Hi! {admin_user.username} I'm your broadcast agent\nBelow are the available commands:\n"
    await message.reply_text(greeting, parse_mode=ParseMode.HTML)
    await help_handler(update, context)


async def try_broadcast_handler(update: Update, context: CallbackContext):
    """
    Try to switch to broadcast mode

    Authentication:
    - whether the user is banned

    Processes:
    - Try to switch to broadcast mode

    Response:
    - If success, show broadcast menu
    - If failed, send "Occupied, please try again later"
    """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    ready: bool = await admin_service.try_switch_mode(
        admin_user.id, MODE_BROADCAST, MODE_DEFAULT
    )
    if ready:
        await show_broadcast_modes_handler(update, context)
    else:
        await message.reply_text(
            "Occupied, please try again later", parse_mode=ParseMode.HTML
        )


async def show_broadcast_modes_handler(update: Update, context: CallbackContext):
    """
    Show available broadcast data types

    Authentication:
    - whether the user is banned

    Processes:
    - Render data type menu

    Response:
    - Send data type menu
    """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    reply_text = "Select media type you would like to broadcast\n\n"
    prefix = "set_broadcast_mode"
    keyboard_markup = InlineKeyboardMarkup(
        list(
            map(
                lambda mode: [
                    InlineKeyboardButton(
                        mode, callback_data=f"{prefix}|{mode}"
                    )
                ],
                config.broadcast_types,
            )
        )
    )
    await message.reply_text(
        reply_text, reply_markup=keyboard_markup, parse_mode=ParseMode.HTML
    )


async def set_broadcast_mode_handler(update: Update, context: CallbackContext):
    """
    Set broadcast data type

    Authentication:
    - whether the user is banned

    Processes:
    - Try to switch to broadcast mode if not already set to broadcast mode
    - Set dtype to the selected data type

    Response:
    - If success, prompt user to submit content to be broadcast
    - If failed, send "Occupied, please try again later"
    """
    admin_user: TgUser = update.callback_query.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    message = update.message
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None
    mode: str = await admin_service.get_attribute(admin_user.id, "mode")
    if mode != MODE_BROADCAST:
        ready: bool = await admin_service.try_switch_mode(
            admin_user.id, MODE_BROADCAST, MODE_DEFAULT
        )
        if ~ready:
            await context.bot.send_message(
                admin_user.id, "Occupied, please try again later", parse_mode=ParseMode.HTML
            )
            return None
    query = update.callback_query
    await query.answer()
    choice = query.data.split("|")[1]
    if choice in config.broadcast_types:
        await admin_service.set_attribute(admin_user.id, dtype=choice)
        reply_text = f"Ready to broadcast <strong>{choice}</strong>."
        await context.bot.send_message(admin_user.id, reply_text, parse_mode=ParseMode.HTML)


async def release_handler(
        update: Update, context: CallbackContext, verbose: bool = True
) -> None:
    """
    Release operation lock to default state

    Authentication:
    - Whether is user is banned

    Processes:
    - Set mode to default
    - Set dtype to ""

    Response:
    - If verbose, "Lock released"
    """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    await admin_service.set_attribute(admin_user.id, mode=MODE_DEFAULT, dtype="")
    if verbose:
        await message.reply_text(
            "Lock released", parse_mode=ParseMode.HTML
        )


async def message_handler(
        update: Update, context: CallbackContext
):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None
    mode: str = await admin_service.get_attribute(admin_user.id, "mode")
    dtype: str = await admin_service.get_attribute(admin_user.id, "dtype")

    output_msg: str = "Let us play dumb for now."  # default reply
    try:
        prompt = message.text
        if mode == MODE_BROADCAST and dtype in config.broadcast_types:
            t1 = time.time()
            stats: ptb.BroadcastStats = await broadcast(dtype, prompt, message)
            t2 = time.time()
            output_msg = f"{stats}\nElapsed time: {round(t2 - t1, 2)} seconds."
        else:
            sender_info = extract_forwarded_sender_info(message)
            if sender_info:
                output_msg = sender_info
        await message.reply_text(output_msg, parse_mode=ParseMode.HTML, )
    except FileNotFoundError as fnf_error:
        logger.error(f"[/message_handler] => user: {admin_user.id}, output_message: {output_msg}, error: {fnf_error}")
        await message.reply_text(f"FileNotFound: {str(fnf_error)}", parse_mode=ParseMode.HTML)
    except ValueError as v_error:
        logger.error(f"[/message_handler] => user: {admin_user.id}, output_message: {output_msg}, error: {v_error}")
        await message.reply_text(f"ValueError: {str(v_error)}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"[/message_handler] => user: {admin_user.id}, output_message: {output_msg}, error: {e}")
        await message.reply_text(f"Exception: {str(e)}", parse_mode=ParseMode.HTML)
    finally:
        if mode == MODE_BROADCAST:
            await release_handler(update, context, False)


async def broadcast(dtype: str, content: str, message: Message) -> ptb.BroadcastStats:
    """
    Broadcast to all active subscribers

    Response:
    - Broadcast stats

    Notes:
    - Two way to broadcast: Text and Media
    """

    # Switch to one of the three ways to broadcast
    if dtype == "TEXT":
        stats: ptb.BroadcastStats = await broadcast_message(
            message, content,
            seconds=config.seconds, use_multiproc=config.use_multi_process, use_nproc=config.use_nproc
        )
    else:
        stats: ptb.BroadcastStats = await broadcast_media(
            message, dtype, content,
            seconds=config.seconds, use_multiproc=config.use_multi_process, use_nproc=config.use_nproc,
            dummy_user=config.dummy_id
        )
    return stats


async def broadcast_media(
        message: Message,
        dtype: str, params: str,
        use_multiproc=True, use_nproc=2, seconds=0.2, dummy_user=0
) -> ptb.BroadcastStats:
    """
    This function supports sending a media file either by URL or from a local directory. If a URL is
    provided, it sends the photo directly. If a file name is provided, it checks if the file exists
    in a predefined local directory and constructs a URL to send the media file.
    """
    # global subscriber_service
    url_or_filename = params[:]
    caption = ""
    if "@@@" in url_or_filename:
        caption = url_or_filename.split("@@@")[-1]
        url_or_filename = url_or_filename.split("@@@")[0]

    # Validate the URL
    if val.isURL(url_or_filename):
        url = url_or_filename
        if "?" not in url:
            url = url + f"?{config.magic_postfix}"
    else:
        if not val.is_valid_fileName(url_or_filename) and len(url_or_filename.split('.')) > 1:
            raise ValueError(f"Invalid file name: {url_or_filename}")
        file_extension = url_or_filename.split(".")[-1].lower()
        if not val.is_ext_align_w_dtype(file_extension, dtype):
            raise ValueError(f"Attempt to broadcast invalid file: {url_or_filename}")
        if not fs.isLocalFile(url_or_filename, "/online"):
            raise FileNotFoundError(url_or_filename)
        url = f"/online/{url_or_filename}"

    job_tracker = JobTracker(subscriber_service, url)
    subscriber_list: list[Tuple[int, str]] = []
    sent: list[ptb.JobResponse] = []
    failed: list[ptb.JobResponse] = []
    n: int = await subscriber_service.get_count(STATUS_ACTIVE)
    progress_message = await message.reply_text("Broadcasting...")

    broadcast_method_type = ptb.string_to_BroadcastMethodType(dtype)
    broadcast_method = ptb.select_broadcast_method(broadcast_method_type)
    if use_multiproc and use_nproc <= os.cpu_count():
        broadcast_strategy = ptb.BroadcastStrategyType.ASYNCIO_PROCESS_POOL
    else:
        broadcast_strategy = ptb.BroadcastStrategyType.ASYNCIO_SEQUENTIAL

    # Get file_id from Telegram
    file_id = ""
    retry = 0
    while len(file_id) == 0 and retry < config.max_retry:
        try:
            file_id = await ptb.get_file_id(
                config.master, broadcast_method, dummy_user, url, caption, seconds, config.max_retry
            )
        except BadRequest as bad_request:
            logger.error(traceback.format_exc())
            raise
            # TODO: if bad_request == "Wrong file identifier/http url specified":
            # url = url + f"&where={random.randint(0, 1000)}"
            # retry += 1
            # logger.info(f"{bad_request}: Attempt {retry}/{config.max_retry}, new_url={url}")
            # if retry == config.max_retry-1 and fs.isLocalFile(url_or_filename, "/online"):
            #     url = f"/online/{url_or_filename}"
        except Exception:
            logger.error(traceback.format_exc())
            raise

    if file_id == "":
        return ptb.evaluate_broadcast_stats(sent, failed)

    for i in range(0, n, config.db_find_limit):
        try:
            subscribers = await subscriber_service.get_all(
                STATUS_ACTIVE, ["telegram_id", "username", job_tracker.job_hash],
                skip=i, limit=config.db_find_limit
            )
            subscriber_list.clear()
            for subscriber in subscribers:
                if job_tracker.is_job_done(subscriber):
                    continue
                subscriber_list.append((subscriber["telegram_id"], subscriber["username"]))

            if len(subscriber_list) == 0:
                continue

            sent_list, failed_list = await ptb.handle_broadcast(
                subscriber_list, config.master, broadcast_method, broadcast_strategy,
                file_id, caption,
                seconds=seconds, use_nproc=use_nproc, dummy_user=dummy_user,
                async_callback=job_tracker
            )
            sent.extend(sent_list)
            failed.extend(failed_list)
            await progress_message.edit_text(f"Tried: {len(sent) + len(failed)}/{n}")
        except Exception as error:
            logger.error(f"[/broadcast_media] => {error}")
            raise

    for jsi in failed:
        telegram_id, username, payload, error = jsi.to_tuple()
        if isinstance(error, ptb.ErrorInformation):
            # These users have blocked the bot
            if error.error_type == "Forbidden":
                await subscriber_service.set_attribute(telegram_id, status=STATUS_INACTIVE)

    if len(failed) > 0:
        log_sheet = f"/error/broadcast_media_{dtype}_{str(time.time())}.txt"
        ptb.write_sent_result(log_sheet, failed, url)

    return ptb.evaluate_broadcast_stats(sent, failed)


async def broadcast_message(
        message: Message, content: str, use_multiproc=True, use_nproc=2, seconds=0.2
) -> ptb.BroadcastStats:
    n: int = await subscriber_service.get_count(STATUS_ACTIVE)
    sent: list[ptb.JobResponse] = []
    failed: list[ptb.JobResponse] = []
    progress_message = await message.reply_text("Broadcasting...")
    broadcast_method = ptb.select_broadcast_method(
        ptb.BroadcastMethodType.TEXT
    )
    if use_multiproc and use_nproc <= os.cpu_count():
        broadcast_strategy = ptb.BroadcastStrategyType.ASYNCIO_PROCESS_POOL
    else:
        broadcast_strategy = ptb.BroadcastStrategyType.ASYNCIO_SEQUENTIAL

    for i in range(0, n, config.db_find_limit):
        # Get a small batch of subscribers
        subscribers = await subscriber_service.get_all(
            STATUS_ACTIVE, ["telegram_id", "username"], skip=i, limit=config.db_find_limit
        )
        subscriber_list = list(
            map(lambda sub: (sub['telegram_id'], sub['username']), subscribers)
        )
        content_list = []
        for subscriber in subscribers:
            username = subscriber['username']
            if username is None:
                content_list.append(content)
            else:
                content_list.append(content.replace("username", username))
        
        content_list = list(
            map(lambda text: f'<a href="{text}">{text}</a>' if val.isURL(text) else text, content_list)
        )
        if len(subscriber_list) == 0:
            continue

        sent_list, failed_list = await ptb.handle_broadcast(
            subscriber_list, config.master, broadcast_method, broadcast_strategy,
            content_list, "",
            seconds=seconds, use_multiproc=use_multiproc, use_nproc=use_nproc
        )
        sent.extend(sent_list)
        failed.extend(failed_list)
        await progress_message.edit_text(f"Tried: {len(sent) + len(failed)}/{n}")

    if len(failed) > 0:
        log_sheet = f"/error/broadcast_message_{str(time.time())}.txt"
        ptb.write_sent_result(log_sheet, failed, content)
    
    return ptb.evaluate_broadcast_stats(sent, failed)


async def query_nos_button(update: Update, context: CallbackContext):
    """
    Query the number of subscribers

    Remarks:
    - Only active subscribers are included
    """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    n: int = await subscriber_service.get_count(STATUS_ACTIVE)
    await message.reply_text(
        f"Total: {n: 4d} subscribers\n",
        parse_mode=ParseMode.HTML,
    )


async def terminate_handler(update: Update, context: CallbackContext):
    """
    Broadcast termination message to subscribers.

    Processes:
        - Try to switch to broadcast mode if not already set to broadcast mode
        - Broadcast termination message to subscribers

    Response:
        Send user broadcast statistics

    Notes:
        This function does not terminate the bot.
    """
    is_edit = context.user_data['is_edit']
    message: Message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    ready: bool = await admin_service.try_switch_mode(
        admin_user.id, MODE_BROADCAST, MODE_DEFAULT
    )
    output_message = "Occupied, please try again few minutes later"

    if ready:
        t1 = time.time()
        stats: ptb.BroadcastStats = await broadcast_message(
            message, config.bot_line["TERMINATION_MSG"],
            use_multiproc=config.use_multi_process, use_nproc=config.use_nproc, seconds=config.seconds
        )
        t2 = time.time()
        output_message = f"{stats}\nElapsed time: {round(t2 - t1, 2)} seconds."
    await message.reply_text(output_message, parse_mode=ParseMode.HTML, )
    await release_handler(update, context, False)  # always release lock


async def export_subscribers_button(update: Update, context: CallbackContext):
    """
    Export the list of subscribers in csv format.
    """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    suffix = str(datetime.now().timestamp()).split(".")[0]
    log_sheet = f"/data/subscribers_{suffix}.csv"
    with open(log_sheet, "w", encoding="utf-8") as file:
        columns = [
            "telegram_id", "chat_id", "username", "mode", "status", "blessed",
            "n_feedback", "feedback", "reg_datetime",
        ]
        keys = ",".join(columns)
        file.write(f"{keys}\n")

        n: int = await subscriber_service.get_count(STATUS_ACTIVE)
        subscribers = await subscriber_service.get_all(STATUS_ACTIVE, None, skip=0, limit=n)
        for subscriber in subscribers:
            user_columns = subscriber.keys()

            data_cells = list(
                map(
                    lambda column: subscriber[column] if column in user_columns else 0,
                    columns,
                )
            )

            data_cells = list(
                map(lambda cell: str(cell), data_cells)
            )

            data_row = ",".join(data_cells)
            # print(">>>>", data_row)
            file.write(f"{data_row}\n")

    try:
        logger.debug("Attempt to send document")
        await message.reply_document(
            log_sheet,
            caption="subscribers",
            allow_sending_without_reply=True,
            filename=log_sheet,
        )
    except Exception as e:
        logger.error(f"[/export_subscribers_button]: {str(e)}")


async def store_to_drive(context: CallbackContext, file_id: str, export_path: str):
    """
    Stores a file from Telegram to a specified drive location.

    This function attempts to download a file based on its Telegram file ID and store it
    in the provided export path on the drive. It first checks if the target path already exists
    to avoid overwriting existing files. If the file does not exist, it proceeds with the download
    and storage process. Timeouts for reading, writing, and connecting are explicitly set for the
    download operation to ensure reliability across different network conditions.

    Parameters:
    - context (CallbackContext): The context provided by the bot framework, which includes
                                 methods for interacting with the Telegram bot API, particularly
                                 for file downloading.
    - fileId (str): The unique identifier for the file on Telegram's servers.
    - exportPath (str): The destination path on the drive where the file should be saved.

    Returns:
    - bool: True if the file was successfully stored, False if the file already exists
            at the specified path.

    Raises:
    - Exception: If any error occurs during the file download or storage process, the
                 exception is raised to be handled by the caller.
    """
    if os.path.exists(export_path):
        return False
    try:
        _file = await context.bot.get_file(
            file_id, read_timeout=300, write_timeout=300, connect_timeout=300, pool_timeout=300,
        )
        await _file.download_to_drive(
            export_path, read_timeout=3000, write_timeout=3000, connect_timeout=3000, pool_timeout=300,
        )
        return True
    except TelegramError as tg_err:
        logger.error(f"[store_to_drive]=TelegramError:{str(tg_err)}")
    except Exception as e:
        logger.error(f"[store_to_drive]=Exception:{str(e)}")
    raise Exception(f"({file_id}, {export_path}) => File download failed.")


async def addPhoto(update: Update, context: CallbackContext):
    """
    Asynchronously handles the storing of a photo sent by a user to a backend storage system.

    This function first validates the provided photo and its filename. If the validation fails,
    it immediately replies to the user with the validation error message. If the validation
    passes, it attempts to store the photo using the `store_to_drive` function. It handles
    potential exceptions by logging them and informing the user of an error.

    Parameters:
    - update (Update): The update instance containing the message from the user. It includes
                       the photo and its caption among other data.
    - context (CallbackContext): The context provided by the bot framework, used here primarily
                                 for accessing bot methods and storage.

    The caption text is used to generate a file name for storing the photo. The photo is expected
    to be in the message's photo list, with the highest resolution photo being selected for storage.

    Returns:
    - None: This function does not return any value. Instead, it uses the `reply_text` method
            to send messages back to the user.

    Raises:
    - Exception: Propagates exceptions from the `store_to_drive` function or any unexpected
                 errors during processing. Logged and reported back to the user.

    Note:
    This function assumes that the `update` object contains a valid message with a photo
    and optionally a caption. It is designed to be used with the telegram bot API.
    """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    filename = message.caption  # this does not retrieve the text portion

    in_photo = getattr(message, "photo", None)
    in_document = getattr(message, "document", None)

    if in_photo:
        telegram_file_id = in_photo[-1].file_id
    elif in_document:
        if in_document.mime_type not in ["image/jpeg", "image/png"]:
            return await message.reply_text(
                "Only image files are supported.", parse_mode=ParseMode.HTML
            )
        telegram_file_id = in_document.file_id
        if filename is None:
            filename = message.document.file_name
    else:
        output_message = "The attached file failed to add as a photo. Please try to add with compression."
        await message.reply_text(output_message, parse_mode=ParseMode.HTML)
        return None

    val_code, val_msg = val.addPhoto_validation_fn(filename, telegram_file_id)
    if val_code != 0:
        return await message.reply_text(val_msg, parse_mode=ParseMode.HTML)

    filename = patch_extension(filename)
    export_path = f"/online/{filename}"
    try:
        stored = await store_to_drive(context, telegram_file_id, export_path)
        if stored:
            return await message.reply_text("Success", parse_mode=ParseMode.HTML)
        else:
            return await message.reply_text(
                "File exists.", parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"[/addPhoto] => user: {admin_user.id}, error: {e}")
        await message.reply_text(f"Please try again.\n{e}", parse_mode=ParseMode.HTML, )
        await release_handler(update, context, False)


async def handle_file_upload(update: Update, context: CallbackContext, dtype: str):
    if dtype == "Photo":
        await addPhoto(update, context)
    elif dtype == "Document":
        await addDocument(update, context)
    else:  # dtype == "Video":
        await addVideo(update, context)


async def attachment_handler(update: Update, context: CallbackContext):
    """ """
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None
    try:
        mode: str | None = await admin_service.get_attribute(admin_user.id, "mode")
        if mode == MODE_ADD_FILE:
            dtype: str | None = await admin_service.get_attribute(admin_user.id, "dtype")
            if dtype not in config.upload_prompt_message.keys():
                await message.reply_text("Invalid upload type.", parse_mode=ParseMode.HTML)
                return None
            await handle_file_upload(update, context, dtype)
            await admin_service.set_attribute(admin_user.id, mode=MODE_DEFAULT, dtype="")
        else:
            await message.reply_text("Invalid mode", parse_mode=ParseMode.HTML)
    except Exception as err:
        logger.error(f"[/attachment_handler] => {str(err)}")
        await message.reply_text(
            "Please try again or contact developer.", parse_mode=ParseMode.HTML
        )


async def get_photo(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    folder = f"/online"
    file_list = fs.getSubFiles(folder)
    if len(file_list) == 0:
        await message.reply_text("No photo found", parse_mode=ParseMode.HTML)
        return None
    file_list.sort(key=lambda x: x.lower(), reverse=False)
    output_message = "Photos:\n==========\n"
    for filename in file_list:
        file_extension = filename.split(".")[-1]
        if file_extension.lower() in ["jpg", "jpeg", "png"]:
            output_message += f"=> {filename}\n"
    output_message += "==========\n"
    await message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def get_video(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    folder = f"/online"
    file_list = fs.getSubFiles(folder)
    if len(file_list) == 0:
        await message.reply_text("No video found", parse_mode=ParseMode.HTML)
        return None
    file_list.sort(key=lambda x: x.lower(), reverse=False)
    output_message = "Videos:\n==========\n"
    for filename in file_list:
        file_extension = filename.split(".")[-1]
        if file_extension in ["mp4", "mkv"]:
            output_message += f"=> {filename}\n"
    output_message += "==========\n"
    await message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def get_document(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    folder = f"/online"
    file_list = fs.getSubFiles(folder)
    if len(file_list) == 0:
        await message.reply_text("No document found", parse_mode=ParseMode.HTML)
        return None
    file_list.sort(key=lambda x: x.lower(), reverse=False)
    output_message = "Documents:\n==========\n"
    for filename in file_list:
        file_extension = filename.split(".")[-1]
        if file_extension in ["pdf"]:
            output_message += f"=> {filename}\n"
    output_message += "==========\n"
    await message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def clearTaskLog(update: Update, context: CallbackContext) -> None:
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    task_name = message.text
    task_name = task_name.replace("/reset_file_tracking", "")
    task_name = task_name.strip()
    if task_name is None or task_name == "":
        await message.reply_text(
            f"FAILED. Missing filename.", parse_mode=ParseMode.HTML
        )
        return None

    if val.isURL(task_name):
        if "?" in task_name:
            task_name = task_name.split("?")[0]
    else:
        if fs.isLocalFile(task_name, "/online"):
            task_name = f"/online/{task_name}"
        else:
            await message.reply_text("FAILED. File not found.", parse_mode=ParseMode.HTML)
            return None

    job_hash = JobTracker.construct_job_hash(task_name)
    modified_count = await subscriber_service.clear_task_log(job_hash)
    if modified_count > 0:
        output_msg = f'Clear log for "{task_name}"'
    else:
        output_msg = f'No log found for "{task_name}"'
    await message.reply_text(output_msg, parse_mode=ParseMode.HTML)
    return None


async def addDocument(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    filename = message.caption  # this does not retrieve the text portion

    in_document = getattr(message, "document", None)

    if in_document:
        telegram_file_id = in_document.file_id
        if filename is None:
            filename = in_document.file_name
    else:
        await message.reply_text(
            "Please attach a non-image file.", parse_mode=ParseMode.HTML
        )
        return None

    mimetype: str = in_document.mime_type
    val_code, val_msg = val.addDocument_validation_fn(
        filename, telegram_file_id, mimetype
    )
    if val_code != 0:
        return await message.reply_text(val_msg, parse_mode=ParseMode.HTML)

    output_msg = "Success"
    export_path = f"/online/{filename}"
    try:
        stored = await store_to_drive(context, telegram_file_id, export_path)
        if not stored:
            output_msg = "File exists."
        await message.reply_text(output_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"[/addDocument] => user: {admin_user.id}, error: {e}")
        await message.reply_text(
            f"Please try again.\n{e}",
            parse_mode=ParseMode.HTML,
        )
    await release_handler(update, context, False)


async def addVideo(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    in_video = getattr(message, "video", None)
    in_document = getattr(message, "document", None)
    filename = message.caption

    if in_video:
        telegram_file_id = in_video.file_id
        mimetype = in_video.mime_type
        if filename is None:
            filename = in_video.file_name
    elif in_document:
        telegram_file_id = in_document.file_id
        mimetype = in_document.mime_type
    else:
        logger.info(f"[/addVideo] => user: {admin_user.id}, error: {message}")
        await message.reply_text("Please attach a video file.", parse_mode=ParseMode.HTML)
        return None

    val_code, val_msg = val.addVideo_validation_fn(filename, telegram_file_id, mimetype)
    if val_code != 0:
        return await message.reply_text(val_msg, parse_mode=ParseMode.HTML)

    output_msg = "Success"
    export_path = f"/online/{filename}"
    try:
        stored = await store_to_drive(context, telegram_file_id, export_path)
        if not stored:
            output_msg = "File exists."
        await message.reply_text(output_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"[/addVideo] => user: {admin_user.id}, error: {e}")
        await message.reply_text(
            f"Please try again.\n{e}",
            parse_mode=ParseMode.HTML,
        )
    await release_handler(update, context, False)


async def add_file_type_handle(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    ready: bool = await admin_service.try_switch_mode(
        admin_user.id, MODE_ADD_FILE, MODE_DEFAULT
    )
    if ready:
        await show_add_file_modes_handle(update, context)
    else:
        await message.reply_text(
            "Occupied, please try again later", parse_mode=ParseMode.HTML
        )


async def show_add_file_modes_handle(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    output_message = "Select media type you would like to add\n\n"
    keyboard_markup = InlineKeyboardMarkup(
        list(
            map(
                lambda mode: [
                    InlineKeyboardButton(mode, callback_data=f"set_file_type|{mode}")
                ],
                config.upload_prompt_message.keys(),
            )
        )
    )
    await message.reply_text(
        output_message, reply_markup=keyboard_markup, parse_mode=ParseMode.HTML
    )


async def set_file_type_handle(update: Update, context: CallbackContext):
    admin: TgUser = update.callback_query.from_user
    is_not_allowed: bool = await is_banned(admin.id)
    if is_not_allowed:
        await context.bot.send_message(
            admin.id,
            "You are banned from using this bot",
            parse_mode=ParseMode.HTML,
        )
        return None

    mode: str = await admin_service.get_attribute(admin.id, "mode")
    if mode != MODE_ADD_FILE:
        ready: bool = await admin_service.try_switch_mode(
            admin.id, MODE_ADD_FILE, MODE_DEFAULT
        )
        if ~ready:
            await context.bot.send_message(
                admin.id,
                "Occupied, please try again later",
                parse_mode=ParseMode.HTML,
            )
            return None

    query = update.callback_query
    await query.answer()
    choice = query.data.split("|")[1]

    output_msg = "Invalid choice."
    if choice in config.upload_prompt_message.keys():
        await admin_service.set_attribute(admin.id, dtype=choice)
        output_msg = f"{config.upload_prompt_message[choice]}"

    await context.bot.send_message(admin.id, output_msg, parse_mode=ParseMode.HTML, )


async def grant_handler(update: Update, context: CallbackContext) -> None:
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    prompt = message.text
    prompt = prompt.replace("/grant", "").strip()
    if len(prompt) == 0:
        await message.reply_text(
            "FAILED: Empty input.", parse_mode=ParseMode.HTML
        )
        return None
    superuser_info = prompt.split("|")
    if len(superuser_info) != 2:
        await message.reply_text(
            "FAILED: Invalid input. Please supply superuser telegram id and username (separate by |).",
            parse_mode=ParseMode.HTML,
        )
        return None
    tel_id, username = superuser_info
    try:
        await super_service.grant(int(tel_id), username)
        await message.reply_text(
            f"Permission granted to {username} ({tel_id}).", parse_mode=ParseMode.HTML
        )
    except Exception as err:
        logger.error(f"[/grant] => user: {admin_user.id}, error: {err}")
        await message.reply_text("Failed.", parse_mode=ParseMode.HTML)
    return None


async def revoke_handler(update: Update, context: CallbackContext) -> None:
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    prompt = message.text
    prompt = prompt.replace("/revoke", "").strip()
    if len(prompt) == 0:
        await message.reply_text(
            "FAILED: Empty input.", parse_mode=ParseMode.HTML
        )
        return None
    try:
        tel_id = int(prompt)
        is_not_allow: bool = await super_service.not_in_allow_list(tel_id)
        if is_not_allow:
            await message.reply_text(
                f"{tel_id} is not a superuser.", parse_mode=ParseMode.HTML
            )
        else:
            su = await super_service.search_by_tid(tel_id)
            deleted_count = await super_service.revoke(tel_id)
            if deleted_count != 1:
                raise Exception(
                    f"Failed to revoke {tel_id}. Deleted count: {deleted_count}"
                )
            await message.reply_text(
                f"Permission revoked to {su[1]} ({tel_id}).", parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"[/revoke] => user: {admin_user.id}, error: {e}")
        await message.reply_text("Failed.", parse_mode=ParseMode.HTML)
    return None


async def list_superuser_handler(update: Update, context: CallbackContext) -> None:
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    superuser = await super_service.list_superuser()
    output_msg = "Admins:\n----------\n"
    for idx, su in enumerate(superuser, 1):
        output_msg += f"[{idx}] {su[0]} | {su[1]}\n"

    await message.reply_text(output_msg, parse_mode=ParseMode.HTML)


async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    try:
        # collect error message
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            f"{html.escape(tb_string)}"
        )

        # split text into multiple messages due to 4096 character limit
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(
                    update.effective_chat.id, f"<pre>{message_chunk}</pre>", parse_mode=ParseMode.HTML
                )
            except telegram.error.BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(
                    update.effective_chat.id, f"<pre>{message_chunk}</pre>",
                    parse_mode=ParseMode.HTML
                )
    except Exception as e:
        logger.error("An error occurred while handling an error", exc_info=e)
        # await context.bot.send_message(
        #     update.effective_chat.id, "Some error in error handler"
        # )


async def who_has_this_file(update: Update, context: CallbackContext):
    is_edit = context.user_data['is_edit']
    message = update.edited_message if is_edit else update.message
    admin_user: TgUser = message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    prompt = message.text
    prompt = prompt.replace("/who_has_this_file", "").strip()
    if len(prompt) == 0:
        await message.reply_text(
            "FAILED: Empty input.", parse_mode=ParseMode.HTML
        )
        return None

    test_case = []
    if val.isURL(prompt):
        if "?" in prompt:
            test_case.append(prompt.split("?")[0])
    else:
        test_case.append(f"/online/{prompt}")  # photo, document, video

    def pick(inp_dict, columns) -> dict:
        return {k: v for k, v in inp_dict.items() if k in columns}

    def list_to_string(lst: list[Any]) -> str:
        lst = list(map(lambda x: "None" if x is None else x, lst))  # Handle None value
        lst = list(map(lambda x: str(x), lst))                      # Convert to string
        return ",".join(lst)
    
    generated_file = []
    target_columns = ["telegram_id", "username", "status", "mode"]
    for test_index, tc in enumerate(test_case, 1):
        job_hash = JobTracker.construct_job_hash(tc)
        subscriber_list = await subscriber_service.who_has_this_file(
            job_hash, target_columns
        )
        if len(subscriber_list) == 0:
            continue
        
        output_msg = f"Content: {tc}\n----------\nSubscriber List:\n----------\n"
        for idx, sub in enumerate(subscriber_list, 1):
            values = list(pick(sub, target_columns).values())
            value_string = list_to_string(values)
            output_msg += f"[{idx}] {value_string}\n"
        file_path = f"/data/who_has_this_file_{test_index}.txt"
        with open(file_path, "w") as f:
            f.write(output_msg)
        generated_file.append(file_path)
    
    if len(generated_file) == 0:
        await message.reply_text("No subscriber.", parse_mode=ParseMode.HTML)
    else:
        for gf in generated_file:
            await message.reply_document(
                document=open(gf, "rb"),
                caption=f"Who has this file? {prompt}",
                parse_mode=ParseMode.HTML, 
                allow_sending_without_reply=True, write_timeout=120, read_timeout=120
            )
            os.remove(gf)
