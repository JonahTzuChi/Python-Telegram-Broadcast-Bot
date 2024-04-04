# external library
from queue import Queue
from typing import Any
from telegram import Update, Message
# internal library
import service
# data class
from data_class.dtype import JobSentInformation


def extract_forwarded_sender_info(update: Update) -> str | None:
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
    forward_origin = getattr(update.message, "forward_origin", None)
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


def is_job_done(subscriber: Any, hashcode: str) -> bool:
    """
    Check whether the same media file was sent to this subscriber.

    Notes:
    - media file is identified by its hashcode
    - two file with identical hashcode will be considered the same file
    - two identical file with different hashcode (due to different file name) will be considered different file.

    Return:
    - condition (bool): True if the media file was sent to this subscriber, False otherwise

    @Warning: Never attempt to get value directly, KeyError can be very scary!!
    """
    if hashcode not in subscriber.keys():
        return False
    return subscriber[hashcode] == 1


async def set_job_as_done(
        ss: service.subscriber_service.SubscriberService, subscriber_id: int, hashcode: str
) -> None:
    """
    Mark the media file as sent.

    Notes:
    - media file is identified by its hashcode
    - two file with identical hashcode will be considered the same file
    - two identical file with different hashcode (due to different file name) will be considered different file.
    """
    await ss.set_attribute(subscriber_id, _key=hashcode, _value=1)


def write_sent_result(log_sheet_path: str, job_information_list: list[JobSentInformation], content: str) -> None:
    """
    Write job sent information to the log sheet.

    Args:
        log_sheet_path (sheet): path to the log sheet
        job_information_list (list[JobSentInformation]): failed jobs information
        content (str): job content expected to be sent

    Return:
        None
    """
    with open(log_sheet_path, "a") as file:
        file.write(f"Content:{content}\n")
        for jsi in job_information_list:
            file.write(f"{jsi.dump()}\n")


def create_subscriber(
        inp: dict
) -> service.subscriber_service.Subscriber:
    """
    Unpack input dictionary to create Subscriber Object.

    Notes:
        - Only uses standard columns.
    """
    subscriber = service.subscriber_service.Subscriber(
        inp.get("telegram_id"), inp.get("chat_id"),
        inp.get("username"), inp.get("mode"),
        inp.get("status"), inp.get("n_feedback"),
        inp.get("feedback"), inp.get("reg_datetime")
    )
    return subscriber


async def update_non_standard_columns(
        ss: service.subscriber_service.SubscriberService,
        inp: dict
) -> None:
    """
    Update the value to non-standard columns to DB.

    Notes:
        - Mostly are hash_code of media files
    """
    standard_columns: list[str] = [
        "telegram_id", "chat_id", "username", "mode", "status", "n_feedback", "feedback", "reg_datetime"
    ]
    columns = list(filter(lambda column: column not in standard_columns, inp.keys()))
    for col in columns:
        await ss.set_attribute(
            inp.get("telegram_id"), _key=col, _value=inp.get(col)
        )


def patch_extension(filename: str):
    parts = filename.split(".")
    if len(parts) >= 2:
        extension = parts[-1]
        if extension.lower() not in ["jpg", "jpeg", "png"]:
            raise Exception("Invalid file extension")
        return filename
    return filename + ".jpg"


def group_by_result(
        result_queue: Queue[JobSentInformation], is_apply_result: bool
) -> tuple[list[JobSentInformation], list[JobSentInformation]]:
    sent_list, failed_list = list(), list()
    while result_queue.qsize():
        item = result_queue.get()
        sid, uname, result = item.to_tuple()
        if is_apply_result:
            result = result.get()
        if type(result) is Message:
            sent_list.append(JobSentInformation(sid, uname, str(result)))
        else:
            failed_list.append(JobSentInformation(sid, uname, result))

    return sent_list, failed_list


def group_by_result_list(
        result_list: list[JobSentInformation], is_apply_result: bool
) -> tuple[list[JobSentInformation], list[JobSentInformation]]:
    sent_list, failed_list = list(), list()
    for job_result in result_list:
        sid, uname, result = job_result.to_tuple()
        if is_apply_result:
            result = result.get()
        if type(result) is Message:
            sent_list.append(JobSentInformation(sid, uname, str(result)))
        else:
            failed_list.append(JobSentInformation(sid, uname, result))

    return sent_list, failed_list


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i: i + chunk_size]
