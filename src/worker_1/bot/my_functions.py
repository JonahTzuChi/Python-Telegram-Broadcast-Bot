# external library
import hashlib as hx
import charade
from telegram import Message
# internal library
import config
import service


class JobTracker:
    """
    This class is used to track whether a media file was sent to a subscriber.
    Fundamentally this is a wrapper around the `SubscriberService` class to specifically track media files.
    This class is recognized as an asynchronous callback function in broadcast operations.

    Attributes:
    ------------
    - __service (service.subscriber_service.SubscriberService): SubscriberService instance
    - __job_hash (str): Hashcode of the media file to be tracked

    Notes:
    ------------
    * Media file is identified by its hashcode.
    * Two files with identical hashcode will be considered the same file.
    * Two identical files with different hashcode (due to different file names) will be considered different files.
    * Call __call__ method to mark the media file as sent.

    Example:
    ------------
    >>> job_tracker = JobTracker(subscriber_service, job_hash)
    >>> await job_tracker(telegram_id)

    >>> job_tracker = JobTracker(subscriber_service, job_hash)
    >>> sent = job_tracker.is_job_done(subscriber)
    """

    def __init__(self, ss: service.subscriber_service.SubscriberService, url_or_filename: str):
        """
        Initialize a new instance of the JobTracker class.

        Parameters:
        ------------
        - ss (service.subscriber_service.SubscriberService): SubscriberService instance
        - url_or_filename (str): The URL or filename of the media file
        """
        self.__service = ss
        self.__job_hash = JobTracker.construct_job_hash(url_or_filename)

    async def set_job_as_done(self, telegram_id: int):
        """
        Mark the media file as sent.

        Parameters:
        ------------
        - telegram_id (int): Telegram ID of the subscriber

        Return:
        ------------
        None
        """
        await self.__service.set_attribute(telegram_id, _key=self.__job_hash, _value=1)

    async def __call__(self, telegram_id: int):
        await self.set_job_as_done(telegram_id)

    def is_job_done(self, subscriber: dict) -> bool:
        """
        Check whether the same media file was sent to this subscriber.

        Parameters:
        ------------
        - subscriber (dict): Subscriber information

        Return:
        ------------
        - condition (bool): True if the media file was sent to this subscriber, False otherwise

        Notes:
        ------------
        - Never attempt to get value directly, KeyError can be very scary!!
        """
        if self.__job_hash not in subscriber.keys():
            return False
        return subscriber[self.__job_hash] == 1

    @property
    def job_hash(self) -> str:
        return self.__job_hash

    @classmethod
    def construct_job_hash(cls, url_or_filename: str):
        # Strip away the query string
        url_or_filename = url_or_filename.split("?")[0]
        _bytes = url_or_filename.encode()
        return hx.md5(_bytes).hexdigest()


def extract_forwarded_sender_info(message: Message) -> str | None:
    """
    Extracts sender information from a forwarded Telegram message contained within an Update object.

    This function attempts to retrieve and format the sender information of a forwarded message,
    including the sender's Telegram ID, first name, last name, and username. If the message is not
    forwarded or if sender information cannot be fully retrieved due to privacy settings, the function
    might return partial information or None.

    Parameters:
    - update (Update): The Update object received from the Telegram API, which contains the message data.

    Returns:
    - str | None: A formatted string containing the sender's information if the message is forwarded
                  and the information is available. Returns None if the message is not forwarded or
                  if the necessary information cannot be retrieved.
    """
    output_msg = """
Sender Information:
-----------------------
id: {id}
first_name: {firstname}
last_name: {lastname}
username: {username}
"""
    forward_origin = getattr(message, "forward_origin", None)
    found = False
    if forward_origin:
        found = True
        sender_user = getattr(forward_origin, "sender_user", None)
        if sender_user:
            output_msg = output_msg.format(
                id=sender_user.id,
                firstname=getattr(sender_user, "first_name", None),
                lastname=getattr(sender_user, "last_name", None),
                username=getattr(sender_user, "username", None)
            )
        else:
            output_msg = output_msg.format(
                id="", firstname="", lastname="", username=getattr(forward_origin, "sender_user_name", None)
            )
    return output_msg if found else None


def patch_extension(filename: str):
    parts = filename.split(".")
    if len(parts) >= 2:
        extension = parts[-1]
        if extension.lower() not in ["jpg", "jpeg", "png"]:
            raise Exception("Invalid file extension")
        return filename
    return filename + ".jpg"


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i: i + chunk_size]
