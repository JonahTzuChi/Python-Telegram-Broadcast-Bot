
"""
# case-2, send photo
image_name = "kawaii_asian_girl.jpeg"
USER_TELEGRAM_ID = 75316412
asyncio.run(tu.sendPhoto(bot, USER_TELEGRAM_ID, image_name))

# case-3, send photo by file_id
image_1 = (
    "AgACAgUAAxkDAANOZEdwPMoxw__lBUt5Wgl-vCzicr8AAjW1MRtvGjhWDqzDe-GjbqwBAAMCAANzAAMvBA"
)
USER_TELEGRAM_ID = 75316412
asyncio.run(tu.sendPhotoById(bot, USER_TELEGRAM_ID, image_1))

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
asyncio.run(tu.sendMediaGroup(bot, USER_TELEGRAM_ID, media_collection))
"""
print("END")
