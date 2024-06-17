from datetime import datetime
import asyncio
import charade
import re
from typing import Tuple


async def check_and_update_quota(
    user_id: int,
    scope_lock: asyncio.Lock,
    request_limit: int = 10,
    time_window: int = 60,
) -> bool:
    async with scope_lock:
        if not hasattr(check_and_update_quota, "storage"):
            check_and_update_quota.storage = dict()
        current_time = datetime.now()
        user_info = check_and_update_quota.storage.get(user_id)
        if user_info is None:
            check_and_update_quota.storage[user_id] = (current_time, 1)
            return True
        first_encounter_time, request_count = user_info
        time_since_first_encounter = (current_time - first_encounter_time).total_seconds() / 60
        if time_since_first_encounter > time_window:
            check_and_update_quota.storage[user_id] = (current_time, 1)
            return True
        if request_count < request_limit:
            check_and_update_quota.storage[user_id] = (current_time, request_count + 1,)
            return True
    return False


def isURL(value_string: str) -> bool:
    return "://" in value_string


def is_valid_username(username: str) -> Tuple[bool, str]:
    invalid_username_missing = """
    New name missing. Please follow format /rename new_name
    未提供新名字。請按照格式 /rename 新名字
    """
    invalid_username_len = """
    字数超出限制，中文请勿超过5个字。英文请勿超过20个字母（含空格)
    The number of characters exceeds the limit, please do not exceed 5 characters in Chinese.
    Do not exceed 20 letters in English (including spaces)
    """
    invalid_username_multi_lang = """
    系統只能接收中文名字或英文名字而已；
    請避免同時輸入兩種語言名字，引起不便，還望多多善解！
    The system can only accept Chinese or English names; 
    Please avoid entering names in both languages at the same time, 
    We apologize for any inconvenience caused!
    """

    not_ascii = charade.detect(username.encode())["encoding"] != "ascii"
    has_alphabet = re.search("[a-zA-Z]", username) is not None

    if len(username) == 0:
        return False, invalid_username_missing
    if not_ascii and has_alphabet:
        return False, invalid_username_multi_lang
    elif has_alphabet and len(username) > 20:
        return False, invalid_username_len
    elif not_ascii and len(username) > 5:
        return False, invalid_username_len
    return True, "OK"
