from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
import pymongo
from . import admin_service, subscriber_service, super_service

COLLECTIONS_NAME = ["subscriber", "admin", "super"]


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
        if service_name == "admin":
            return admin_service.AdminService(self.get_collection(service_name), self.__bot_id)
        elif service_name == "subscriber":
            return subscriber_service.SubscriberService(self.get_collection(service_name))
        elif service_name == "super":
            return super_service.SuperService(self.get_collection(service_name))
        return None
