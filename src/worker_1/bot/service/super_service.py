from motor.motor_asyncio import AsyncIOMotorCollection


class SuperService:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.__collection = collection

    async def not_in_allow_list(self, tel_id: int) -> bool:
        count = await self.__collection.count_documents({"telegram_id": tel_id})
        return count == 0

    async def grant(self, tel_id: int, username: str) -> None:
        await self.__collection.insert_one({
            "telegram_id": tel_id,
            "username": username
        })

    async def revoke(self, tel_id: int) -> int:
        update_result = await self.__collection.delete_one({"telegram_id": tel_id})
        return update_result.deleted_count
    
    async def count(self) -> int:
        return await self.__collection.count_documents({})

    async def list_superuser(self) -> list[tuple[int, str]]:
        tmp = self.__collection.find({})
        tmp_list = await tmp.to_list(length=None)
        _list = []
        for s in tmp_list:
            _list.append((s["telegram_id"], s["username"]))
        return _list

    async def search_by_tid(self, tel_id: int) -> tuple:
        su = await self.__collection.find_one({"telegram_id": tel_id})
        return su["telegram_id"], su["username"]
