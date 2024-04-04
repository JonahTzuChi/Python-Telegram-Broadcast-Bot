import asyncio

import telegram
from telegram.constants import ParseMode
from telegram import Message
from telegram.error import TelegramError

from typing import Union, Callable, Awaitable, Optional
import config as cfg
import library.filesystem as fs
import library.validation as val


async def sendMessage(
        bot: telegram.Bot, target_id: int, message: str, seconds: float = 0.0
) -> Union[Message, str]:
    try:
        if len(message) == 0:
            raise ValueError("Empty message")
        if seconds > 0.0:
            await asyncio.sleep(seconds)
        res: Message = await bot.sendMessage(
            chat_id=target_id, text=message, parse_mode=ParseMode.HTML
        )
        return res
    except TelegramError as tg_err:
        return f"{target_id}=TelegramError:{str(tg_err)}"
    except Exception as e:
        return f"{target_id}={str(e)}"


async def sendPhoto(
        bot: telegram.Bot,
        target_id: int,
        filename_or_url: str,
        caption: str = "",
        seconds: float = 0.0,
) -> Union[Message, str]:
    """
    Asynchronously sends a photo to a specified target using a Telegram bot.

    This function supports sending a photo either by URL or from a local directory. If a URL is
    provided, it sends the photo directly. If a file name is provided, it checks if the file exists
    in a predefined local directory and constructs a URL to send the photo. It can also introduce
    a delay before sending the photo, specified by the `seconds` parameter.

    Parameters:
    - bot (telegram.Bot): An instance of the Telegram Bot used to send the photo.
    - target_id (str): The Telegram chat_id where the photo will be sent.
    - photo (Any): The photo to be sent. Can be a URL or a local file name.
    - caption (str, optional): The caption for the photo. Defaults to an empty string.
    - seconds (float, optional): A delay in seconds before sending the photo. Defaults to 0.0, meaning no delay.

    Returns:
    - bool: True if the photo was sent successfully, False otherwise.

    Raises:
    - Exception: If the photo could not be found locally or any other issue occurs during the sending process.
                 Exceptions are caught and logged, but not re-raised.

    """
    url: str
    try:
        if val.isURL(filename_or_url):
            url = filename_or_url
            if "?" not in url:
                url = url + f"?{cfg.magic_postfix}"
        else:
            if fs.isLocalFile(filename_or_url, "/online"):
                url = f"{cfg.base_server}/{filename_or_url}?{cfg.magic_postfix}"
            else:
                raise FileNotFoundError(filename_or_url)

        if seconds > 0.0:
            await asyncio.sleep(seconds)

        res: Message = await bot.sendPhoto(
            chat_id=target_id,
            photo=url,
            allow_sending_without_reply=True,
            protect_content=False,
            caption=caption,
            read_timeout=20,
            write_timeout=20,
            connect_timeout=20,
            pool_timeout=20,
            parse_mode=ParseMode.HTML,
        )
        return res
    except TelegramError as tg_err:
        return f"{target_id}=TelegramError:{str(tg_err)}"
    except Exception as e:
        return f"{target_id}={str(e)}"


async def sendVideo(
        bot: telegram.Bot,
        target_id: int,
        filename_or_url: str,
        caption: str = "",
        seconds: float = 0.0,
) -> Union[Message, str]:
    url: str
    try:
        if val.isURL(filename_or_url):
            url = filename_or_url
            if "?" not in url:
                url = url + f"?{cfg.magic_postfix}"
        else:
            # ? to have a doc directory? won't hurt to dump them in one big folder
            if fs.isLocalFile(filename_or_url, "/online"):
                url = f"{cfg.base_server}/{filename_or_url}?{cfg.magic_postfix}"
            else:
                raise FileNotFoundError(filename_or_url)

        if seconds > 0.0:
            await asyncio.sleep(seconds)

        res = await bot.sendVideo(
            chat_id=target_id,
            video=url,
            allow_sending_without_reply=True,
            protect_content=False,
            caption=caption,
            read_timeout=100,
            write_timeout=100,
            connect_timeout=100,
            pool_timeout=100,
        )
        return res
    except TelegramError as tg_err:
        return f"{target_id}=TelegramError:{str(tg_err)}"
    except Exception as e:
        return f"{target_id}={str(e)}"


async def sendDocument(
        bot: telegram.Bot,
        target_id: int,
        filename_or_url: str,
        caption: str = "",
        seconds: float = 0.0,
) -> Union[Message, str]:
    url: str
    try:
        if val.isURL(filename_or_url):
            url = filename_or_url
            if "?" not in url:
                url = url + f"?{cfg.magic_postfix}"
        else:
            # ? to have a doc directory? won't hurt to dump them in one big folder
            if fs.isLocalFile(filename_or_url, "/online"):
                url = f"{cfg.base_server}/{filename_or_url}?{cfg.magic_postfix}"
            else:
                raise FileNotFoundError(filename_or_url)

        if seconds > 0.0:
            await asyncio.sleep(seconds)

        res: Message = await bot.sendDocument(
            chat_id=target_id,
            document=url,
            allow_sending_without_reply=True,
            protect_content=False,
            caption=caption,
            read_timeout=20,
            write_timeout=20,
            connect_timeout=20,
            pool_timeout=20,
        )
        return res
    except TelegramError as tg_err:
        return f"{target_id}=TelegramError:{str(tg_err)}"
    except FileNotFoundError as file_not_found_err:
        return f"{target_id}={str(file_not_found_err)}"
    except Exception as e:
        return f"{target_id}={str(e)}"


def selector(
        dtype: str
) -> Optional[Callable[[telegram.Bot, int, str, str, float], Awaitable[Union[Message, str]]]]:
    if dtype == "Photo":
        return sendPhoto
    if dtype == "Document":
        return sendDocument
    if dtype == "Video":
        return sendVideo
    return None
