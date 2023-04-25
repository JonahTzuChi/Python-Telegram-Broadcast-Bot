import os
import telegram


async def sendPhoto(bot, target_id, image_name):
    path = f"./static/{image_name}"
    res = await bot.send_photo(
        chat_id=target_id,
        photo=open(path, "rb"),
        caption=image_name,
        allow_sending_without_reply=True,
    )  # reply_to_message_id=target_id,
    print("res:", res["photo"][0]["file_id"])


async def sendPhotoById(bot, target_id, file_id):
    res = await bot.send_photo(
        chat_id=target_id,
        photo=file_id,
        caption="through file id",
        reply_to_message_id=target_id,
        allow_sending_without_reply=True,
    )


async def sendMediaGroup(bot, target_id, collection):
    await bot.send_media_group(
        chat_id=target_id, media=collection, allow_sending_without_reply=True
    )


async def sendDocument(bot: telegram.Bot, target_id, doc):
    res = await bot.sendDocument(
        chat_id=target_id, document=doc, allow_sending_without_reply=True
    )
    print(res)


async def sendVideo(bot: telegram.Bot, target_id, vid):
    res = await bot.sendVideo(
        chat_id=target_id, video=vid, allow_sending_without_reply=True
    )
    print(res)


async def sendMessage(bot, target_id, message):
    res = await bot.sendMessage(chat_id=target_id, text=message)
