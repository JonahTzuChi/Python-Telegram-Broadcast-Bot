from datetime import datetime
import asyncio


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
