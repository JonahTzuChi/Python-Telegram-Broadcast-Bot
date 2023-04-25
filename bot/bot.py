import telegram
import asyncio
import config

import telegram_utils as tu

TOKEN = config.telegram_token
bot = telegram.Bot(token=TOKEN)

async def main():
    # case-1, send text message
    USER_TELEGRAM_ID = 75316412
    message = "testing"
    #await tu.sendMessage(bot, USER_TELEGRAM_ID, message)
    # case-2, send photo
    image_name = "kawaii_asian_girl.jpeg"
    USER_TELEGRAM_ID = 75316412
    #await tu.sendPhoto(bot, USER_TELEGRAM_ID, image_name)
    # case-3, send photo by file_id
    image_1 = (
        "AgACAgUAAxkDAANOZEdwPMoxw__lBUt5Wgl-vCzicr8AAjW1MRtvGjhWDqzDe-GjbqwBAAMCAANzAAMvBA"
    )
    USER_TELEGRAM_ID = 75316412
    #await tu.sendPhotoById(bot, USER_TELEGRAM_ID, image_1)
    # case-4, send photo in a group
    image_1 = (
        "AgACAgUAAxkDAANOZEdwPMoxw__lBUt5Wgl-vCzicr8AAjW1MRtvGjhWDqzDe-GjbqwBAAMCAANzAAMvBA"
    )
    image_2 = (
        "AgACAgUAAxkDAANdZEeLPA0ND1x3VINM34sZYgOe9GQAAim1MRtvGjhWUp8OPHix_NMBAAMCAANzAAMvBA"
    )
    image_3 = (
        "AgACAgUAAxkDAANcZEeLO0hw-e1YZxdRVZLM2P33UUAAAjW1MRtvGjhWDqzDe-GjbqwBAAMCAANzAAMvBA"
    )
    image_4 = (
        "AgACAgUAAxkDAANjZEeL_EMjTy9e2JiZ6zGL7mu81aYAAjK1MRtvGjhWMwiQuXvyGywBAAMCAANzAAMvBA"
    )
    USER_TELEGRAM_ID = 75316412
    media_collection = [
        telegram.InputMediaPhoto(media=image_1),
        telegram.InputMediaPhoto(media=image_2),
        telegram.InputMediaPhoto(media=image_3),
        telegram.InputMediaPhoto(media=image_4),
    ]
    #await tu.sendMediaGroup(bot, USER_TELEGRAM_ID, media_collection)
    print("END")
    # case-5, send doc
    USER_TELEGRAM_ID = 75316412
    doc = "01. The A-Z of Programming Languages author Computerworld.pdf"
    #await tu.sendDocument(bot, USER_TELEGRAM_ID, open(f"./static/{doc}", "rb"))
    # case-6, send video
    USER_TELEGRAM_ID = 75316412#105816202#
    video_1 = "pexels-life-on-super-3324257-1920x1080-18fps.mp4"
    video_2 = "pexels-life-on-super-3588875-1280x720-18fps.mp4"
    video_3 = "pexels-taryn-elliott-3018669-1920x1080-24fps.mp4" # 10MB++
    video_1_id = "BAACAgUAAxkDAAOOZEed3qRwGHMIE93UYeOcZMieGnkAAnQMAAJvGkBW-cekLfejplkvBA"
    video_2_id = "BAACAgUAAxkDAAOQZEee478uvQnIW8DdUjInfdSDz0AAAnUMAAJvGkBWF195utnoAuQvBA"
    video_3_id = "BAACAgUAAxkDAAOTZEegDHOIYI19tueFBQRvdbAa1TMAAuwIAAISVDlWRm-WtzG5M0YvBA"

    #await tu.sendVideo(bot, USER_TELEGRAM_ID, open(f"./static/{video_3}", "rb"))
    #await tu.sendVideo(bot, USER_TELEGRAM_ID, video_3_id)

    #case-7, mix type, failed
    doc = "01. The A-Z of Programming Languages author Computerworld.pdf"
    video_1 = "pexels-life-on-super-3324257-1920x1080-18fps.mp4"
    media_collection = [
        telegram.InputMediaDocument(media=open(f"./static/{doc}", "rb")),
        telegram.InputMediaVideo(media=open(f"./static/{video_1}", "rb"))
    ]
    #await tu.sendMediaGroup(bot, USER_TELEGRAM_ID, media_collection)
    #case-8, video collection
    video_1_id = "BAACAgUAAxkDAAOOZEed3qRwGHMIE93UYeOcZMieGnkAAnQMAAJvGkBW-cekLfejplkvBA"
    video_2_id = "BAACAgUAAxkDAAOQZEee478uvQnIW8DdUjInfdSDz0AAAnUMAAJvGkBWF195utnoAuQvBA"
    video_3_id = "BAACAgUAAxkDAAOTZEegDHOIYI19tueFBQRvdbAa1TMAAuwIAAISVDlWRm-WtzG5M0YvBA"
    media_collection = [
        telegram.InputMediaVideo(media=video_1_id),
        telegram.InputMediaVideo(media=video_2_id),
        telegram.InputMediaVideo(media=video_3_id)
    ]
    await tu.sendMediaGroup(bot, USER_TELEGRAM_ID, media_collection)

asyncio.run(main())