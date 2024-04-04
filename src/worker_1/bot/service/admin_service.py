from dataclasses import dataclass
from typing import Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection


@dataclass
class AdminUser:
    tel_id: int
    chat_id: int
    username: str
    mode: str
    dtype: str = ""
    reg_datetime: str = str(datetime.now())

    def to_dict(self) -> dict:
        return {
            "telegram_id": self.tel_id,
            "chat_id": self.chat_id,
            "username": self.username,
            "mode": self.mode,
            "dtype": self.dtype,
            "datetime": self.reg_datetime,
        }


class AdminService:
    def __init__(self, collection: AsyncIOMotorCollection, bot_id: int):
        self.__collection = collection
        self.__id = bot_id

    async def exists(self, admin_id: int, raise_exception: bool = False) -> bool:
        count = await self.__collection.count_documents({'telegram_id': self.preprocess_id(admin_id)})
        if count > 0:
            return True
        if raise_exception:
            raise ValueError(f"{admin_id} does not exists")
        return False

    async def add(self, admin: AdminUser) -> None:
        is_exists: bool = await self.exists(admin.tel_id, False)
        if is_exists:
            return None
        admin.tel_id = self.preprocess_id(admin.tel_id)
        await self.__collection.insert_one(admin.to_dict())

    async def get_attribute(self, admin_id: int, key: str) -> Any | None:
        assert len(key) > 0, "Encounter empty string"
        await self.exists(admin_id, True)
        document = await self.__collection.find_one(
            {'telegram_id': self.preprocess_id(admin_id)},
            {key: 1}
        )
        if document:
            if key in document:
                return document[key]
        return None

    async def set_attribute(self, admin_id: int, **key_value_pair) -> int:
        await self.exists(admin_id, True)
        # TODO Detect invalid key
        result = await self.__collection.update_one(
            {'telegram_id': self.preprocess_id(admin_id)},
            {'$set': key_value_pair}
        )
        return result.modified_count

    def preprocess_id(self, admin_id: int) -> str:
        return f"{admin_id}|{self.__id}"

    async def try_switch_mode(self, admin_id: int, mode: str, default: str) -> bool:
        current_mode: str = await self.get_attribute(admin_id, "mode")
        if current_mode == default:
            await self.set_attribute(admin_id, mode=mode)
            return True
        return False
