from telegram.ext import (
    filters,
    CommandHandler,
    ApplicationBuilder as BotApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
)

from tools.mathematix import seconds_to_next_minute
from datetime import time
from bot.handlers import *
from decouple import config


# FIXME: Some cmd_ methods are re-getting accounts, (admin or non-admin commands), do a full check on them, and check if they need changing, (cause we have fastmem of course)


# TODO: disable old caching
# FIXME: Empty Tags in Equalizing
def main(run_webhook: bool = True):
    app = BotApplicationBuilder().token(botman.token).build()
    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("crypto", select_coin_menu))
    app.add_handler(CommandHandler("currency", select_currency_menu))
    app.add_handler(CommandHandler("gold", select_gold_menu))
    app.add_handler(CommandHandler("equalizer", cmd_equalizer))
    app.add_handler(CommandHandler("lang", cmd_switch_language))
    app.add_handler(CommandHandler("useinchannel", cmd_start_using_in_channel))
    app.add_handler(CommandHandler("myplan", cmd_show_my_plan_status))
    app.add_handler(CommandHandler("refresh", cmd_refresh))

    # ADMIN SECTION
    app.add_handler(CommandHandler("god", cmd_admin_login))
    app.add_handler(CommandHandler("add_admin", cmd_add_admin))
    app.add_handler(CommandHandler("rem_admin", cmd_remove_admin))
    app.add_handler(CommandHandler("up", cmd_upgrade_user))
    app.add_handler(CommandHandler("down", cmd_list_users_to_downgrade))
    app.add_handler(CommandHandler("post", cmd_send_post))
    app.add_handler(CommandHandler("newplans", cmd_send_plans_post))
    app.add_handler(CommandHandler("schedule", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("stop", cmd_stop_schedule))
    app.add_handler(CommandHandler("stats", cmd_report_statistics))

    app.add_handler(CallbackQueryHandler(handle_inline_keyboard_callbacks))
    app.add_handler(ChatMemberHandler(handle_new_group_members, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS,
            handle_group_messages,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_messages))
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, handle_multimedia_messages))
    app.add_handler(MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, unknown_command_handler))
    plan_main_channel(app, float(config('MAIN_CHANNEL_DEFAULT_INTERVAL', 10)))
    app.job_queue.run_repeating(botman.process_channels, interval=30, first=seconds_to_next_minute() - 1,
                                name="PLUS_CHANNELS")
    app.job_queue.run_repeating(botman.do_hourly_check, name="DAILY_REFRESH", interval=3600,
                                first=seconds_to_next_period(period_in_minutes=60))
    app.add_error_handler(unhandled_error_happened)

    print("Server is up and running...")
    if not run_webhook:
        app.run_polling(poll_interval=0.2, timeout=10)
    else:
        # Run as webhook
        app.run_webhook(
            listen="0.0.0.0",
            port=botman.bot_port,
            webhook_url=f"{botman.host_url}/{botman.bot_tag}",
            url_path=botman.bot_tag,
        )


if __name__ == "__main__":
    try:
        run_method = config("RUN_METHOD", "webhook")
        main(run_webhook=run_method.lower() == "webhook")
    except Exception as ex:
        print(ex)
        log("Server crashed because: ", ex, "FATALITY")
