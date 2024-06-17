from dataclasses import dataclass
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime


@dataclass
class Subscriber:
    tel_id: int
    chat_id: int
    username: str
    mode: str
    status: str
    blessed: int = 0
    n_feedback: int = 0
    feedback: str = ""
    reg_datetime: str = str(datetime.now())

    def to_dict(self) -> dict:
        return {
            "telegram_id": self.tel_id,
            "chat_id": self.chat_id,
            "username": self.username if self.username else "User Name",
            "mode": self.mode,
            "status": self.status,
            "blessed": self.blessed,
            "n_feedback": self.n_feedback,
            "feedback": self.feedback,
            "reg_datetime": self.reg_datetime,
        }


class SubscriberService:
    standard_column = [
        "telegram_id", "chat_id", "username",
        "mode", "status", "blessed",
        "n_feedback", "feedback", "reg_datetime"
    ]

    def __init__(self, collection: AsyncIOMotorCollection):
        self.__collection = collection

    async def exists(self, subscriber_id: int, raise_exception: bool = False) -> bool:
        count: int = await self.__collection.count_documents({"telegram_id": subscriber_id})
        if count > 0:
            return True
        if raise_exception:
            raise ValueError(f"{subscriber_id} does not exists")
        return False

    async def get_all(
            self, target_status: str, target_columns: Optional[list[str]], skip: int = 0, limit: int = 100
    ):
        """Get all subscribers with the target status.

        Notes:
        ---------------------------
        Claude: In MongoDB, when you use the find method with a projection that includes a field that doesn't exist in
        some documents, MongoDB will handle it gracefully without throwing an error.

        Here's what happens:
        - Documents without the specified field:
            - For documents that don't have the field specified in the projection,
                MongoDB will simply exclude it and return the other fields that exist in those documents.
        - Documents with the specified field:
            - For documents that have the field specified in the projection, MongoDB will include that field in
        the result.

        - If the target_columns is None, the projection will exclude the _id field.
        - If the target_columns is an empty list, the projection will exclude the _id field.
        """
        search_filter = {"status": target_status}
        if target_columns is None:
            search_projection = {"_id": 0}
        elif len(target_columns) == 0:
            search_projection = {"_id": 0}
        else:
            search_projection = {"telegram_id": 1, "username": 1, "_id": 0}
            for col in target_columns:
                search_projection.update({col: 1})

        find_cursor = self.__collection.find(
            search_filter, search_projection, skip=skip, limit=limit
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

    async def bless(self, user_id: int) -> int:
        await self.exists(user_id, True)
        update_result = await self.__collection.update_one({"telegram_id": user_id}, {"$inc": {"blessed": 1}})
        return update_result.modified_count

    async def get_mini_luck_subscriber(self, user_id: int, batch_size: int = 10) -> int:
        await self.exists(user_id, True)
        pipelines = [
            {
                "$match": {
                    "status": "active",
                    "telegram_id": {
                        "$ne": user_id
                    }
                }
            },
            {
                "$project": {
                    "telegram_id": 1,
                    "blessed": 1
                }
            },
            {
                "$sample": {
                    "size": batch_size
                }
            }
        ]
        subscribers_cursor = self.__collection.aggregate(pipelines)
        subscribers = await subscribers_cursor.to_list(length=None)

        lst = []
        for subscriber in subscribers:
            lst.append(
                {'telegram_id': subscriber['telegram_id'], 'blessed': subscriber['blessed']}
            )

        # < than 2 subscribers
        if len(lst) == 0:
            raise Exception("No subscribers found.")

        # Find the least blessed subscriber
        lst.sort(key=lambda x: x['blessed'], reverse=False)
        return lst[0]['telegram_id']

    async def add(self, subscriber: Subscriber) -> None:
        is_exists: bool = await self.exists(subscriber.tel_id, False)
        if is_exists:
            return None
        await self.__collection.insert_one(subscriber.to_dict())

    async def who_has_this_file(self, file_hash: str, target_column: list[str] = [], limit: int = 100):
        """
        Get the list of subscribers who have previously received the target file.
        
        This method exists to help sys-admin to track the distribution of files.
        
        Parameters:
        ---------------------------
        - file_hash (str): The hash of the target file.
        - target_column (list[str]): The list of columns to be included in the result.
        
        Returns:
        ---------------------------
        - list[dict]: The list of subscribers who have previously received the target file.

        Notes:
        ---------------------------
        - Loop through the entire collection.
        - Only include `active` subscribers.
        """
        search_filter = { file_hash: 1, "status": "active" }
        search_projection = {"_id": 0}
        for col in target_column:
            search_projection.update({col: 1})
        
        page_size = limit
        n = await self.get_count("active")
        subscriber_list = []
        for i in range(0, n, page_size):
            find_cursor = self.__collection.find(
                search_filter, search_projection, skip=i, limit=page_size
            )
            lst = await find_cursor.to_list(length=None)
            if len(lst) == 0:
                break
            subscriber_list.extend(lst)
        return subscriber_list

    @classmethod
    def create_subscriber(cls, inp: dict) -> Subscriber:
        """
        Unpack input dictionary to create Subscriber Object.

        Notes:
            - Only uses standard columns.
        """
        params = list(map(lambda column: inp.get(column), SubscriberService.standard_column))
        params = list(map(lambda param: None if param == "None" else param, params))
        subscriber = Subscriber(*params)
        return subscriber

    async def update_non_standard_columns(
            self, inp: dict
    ) -> None:
        """
        Update the value to non-standard columns to DB.

        Notes:
            - Mostly are hash_code of media files
        """
        columns = list(filter(lambda column: column not in SubscriberService.standard_column, inp.keys()))
        telegram_id = inp.get("telegram_id")
        for col in columns:
            await self.set_attribute(
                telegram_id, _key=col, _value=inp.get(col)
            )
