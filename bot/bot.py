import telegram
import asyncio
import config

import telegram_utils as tu

TOKEN = config.telegram_token
CDN = "https://jonahtzuchi.github.io/Python-Telegram-Broadcast-Bot"

# Most we can't test all of the test-case at once due to request frequency set by Telegram
# Uncomment code you would like to test

async def main():
    # Initialize bot
    bot = telegram.Bot(token=TOKEN)
    # valid telegram user id in integer format
    # just replace config.target below to telegram id of your receiver
    # before this make sure 
    ### the receiver's telegram account search for your bot
    ### the user click the "start" button
    # otherwise, the user won't be able to receive the content you are about to send
    RECEIVER_TELEGRAM_ID = config.target_id #replace config.target to telegram id of your receiver

    '''
        case-1, send message
    '''
    #print("sendMessage")
    #message = "Good day"
    #await tu.sendMessage(bot, RECEIVER_TELEGRAM_ID, message)

    '''
        Case-2, send photo
    '''
    #print("send photo raw file")
    #image_name = f"./static/kawaii_asian_girl.jpeg" # make sure photo you choose is placed under folder 'static'
    #image_id = await tu.sendPhoto(bot, RECEIVER_TELEGRAM_ID, image_name, return_id = True)

    #print("send photo URL")
    #image_url = f"{CDN}/static/kawaii_asian_girl.jpeg"
    #image_id = await tu.sendPhoto(bot, RECEIVER_TELEGRAM_ID, image_url, return_id = True)

    #print("send photo file_id") # id included below might not work for you due to 
    #_image_id = "AgACAgQAAxkDAAO5ZEjRO_4h0ozAaZTNeHd85rYvFkcAAmqvMRv-00xS62nhWuOgCekBAAMCAANzAAMvBA"
    #image_id = await tu.sendPhoto(bot, RECEIVER_TELEGRAM_ID, _image_id, "kawaii", True)
    #assert _image_id != image_id, f"\n{_image_id}\n{image_id}"
    #print("Returned image id:", image_id)

    '''
        case-3, send video
    '''
    #print("send video raw file")
    #video_name = "./static/pexels-life-on-super-3324257-1920x1080-18fps.mp4"
    #video_id = await tu.sendVideo(bot, RECEIVER_TELEGRAM_ID, video_name, "raw file", True)
    #print("Returned video id", video_id)
    
    #print("send video URL")
    #video_url = f"{CDN}/static/pexels-life-on-super-3324257-1920x1080-18fps.mp4"
    #video_id = await tu.sendVideo(bot, RECEIVER_TELEGRAM_ID, video_url, "URL", True)
    #print("Returned video id", video_id)
    
    #print("send video file_id")
    #video_id = "BAACAgQAAxkDAAPHZEjdgjIpTYcKV0DiFzKkp_a3iw8AAkgEAAI3a0VSZ-MYCql5ZFUvBA"
    #video_id = await tu.sendVideo(bot, RECEIVER_TELEGRAM_ID, video_id, "file id", True)
    #print("Returned video id", video_id)

    '''
        case-4, send document
    '''
    #print("send document raw file")
    #document_name = "./static/01. The A-Z of Programming Languages author Computerworld.pdf"
    #document_id = await tu.sendDocument(bot, RECEIVER_TELEGRAM_ID, document_name, "raw file", True)
    #print("Returned document id", document_id)
    
    #print("send document URL")
    #document_url = f"{CDN}/static/01. The A-Z of Programming Languages author Computerworld.pdf"
    #document_id = await tu.sendDocument(bot, RECEIVER_TELEGRAM_ID, document_url, "URL", True)
    #print("Returned document id", document_id)

    #print("send document file_id")
    #document_id = "BQACAgQAAxkDAAPLZEjpAc2NLcLsow-ZL-N7elVNqKIAAtEDAALFrExSPqW1esNd0wkvBA"
    #document_id = await tu.sendDocument(bot, RECEIVER_TELEGRAM_ID, document_id, "URL", True)
    #print("Returned document id", document_id)

    '''
        case-5, send photo in a group
    '''
    #print("send photo in a group URL")
    #image_1 = f"{CDN}/static/midjourney_blonde.jpeg"
    #image_2 = f"{CDN}/static/midjourney_girl_by_cryingswan_dfjf806-fullview.jpg"
    #image_3 = f"{CDN}/static/midjourney_girl_red-hat-smile.jpeg"
    #media_collection = [
    #    telegram.InputMediaPhoto(media=tu.file_handler(image_1), caption="image 1", filename="midjourney_blonde.jpeg"),
    #    telegram.InputMediaPhoto(media=tu.file_handler(image_2), caption="image 2", filename="midjourney_girl_by_cryingswan_dfjf806-fullview.jpg"),
    #    telegram.InputMediaPhoto(media=tu.file_handler(image_3), caption="image 3", filename="midjourney_girl_red-hat-smile.jpeg"),
    #]
    #res = await tu.sendMediaGroup(bot, RECEIVER_TELEGRAM_ID, media_collection)
    #print(res)
    
    '''
        case-6, send video in a group
    '''
    # change telegram.InputMediaPhoto -> telegram.InputMediaVideo

    '''
        case-7, send document in a group
    '''
    # change telegram.InputMediaPhoto -> telegram.InputMediaDocument

asyncio.run(main())