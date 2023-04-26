import os
import telegram

"""
    protect_content : bool = False
    any user can access to photo/video/doc we shared through file_id
    protect_content = True will prevent other user from sharing or forwarding
"""


def file_handler(media):
    # raw file
    if type(media) != str:
        return media
    ext = media.split(".")
    # URL
    if "https://" in media or "http://" in media:
        return media
    if len(ext) > 1:
        # file_path, a complete path is required
        if ext[-1].lower() in ["jpg", "jpeg", "png", "mp4", "pdf"]:
            return open(media, "rb")
    # file_id
    return media


async def sendMessage(bot, target_id, message):
    res = await bot.sendMessage(chat_id=target_id, text=message)


async def sendPhoto(
    bot: telegram.Bot, target_id: str, photo: any, caption: str = None, return_id=False
):
    _photo = file_handler(photo)
    res = await bot.send_photo(
        chat_id=target_id,
        photo=_photo,
        caption=caption,
        allow_sending_without_reply=True,
        protect_content=False,
    )
    print(res)
    """
    # what I want to show here is photo[0]['file_id'] is equal to photo[1]['file_id']
    # and many more information are captured here
    Message(
        caption='###', 
        channel_chat_created=False, 
        chat=Chat(first_name='###', id=###, type=<ChatType.PRIVATE>, username='###'), 
        date=datetime.datetime(2023, 4, 26, 1, 14, 34, tzinfo=<UTC>), 
        delete_chat_photo=False, 
        from_user=User(first_name='###', id=###, is_bot=True, username='###_Bot'), 
        group_chat_created=False, 
        message_id=###, 
        photo=(
            PhotoSize(file_id='###', file_size=1431, file_unique_id='@@@@@@@@@@@@@@@@', height=90, width=62), 
            PhotoSize(file_id='###', file_size=7267, file_unique_id='$$$$$$$$$$$$$$$$', height=272, width=186)
        ), 
        supergroup_chat_created=False
    )
    """
    if return_id:
        return res["photo"][0]["file_id"]


async def sendVideo(
    bot: telegram.Bot, target_id: str, video: any, caption: str = None, return_id=False
):
    _video = file_handler(video)
    res = await bot.sendVideo(
        chat_id=target_id,
        video=_video,
        caption=caption,
        allow_sending_without_reply=True,
        protect_content=False,
    )
    print(res)
    """
    Message(
        caption='raw file', 
        channel_chat_created=False, 
        chat=Chat(first_name='###', id=###, type=<ChatType.PRIVATE>, username='###'), 
        date=datetime.datetime(2023, 4, 26, 8, 9, 26, tzinfo=<UTC>), 
        delete_chat_photo=False, 
        from_user=User(first_name='###', id=###, is_bot=True, username='###_Bot'), 
        group_chat_created=False, 
        message_id=###, 
        supergroup_chat_created=False, 
        video=Video(
            api_kwargs={
                'thumbnail': {
                    'file_id': '###', 
                    'file_unique_id': '###', 
                    'file_size': 9700, 'width': 320, 'height': 180
                }
            }, 
            duration=4, 
            file_id='###', 
            file_name='pexels-life-on-super-3324257-1920x1080-18fps.mp4', 
            file_size=1944465, 
            file_unique_id='###', 
            height=1080, 
            mime_type='video/mp4', 
            thumb=PhotoSize(
                file_id='###', 
                file_size=9700, 
                file_unique_id='###', 
                height=180, 
                width=320
            ), 
            width=1920
        )
    )
    """
    if return_id:
        return res["video"]["file_id"]


async def sendDocument(
    bot: telegram.Bot,
    target_id: str,
    document: any,
    caption: str = None,
    return_id=False,
):
    _document = file_handler(document)
    res = await bot.sendDocument(
        chat_id=target_id,
        document=_document,
        caption=caption,
        allow_sending_without_reply=True,
        protect_content=False,
    )
    print(res)
    """
    Message(
        caption='raw file', 
        channel_chat_created=False, 
        chat=Chat(first_name='###', id=###, type=<ChatType.PRIVATE>, username='###'), 
        date=datetime.datetime(2023, 4, 26, 8, 59, 32, tzinfo=<UTC>), 
        delete_chat_photo=False, 
        document=Document(
            api_kwargs={
                'thumbnail': {
                    'file_id': '###', 
                    'file_unique_id': '###', 
                    'file_size': 12967, 
                    'width': 226, 
                    'height': 320
                }
            }, 
            file_id='###', 
            file_name='01. The A-Z of Programming Languages author Computerworld.pdf', 
            file_size=945553, 
            file_unique_id='###', 
            mime_type='application/pdf', 
            thumb=PhotoSize(
                file_id='###', 
                file_size=12967, 
                file_unique_id='###', 
                height=320, 
                width=226
            )
        ), 
        from_user=User(first_name='###', id=###, is_bot=True, username='###_Bot'), 
        group_chat_created=False, 
        message_id=###, 
        supergroup_chat_created=False
    )
    """
    if return_id:
        return res["document"]["file_id"]


async def sendMediaGroup(bot: telegram.Bot, target_id: str, collection: list):
    res = await bot.send_media_group(
        chat_id=target_id,
        media=collection,
        allow_sending_without_reply=True,
        protect_content=False,
    )
    # print(res)
    """
    ### look for media_group_id, observe that they are the same
    (
        Message(
            caption='image 1', 
            channel_chat_created=False, 
            chat=Chat(first_name='###', id=###, type=<ChatType.PRIVATE>, username='###'), 
            date=datetime.datetime(2023, 4, 26, 9, 18, 30, tzinfo=<UTC>), 
            delete_chat_photo=False, 
            from_user=User(first_name='###', id=###, is_bot=True, username='###_Bot'), 
            group_chat_created=False, 
            media_group_id='###', 
            message_id=###, 
            photo=(
                PhotoSize(file_id='###', file_size=1616, file_unique_id='###', height=90, width=90), 
                PhotoSize(file_id='###', file_size=5818, file_unique_id='###', height=225, width=225)
            ), 
            supergroup_chat_created=False
        ), 
        Message(
            caption='image 2', 
            channel_chat_created=False, 
            chat=Chat(first_name='###', id=###, type=<ChatType.PRIVATE>, username='###'), 
            date=datetime.datetime(2023, 4, 26, 9, 18, 30, tzinfo=<UTC>), 
            delete_chat_photo=False, 
            from_user=User(first_name='###', id=###, is_bot=True, username='###_Bot'), 
            group_chat_created=False, 
            media_group_id='###', 
            message_id=###, 
            photo=(
                PhotoSize(file_id='###', file_size=2084, file_unique_id='###', height=90, width=90), 
                PhotoSize(file_id='###', file_size=27169, file_unique_id='###', height=320, width=320), 
                PhotoSize(file_id='###', file_size=93640, file_unique_id='###', height=894, width=894), 
                PhotoSize(file_id='###', file_size=100420, file_unique_id='###', height=800, width=800)
            ), 
            supergroup_chat_created=False
        ), 
        Message(
            caption='image 3', 
            channel_chat_created=False, 
            chat=Chat(first_name='###', id=###, type=<ChatType.PRIVATE>, username='###'), 
            date=datetime.datetime(2023, 4, 26, 9, 18, 30, tzinfo=<UTC>), 
            delete_chat_photo=False, 
            from_user=User(first_name='###', id=###, is_bot=True, username='###_Bot'), 
            group_chat_created=False, 
            media_group_id='###', 
            message_id=###, 
            photo=(
                PhotoSize(file_id='###', file_size=1838, file_unique_id='###', height=90, width=90), 
                PhotoSize(file_id='###', file_size=10214, file_unique_id='###', height=225, width=225)
            ), 
            supergroup_chat_created=False
        )
    )
    """
    return res
