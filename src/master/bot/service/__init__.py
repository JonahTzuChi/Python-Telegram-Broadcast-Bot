from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from . import subscriber_service

COLLECTIONS_NAME = ["subscriber"]


class ServiceFactory:
    def __init__(self, db_uri: str, bot_id: int = None, database_name: str = ""):
        self.__client = AsyncIOMotorClient(db_uri)
        self.__db: AsyncIOMotorDatabase = self.__client[database_name]
        self.__bot_id = bot_id

    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        if collection_name not in COLLECTIONS_NAME:
            raise ValueError(f"{collection_name} is not a valid collection name")

        return self.__db[collection_name]

    def get_service(self, service_name: str):
        if service_name == "subscriber":
            return subscriber_service.SubscriberService(self.get_collection(service_name))
        return None
