import asyncio
import hashlib as hx
import html
import json
import logging
import os
import re
import time
import traceback
from datetime import datetime, timezone, timedelta
from multiprocessing.pool import Pool
from typing import Callable, Coroutine

import requests
import telegram
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User as TgUser,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    CallbackContext,
)

import api
import config
import library.filesystem as fs
import library.validation as val
from const import *
from my_functions import *
from service import ServiceFactory
from data_class.dtype import BroadcastStats

sf = ServiceFactory(config.mongodb_uri, config.bot_id, config.mongodb_database)
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
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    help_message = ""
    for command in available_commands:
        help_message += f"{command[0]} - {command[1]}\n"
    await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)


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
    """
    admin: TgUser = update.message.from_user
    logger.info(f"[0] => {admin.id} | {update.message.text}")
    await register_admin_if_not_exists(admin.id, update.message.chat.id, admin.username)


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
    admin_user: TgUser = update.message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot",
            parse_mode=ParseMode.HTML
        )
        return None

    greeting: str = f"Hi! {admin_user.username} I'm your broadcast agent\nBelow are the available commands:\n"
    await update.message.reply_text(greeting, parse_mode=ParseMode.HTML)
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
    admin_user = update.message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    ready: bool = await admin_service.try_switch_mode(
        admin_user.id, MODE_BROADCAST, MODE_DEFAULT
    )
    if ready:
        await show_broadcast_modes_handler(update, context)
    else:
        await update.message.reply_text(
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
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
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
                config.media_types,
            )
        )
    )
    await update.message.reply_text(
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
    admin_user = update.callback_query.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await update.message.reply_text(
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
    if choice in config.media_types:
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
    admin_user = update.message.from_user
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    await admin_service.set_attribute(admin_user.id, mode=MODE_DEFAULT, dtype="")
    if verbose:
        await update.message.reply_text(
            "Lock released", parse_mode=ParseMode.HTML
        )


async def message_handler(update: Update, context: CallbackContext, message=None):
    admin_user: TgUser = update.message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None
    mode: str = await admin_service.get_attribute(admin_user.id, "mode")
    dtype: str = await admin_service.get_attribute(admin_user.id, "dtype")

    output_msg: str = "Let us play dumb for now."  # default reply
    try:
        _message = message or update.message.text
        if mode == MODE_BROADCAST and dtype in config.media_types:
            t1 = time.time()
            stats: BroadcastStats = await broadcast(dtype, _message, config.seconds)
            t2 = time.time()
            output_msg = f"{stats}\nElapsed time: {t2 - t1} seconds."
        else:
            sender_info = extract_forwarded_sender_info(update)
            if sender_info:
                output_msg = sender_info
        await update.message.reply_text(output_msg, parse_mode=ParseMode.HTML, )
    except Exception as e:
        logger.error(f"[/message_handler] => user: {admin_user.id}, output_message: {output_msg}, error: {e}")
        await update.message.reply_text(str(e), parse_mode=ParseMode.HTML,)
    finally:
        if mode == MODE_BROADCAST:
            await release_handler(update, context, False)


async def broadcast(dtype: str, content: str, seconds: float = 0.2) -> BroadcastStats:
    """
    Broadcast to all active subscribers

    Processes:
    - Iteratively get small batch of active subscribers
    - Broadcast to each subscriber

    Response:
    - Broadcast stats

    Notes:
    - Three way to broadcast: Text, Media
    """
    master = telegram.Bot(token=config.master)
    n: int = await subscriber_service.get_count(STATUS_ACTIVE)
    acc_stats = BroadcastStats(0, 0, 0)  # Accumulated Stats
    for i in range(0, n, config.db_find_limit):
        # Get a small batch of subscribers
        subscribers = await subscriber_service.get_all(
            STATUS_ACTIVE, skip=i, limit=config.db_find_limit
        )
        # Switch to one of the three ways to broadcast
        if dtype == "Text":
            stats: BroadcastStats = await broadcast_message(
                master, subscribers, content, seconds
            )
        else:
            stats: BroadcastStats = await broadcast_media(
                subscribers, dtype, content, config.use_multiproc, config.use_nproc, seconds,
            )
        acc_stats = acc_stats + stats
    return acc_stats


def task_wrapper(
        method: Callable[[telegram.Bot, int, str, str, float], Coroutine[Any, Any, Message | str]],
        subscriber: dict, url: str, caption: str, seconds: float = 0.0
) -> Message | str:
    """
    Wrapper function to make async function non-async to that it can be dispatched to new process.
    """
    return asyncio.run(
        method(
            telegram.Bot(token=config.master),
            subscriber["telegram_id"],
            url,
            caption,
            seconds,
        )
    )


async def broadcast_media(
        subscribers, dtype: str, params: str, use_multiproc=True, use_nproc=2, seconds=0.2
) -> BroadcastStats:
    send_fn = api.selector(dtype)
    url = params[:]
    caption = ""
    if "@@@" in url:
        caption = url.split("@@@")[-1]
        url = url.split("@@@")[0]

    job_hash = hx.md5(url.encode()).hexdigest()
    res_list: Queue[JobSentInformation] = (
        Queue()
    )  # import multiprocessing.pool.ApplyResult failed
    if use_multiproc and use_nproc <= os.cpu_count():
        with Pool(processes=use_nproc) as pool:
            # Sequentially dispatch task to new process
            for subscriber in subscribers:
                if is_job_done(subscriber, job_hash):
                    continue

                user_id = subscriber["telegram_id"]
                username = str(subscriber["username"])
                _sub = {"telegram_id": user_id, "username": username}
                res = pool.apply_async(
                    task_wrapper,
                    args=(send_fn, _sub, url, caption, seconds,),
                    callback=lambda ret: None,
                    error_callback=lambda err: None,
                )
                res_list.put(JobSentInformation(user_id, username, res))
            #
            pool.close()
            pool.join()
        # BEGIN log
        sent_list, failed_list = group_by_result(res_list, True)
    else:
        if use_multiproc:
            logger.warning(
                f"broadcast_media: {use_nproc} > {os.cpu_count()}\nFallback to single process operation."
            )
        res_list: list[JobSentInformation] = list()
        master_bot = telegram.Bot(token=config.master)
        # Sequentially send content to subscribers
        for idx, subscriber in enumerate(subscribers):
            if is_job_done(subscriber, job_hash):
                continue

            user_id = subscriber["telegram_id"]
            username = str(subscriber["username"])
            res_list.append(
                JobSentInformation(
                    user_id,
                    username,
                    await send_fn(master_bot, user_id, url, caption, seconds, ),
                )
            )

        # BEGIN log
        sent_list, failed_list = group_by_result_list(res_list, False)

    n_job = len(sent_list) + len(failed_list)
    n_success = len(sent_list)
    # Sent Case
    for _sub in sent_list:
        subscriber_id, _, tel_msg = _sub.to_tuple()
        await set_job_as_done(subscriber_service, subscriber_id, job_hash)
    # Failed Case
    suffix = str(datetime.now().timestamp()).split(".")[0]
    log_sheet = f"/error/log_{config.bot_id}_{dtype}_{suffix}.csv"
    write_sent_result(log_sheet, failed_list, url)
    # END log
    return BroadcastStats(n_job, n_success, n_job - n_success)  # total, successful, failed


async def broadcast_message(
        master, subscribers, content: str, seconds: float = 0.2
) -> BroadcastStats:
    sent_queue: Queue[JobSentInformation] = Queue()

    for subscriber in subscribers:
        try:
            output_text = content.replace("username", subscriber["username"])
            sent_queue.put(
                JobSentInformation(
                    subscriber["telegram_id"],
                    subscriber["username"],
                    await api.sendMessage(
                        master, subscriber["telegram_id"], output_text, seconds
                    )
                )
            )
        except Exception as e:
            print(str(e))
    sent_list, failed_list = group_by_result(sent_queue, False)
    n_job = len(sent_list) + len(failed_list)
    n_success = len(sent_list)
    # Failed
    suffix = str(datetime.now().timestamp()).split(".")[0]
    log_sheet = f"/error/log_{config.bot_id}_sendMessage_{suffix}.csv"
    write_sent_result(log_sheet, failed_list, content)
    # END log
    return BroadcastStats(n_job, n_success, n_job - n_success)  # total, successful, failed


async def query_nos_button(update: Update, context: CallbackContext):
    """
    Query the number of subscribers

    Remarks:
    - Only active subscribers are included
    """
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    n: int = await subscriber_service.get_count(STATUS_ACTIVE)
    await update.message.reply_text(
        f"Total: {n: 4d} subscribers\n",
        parse_mode=ParseMode.HTML,
    )


async def export_subscribers_button(update: Update, context: CallbackContext):
    """
    Export the list of subscribers in csv format.
    """
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    suffix = str(datetime.now().timestamp()).split(".")[0]
    log_sheet = f"/data/subscribers_{suffix}.csv"
    with open(log_sheet, "w", encoding="utf-8") as file:
        columns = [
            "telegram_id", "chat_id", "username", "mode", "status",
            "n_feedback", "feedback", "reg_datetime",
        ]
        keys = ",".join(columns)
        file.write(f"{keys}\n")

        n: int = await subscriber_service.get_count(STATUS_ACTIVE)
        subscribers = await subscriber_service.get_all(STATUS_ACTIVE, 0, n)
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
        await update.message.reply_document(
            log_sheet,
            caption="subscribers",
            allow_sending_without_reply=True,
            filename=log_sheet,
        )
    except Exception as e:
        print(str(e), flush=True)


async def export_subscribers_full_button(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    suffix = str(datetime.now().timestamp()).split(".")[0]
    log_sheet = f"/data/subscribers_full_{suffix}.txt"
    written: bool = False
    with open(log_sheet, "w", encoding="utf-8") as file:
        status = [STATUS_ACTIVE, STATUS_INACTIVE]
        for _status in status:
            n: int = await subscriber_service.get_count(_status)
            subscribers = await subscriber_service.get_all(_status, 0, n)
            for subscriber in subscribers:
                file.write(f"{subscriber}\n")
                written = True
    if written:
        await update.message.reply_document(
            log_sheet, caption="subscribers", allow_sending_without_reply=True, filename=log_sheet
        )
    else:
        await update.message.reply_text(
            "No subscribers found.", parse_mode=ParseMode.HTML
        )


async def set_upload_subscriber_handler(update: Update, context: CallbackContext):
    """
    Set the bot to accept subscriber loading.

    Processes:
        - Try to switch the bot mode to load subscribers

    Response:
        - If success, invite user to upload subscribers list in .txt file.
        - If failed, prompt user to try again later.
    """
    admin_user: TgUser = update.message.from_user
    is_not_allowed: bool = await is_banned(admin_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    ready: bool = await admin_service.try_switch_mode(admin_user.id, MODE_LOAD_SUB, MODE_DEFAULT)
    output_message: str = "Occupied, please try again later"
    if ready:
        output_message = "Ready to upload subscribers. Please provide the .txt file."
    await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def upload_subscriber(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    export_path = ""
    document = getattr(update.message, "document", None)
    filename = getattr(document, "file_name", None)
    mimetype = getattr(document, "mime_type", None)
    try:
        val_code, val_msg = val.addText_validation_fn(filename, document, mimetype)
        if val_code != 0:
            await update.message.reply_text(val_msg, parse_mode=ParseMode.HTML)
            raise Exception(val_msg)

        export_path = f"/online/{filename}"
        stored = await store_to_drive(context, document.file_id, export_path)
        if not stored:
            raise Exception("File download failed.")
        n_load, n_skip = 0, 0
        with open(export_path, "r", encoding="utf-8") as file:
            while True:
                line = file.readline()
                if not line:  # EOF
                    break
                line = line.strip()
                if len(line) == 0:  # EOF
                    break
                line = line.replace("'", "\"")
                line = line.replace('None', '"None"')
                sub_json: dict = json.loads(line)
                telegram_id: int | None = sub_json.get("telegram_id")
                if telegram_id is None:
                    raise KeyError("telegram_id is None")
                is_exist = await subscriber_service.exists(telegram_id)
                if is_exist:
                    n_skip += 1
                    continue
                subscriber: service.subscriber_service.Subscriber = create_subscriber(sub_json)
                await subscriber_service.add(subscriber)
                await update_non_standard_columns(subscriber_service, sub_json)
                n_load += 1
        os.remove(export_path)
        output_message = f"Loaded: {n_load}\nSkipped: {n_skip}"
        await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)
        return None
    except TelegramError as tg_err:
        logger.error(f"[/load_subscriber]=TelegramError:{str(tg_err)}")
    except Exception as e:
        logger.error(f"[/load_subscriber]=Exception:{str(e)}")
    if export_path != "":
        os.remove(export_path)


async def wapi(update: Update, context: CallbackContext) -> None:
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    query_string = f"unitGroup=metric&key={config.weather_api_key}&contentType=json"
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/penang?{query_string}"
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    result = json.loads(response.text)

    today = result["days"][0]

    # determine the number of seconds required to shift the time
    tdelta = timedelta(seconds=result["tzoffset"] * 3600)
    tz = timezone(offset=tdelta)  # timezone object
    current_time = datetime.now(tz).strftime("%H:%M:%S")  # shift by timezone offset

    # determine the weather of next hour
    capture = None
    for session in today["hours"]:
        if session["datetime"] > current_time:
            capture = session
            # print(f"Captured at {session['datetime']}")
            break

    if capture is None:
        capture = result["days"][1]["hours"][0]

    txt = """
Datetime: {today} {datetime}
Location: {location}
Temperature: {temperature}
Feels like: {feels_like}
Condition: {condition}.
"""
    txt = txt.format(
        today=today['datetime'], datetime=capture['datetime'], location=result['address'],
        temperature=capture['temp'], feels_like=capture['feelslike'], condition=capture['conditions']
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def empty_log(update: Update, context: CallbackContext) -> None:
    """
    Empties the log folder by removing all files in it.

    Args:
        update (Update): The update object containing information about the incoming update.
        context (CallbackContext): The callback context object.

    Returns:
        None

    Notes:
        - Skip *.log files because those are the global logger.
    """
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None
    log_folder = "/error"
    log_paths = os.listdir(log_folder)
    log_paths = list(filter(lambda x: re.search(r".log$", x), log_paths))
    log_paths = list(map(lambda x: os.path.join(log_folder, x), log_paths))
    deleted_count, total_count = 0, len(log_paths)
    for log_path in log_paths:
        try:
            os.remove(log_path)
            deleted_count += 1
        except Exception as e:
            logger.error(f"[/empty_log]=Exception:{str(e)}")
    output_message = f"Removed: {deleted_count} of {total_count} files."
    await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def empty_data(update: Update, context: CallbackContext) -> None:
    """
    Empties the data folder by removing all files in it.

    Args:
        update (Update): The update object containing information about the incoming message.
        context (CallbackContext): The context object for handling callbacks.

    Returns:
        None
    """
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    DATA_FOLDER = "/data"
    data_paths = os.listdir(DATA_FOLDER)
    for dpath in data_paths:
        target_path = os.path.join(DATA_FOLDER, dpath)
        os.remove(target_path)

    txt = f"Removed: {len(data_paths)} files"
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


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
    raise Exception("File download failed.")


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
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    user = update.message.from_user
    filename = update.message.caption  # this does not retrieve the text portion

    in_photo = getattr(update.message, "photo", None)
    in_document = getattr(update.message, "document", None)

    if in_photo:
        telegram_file_id = in_photo[-1].file_id
    elif in_document:
        if in_document.mime_type not in ["image/jpeg", "image/png"]:
            return await update.message.reply_text(
                "Only image files are supported.", parse_mode=ParseMode.HTML
            )
        telegram_file_id = in_document.file_id
        if filename is None:
            filename = update.message.document.file_name
    else:
        output_message = "The attached file failed to add as a photo. Please try to add with compression."
        await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)
        return None

    val_code, val_msg = val.addPhoto_validation_fn(filename, telegram_file_id)
    if val_code != 0:
        return await update.message.reply_text(val_msg, parse_mode=ParseMode.HTML)

    filename = patch_extension(filename)
    export_path = f"/online/{filename}"
    try:
        stored = await store_to_drive(context, telegram_file_id, export_path)
        if stored:
            return await update.message.reply_text("Success", parse_mode=ParseMode.HTML)
        else:
            return await update.message.reply_text(
                "File exists.", parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"[/addPhoto] => user: {user.id}, error: {e}")
        await update.message.reply_text(f"Please try again.\n{e}", parse_mode=ParseMode.HTML,)
        await release_handler(update, context, False)


async def attachment_handler(update: Update, context: CallbackContext):
    """ """
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    admin: TgUser = update.message.from_user
    mode: str | None = await admin_service.get_attribute(admin.id, "mode")
    dtype: str | None = await admin_service.get_attribute(admin.id, "dtype")

    if mode == MODE_ADD_FILE:
        if dtype == MODE_ADD_PHOTO:
            await addPhoto(update, context)
            # reset mode to ensure all attachment are properly handled
            await admin_service.set_attribute(admin.id, mode=MODE_DEFAULT, dtype="")
            return None
        if dtype == MODE_ADD_DOCUMENT:
            await addDocument(update, context)
            await admin_service.set_attribute(admin.id, mode=MODE_DEFAULT, dtype="")
            return None
        if dtype == MODE_ADD_VIDEO:
            await addVideo(update, context)
            await admin_service.set_attribute(admin.id, mode=MODE_DEFAULT, dtype="")
            return None
    if mode == MODE_LOAD_SUB:
        await upload_subscriber(update, context)
        await admin_service.set_attribute(admin.id, mode=MODE_DEFAULT)
        return None
    await update.message.reply_text("Invalid mode", parse_mode=ParseMode.HTML)


async def get_photo(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    folder = f"/online"
    file_list = fs.getSubFiles(folder)
    if len(file_list) == 0:
        await update.message.reply_text("No photo found", parse_mode=ParseMode.HTML)
        return None
    file_list.sort(key=lambda x: x.lower(), reverse=False)
    output_message = "Photos:\n==========\n"
    for filename in file_list:
        file_extension = filename.split(".")[-1]
        if file_extension in ["jpg", "jpeg", "png"]:
            output_message += f"=> {filename}\n"
    output_message += "==========\n"
    await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def get_video(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    folder = f"/online"
    file_list = fs.getSubFiles(folder)
    if len(file_list) == 0:
        await update.message.reply_text("No video found", parse_mode=ParseMode.HTML)
        return None
    file_list.sort(key=lambda x: x.lower(), reverse=False)
    output_message = "Photos:\n==========\n"
    for filename in file_list:
        file_extension = filename.split(".")[-1]
        if file_extension in ["mp4", "mkv"]:
            output_message += f"=> {filename}\n"
    output_message += "==========\n"
    await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def get_document(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    folder = f"/online"
    file_list = fs.getSubFiles(folder)
    if len(file_list) == 0:
        await update.message.reply_text("No document found", parse_mode=ParseMode.HTML)
        return None
    file_list.sort(key=lambda x: x.lower(), reverse=False)
    output_message = "Photos:\n==========\n"
    for filename in file_list:
        file_extension = filename.split(".")[-1]
        if file_extension in ["pdf"]:
            output_message += f"=> {filename}\n"
    output_message += "==========\n"
    await update.message.reply_text(output_message, parse_mode=ParseMode.HTML)


async def clearTaskLog(update: Update, context: CallbackContext) -> None:
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    task_name = update.message.text
    task_name = task_name.replace("/reset_file_tracking", "")
    task_name = task_name.strip()
    if task_name is None or task_name == "":
        await update.message.reply_text(
            f"FAILED. Missing filename.", parse_mode=ParseMode.HTML
        )
        return None

    task_hash = hx.md5(task_name.encode()).hexdigest()
    modified_count = await subscriber_service.clear_task_log(task_hash)
    if modified_count > 0:
        output_msg = f'Clear log for "{task_name}"'
    else:
        output_msg = f'No log found for "{task_name}"'
    await update.message.reply_text(output_msg, parse_mode=ParseMode.HTML)
    return None


async def addDocument(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    admin: TgUser = update.message.from_user
    filename = update.message.caption  # this does not retrieve the text portion

    in_document = getattr(update.message, "document", None)

    if in_document:
        telegram_file_id = in_document.file_id
        if filename is None:
            filename = in_document.file_name
    else:
        await update.message.reply_text(
            "Please attach a non-image file.", parse_mode=ParseMode.HTML
        )
        return None

    mimetype: str = in_document.mime_type
    val_code, val_msg = val.addDocument_validation_fn(
        filename, telegram_file_id, mimetype
    )
    if val_code != 0:
        return await update.message.reply_text(val_msg, parse_mode=ParseMode.HTML)

    output_msg = "Success"
    export_path = f"/online/{filename}"
    try:
        stored = await store_to_drive(context, telegram_file_id, export_path)
        if not stored:
            output_msg = "File exists."
        await update.message.reply_text(output_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"[/addDocument] => user: {admin.id}, error: {e}")
        await update.message.reply_text(
            f"Please try again.\n{e}",
            parse_mode=ParseMode.HTML,
        )
    await release_handler(update, context, False)


async def addVideo(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    admin: TgUser = update.message.from_user

    in_video = getattr(update.message, "video", None)
    in_document = getattr(update.message, "document", None)
    filename = update.message.caption

    if in_video:
        telegram_file_id = in_video.file_id
        mimetype = in_video.mime_type
        if filename is None:
            filename = in_video.file_name
    elif in_document:
        telegram_file_id = in_document.file_id
        mimetype = in_document.mime_type
    else:
        logger.info(f"[/addVideo] => user: {admin.id}, error: {update.message}")
        await update.message.reply_text("Please attach a video file.", parse_mode=ParseMode.HTML)
        return None

    val_code, val_msg = val.addVideo_validation_fn(filename, telegram_file_id, mimetype)
    if val_code != 0:
        return await update.message.reply_text(val_msg, parse_mode=ParseMode.HTML)

    output_msg = "Success"
    export_path = f"/online/{filename}"
    try:
        stored = await store_to_drive(context, telegram_file_id, export_path)
        if not stored:
            output_msg = "File exists."
        await update.message.reply_text(output_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"[/addVideo] => user: {admin.id}, error: {e}")
        await update.message.reply_text(
            f"Please try again.\n{e}",
            parse_mode=ParseMode.HTML,
        )
    await release_handler(update, context, False)


async def add_file_type_handle(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    admin: TgUser = update.message.from_user
    ready: bool = await admin_service.try_switch_mode(
        admin.id, MODE_ADD_FILE, MODE_DEFAULT
    )
    if ready:
        await show_add_file_modes_handle(update, context)
    else:
        await update.message.reply_text(
            "Occupied, please try again later", parse_mode=ParseMode.HTML
        )


async def show_add_file_modes_handle(update: Update, context: CallbackContext):
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    admin: TgUser = update.message.from_user

    REPLY_TEXT = "Select media type you would like to add\n\n"
    modes = [
        MODE_ADD_PHOTO,
        MODE_ADD_DOCUMENT,
        MODE_ADD_VIDEO,
    ]
    keyboard_markup = InlineKeyboardMarkup(
        list(
            map(
                lambda mode: [
                    InlineKeyboardButton(mode, callback_data=f"set_file_type|{mode}")
                ],
                modes,
            )
        )
    )
    await update.message.reply_text(
        REPLY_TEXT, reply_markup=keyboard_markup, parse_mode=ParseMode.HTML
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

    output_dict = dict()
    output_dict[MODE_ADD_PHOTO] = (
        "Ready to accept <strong>Photo</strong>.\n"
        "Please provide photo name as caption with extension."
    )
    output_dict[MODE_ADD_DOCUMENT] = (
        "Ready to accept <strong>Document file</strong>.\n"
        "Please provide file name as caption with extension."
    )
    output_dict[MODE_ADD_VIDEO] = (
        "Ready to accept <strong>Video</strong>.\n"
        "Please provide file name as caption with extension."
    )

    output_msg = "Invalid choice."
    if choice in output_dict.keys():
        await admin_service.set_attribute(admin.id, dtype=choice)
        output_msg = f"{output_dict[choice]}"

    await context.bot.send_message(admin.id, output_msg, parse_mode=ParseMode.HTML,)


async def grant_handler(update: Update, context: CallbackContext) -> None:
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    prompt = update.message.text
    prompt = prompt.replace("/grant", "").strip()
    if len(prompt) == 0:
        await update.message.reply_text(
            "FAILED: Empty input.", parse_mode=ParseMode.HTML
        )
        return None
    superuser_info = prompt.split("|")
    if len(superuser_info) != 2:
        await update.message.reply_text(
            "FAILED: Invalid input. Please supply superuser telegram id and username (separate by |).",
            parse_mode=ParseMode.HTML,
        )
        return None
    tel_id, username = superuser_info
    try:
        await super_service.grant(int(tel_id), username)
        await update.message.reply_text(
            f"Permission granted to {username} ({tel_id}).", parse_mode=ParseMode.HTML
        )
    except Exception as err:
        logger.error(f"[/grant] => user: {update.message.from_user.id}, error: {err}")
        await update.message.reply_text("Failed.", parse_mode=ParseMode.HTML)
    return None


async def revoke_handler(update: Update, context: CallbackContext) -> None:
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    prompt = update.message.text
    prompt = prompt.replace("/revoke", "").strip()
    if len(prompt) == 0:
        await update.message.reply_text(
            "FAILED: Empty input.", parse_mode=ParseMode.HTML
        )
        return None
    try:
        tel_id = int(prompt)
        is_not_allow: bool = await super_service.not_in_allow_list(tel_id)
        if is_not_allow:
            await update.message.reply_text(
                f"{tel_id} is not a superuser.", parse_mode=ParseMode.HTML
            )
        else:
            su = await super_service.search_by_tid(tel_id)
            deleted_count = await super_service.revoke(tel_id)
            if deleted_count != 1:
                raise Exception(
                    f"Failed to revoke {tel_id}. Deleted count: {deleted_count}"
                )
            await update.message.reply_text(
                f"Permission revoked to {su[1]} ({tel_id}).", parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"[/revoke] => user: {update.message.from_user.id}, error: {e}")
        await update.message.reply_text("Failed.", parse_mode=ParseMode.HTML)
    return None


async def list_superuser_handler(update: Update, context: CallbackContext) -> None:
    is_not_allowed: bool = await is_banned(update.message.from_user.id)
    if is_not_allowed:
        await update.message.reply_text(
            "You are banned from using this bot", parse_mode=ParseMode.HTML
        )
        return None

    superuser = await super_service.list_superuser()
    output_msg = "Admins:\n----------\n"
    for idx, su in enumerate(superuser, 1):
        output_msg += f"[{idx}] {su[0]} | {su[1]}\n"

    await update.message.reply_text(output_msg, parse_mode=ParseMode.HTML)


async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    try:
        # collect error message
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        # split text into multiple messages due to 4096 character limit
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(
                    update.effective_chat.id, message_chunk, parse_mode=ParseMode.HTML
                )
            except telegram.error.BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(update.effective_chat.id, message_chunk)
    except Exception as _:
        await context.bot.send_message(
            update.effective_chat.id, "Some error in error handler"
        )
