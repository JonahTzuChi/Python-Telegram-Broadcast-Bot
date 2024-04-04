import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    AIORateLimiter,
    filters,
    CallbackQueryHandler,
)

import config

import handlers

# setup logging
logging.basicConfig(
    filename=f"/error/worker_{config.bot_id}.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.worker)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .post_init(handlers.post_init)
        .build()
    )

    sysadmin_filter = filters.ALL
    if len(config.sysadmin_tid) > 0:
        sysadmin_filter = filters.User(user_id=config.sysadmin_tid)

    # regular-admin
    application.add_handler(MessageHandler(filters.ALL, handlers.middleware_function), group=0)
    application.add_handler(CommandHandler("start", handlers.start_handler), group=1)
    application.add_handler(CommandHandler("broadcast", handlers.try_broadcast_handler), group=1)
    application.add_handler(CommandHandler("upload", handlers.add_file_type_handle), group=1)
    application.add_handler(CommandHandler("release", handlers.release_handler), group=1)
    application.add_handler(CommandHandler("help", handlers.help_handler), group=1)
    application.add_handler(CommandHandler("count_subscribers", handlers.query_nos_button), group=1)
    application.add_handler(CommandHandler("export", handlers.export_subscribers_button), group=1)

    application.add_handler(CommandHandler("weather", handlers.wapi), group=1)
    application.add_handler(CommandHandler("photo", handlers.get_photo), group=1)
    application.add_handler(CommandHandler("video", handlers.get_video), group=1)
    application.add_handler(CommandHandler("document", handlers.get_document), group=1)
    application.add_handler(CommandHandler("reset_file_tracking", handlers.clearTaskLog), group=1)
    
    # sys-admin
    application.add_handler(CommandHandler("delete_log", handlers.empty_log, filters=sysadmin_filter), group=1)
    application.add_handler(CommandHandler("delete_data", handlers.empty_data, filters=sysadmin_filter), group=1)
    application.add_handler(CommandHandler("grant", handlers.grant_handler, filters=sysadmin_filter), group=1)
    application.add_handler(CommandHandler("revoke", handlers.revoke_handler, filters=sysadmin_filter), group=1)
    application.add_handler(
        CommandHandler("show_superuser", handlers.list_superuser_handler, filters=sysadmin_filter),
        group=1
    )
    application.add_handler(
        CommandHandler("export_full", handlers.export_subscribers_full_button, filters=sysadmin_filter),
        group=1
    )
    application.add_handler(
        CommandHandler("upload_subscriber_list", handlers.set_upload_subscriber_handler, filters=sysadmin_filter),
        group=1
    )
    application.add_handler(MessageHandler(filters.TEXT, handlers.message_handler), group=1)
    application.add_handler(MessageHandler(filters.ATTACHMENT, handlers.attachment_handler), group=1)
    
    # callback
    application.add_handler(CallbackQueryHandler(handlers.set_broadcast_mode_handler, pattern="^set_broadcast_mode"))
    application.add_handler(CallbackQueryHandler(handlers.set_file_type_handle, pattern="^set_file_type"))
    application.add_error_handler(handlers.error_handler)
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
