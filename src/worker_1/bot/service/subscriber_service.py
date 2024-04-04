from dataclasses import dataclass
from typing import Any
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime


@dataclass
class Subscriber:
    tel_id: int
    chat_id: int
    username: str
    mode: str
    status: str
    n_feedback: int = 0
    feedback: str = ""
    reg_datetime: str = str(datetime.now())

    def to_dict(self) -> dict:
        return {
            "telegram_id": self.tel_id,
            "chat_id": self.chat_id,
            "username": self.username,
            "mode": self.mode,
            "status": self.status,
            "n_feedback": self.n_feedback,
            "feedback": self.feedback,
            "reg_datetime": self.reg_datetime,
        }


class SubscriberService:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.__collection = collection

    async def exists(self, subscriber_id: int, raise_exception: bool = False) -> bool:
        count: int = await self.__collection.count_documents({"telegram_id": subscriber_id})
        if count > 0:
            return True
        if raise_exception:
            raise ValueError(f"{subscriber_id} does not exists")
        return False

    async def get_all(self, target_status: str, skip: int, limit: int):
        find_cursor = self.__collection.find(
            {"status": target_status}, {"_id": 0}, skip=skip, limit=limit
        )
        return await find_cursor.to_list(length=None)

    async def get_count(self, target_status: str) -> int:
        return await self.__collection.count_documents({"status": target_status})

    async def set_attribute(
            self, sub_id: int, _key: str | None = None, _value: Any | None = None, **key_value_pair
    ) -> int:
        await self.exists(sub_id, True)
        # TODO Detect invalid key
        if _key is None or _value is None:
            result = await self.__collection.update_one(
                {'telegram_id': sub_id},
                {'$set': key_value_pair}
            )
            return result.modified_count
        else:
            result = await self.__collection.update_one(
                {'telegram_id': sub_id},
                {'$set': {_key: _value}}
            )
            return result.modified_count

    async def clear_task_log(self, task_hash: str) -> int:
        update_result = await self.__collection.update_many(filter={}, update={"$set": {task_hash: 0}})
        return update_result.modified_count

    async def get_attribute(self, sub_id: int, key: str) -> Any | None:
        await self.exists(sub_id, True)
        document = await self.__collection.find_one(
            {"telegram_id": sub_id}, {key: 1}
        )
        if document:
            if key in document:
                return document[key]
        return None

    async def tick_usage(self, user_id: int, key: str) -> int:
        await self.exists(user_id, True)
        current_value = await self.get_attribute(user_id, key)
        if current_value:
            update_result = await self.__collection.update_one({"telegram_id": user_id}, {"$inc": {key: 1}})
            return update_result.modified_count

        result = await self.__collection.update_one(
            {'telegram_id': user_id},
            {'$set': {
                key: 1
            }}
        )
        return result.modified_count

    async def add(self, subscriber: Subscriber) -> None:
        is_exists: bool = await self.exists(subscriber.tel_id, False)
        if is_exists:
            return None
        await self.__collection.insert_one(subscriber.to_dict())
