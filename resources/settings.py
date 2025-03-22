plans_fa = """💎 همین حالا اکانت خود را پریمیوم کنید

✅ افزایش لیست مشاهده قیمت از ۱۰ به ۱۰۰ قیمت
✅ افزایش لیست ماشین حساب از ۱۰ به ۱۰۰ قیمت
✅ افزایش هشدار قیمت از ۳ به ۳۰ هشدار
✅ حذف تبلیغات 

⭐️ اضافه کردن ربات به یکی از کانال هایتان
(جهت ارسال قیمت های مدنظرتان طبق زمانبندی دلخواهتان در کانال شما)

⭐️ اضافه کردن ربات به یکی از گروه هایتان
(استفاده مستقیم از قابلیت مشاهده قیمت و ماشین حساب داخل گروه توسط تمام اعضا)

📌 تعرفه ها:
💳 تعرفه ۳۰ روزه: ۵ تتر
💳 تعرفه ۹۰ روزه: ۱۵ تتر
💳 تعرفه ۱۸۰ روزه: ۳۰ تتر
💳 تعرفه ۳۶۵ روزه: ۵۰ تتر

جهت مشاوره و یا تهیه اشتراک کلمه [ پریمیوم ] را برای ادمین پاسخگویی ارسال کنید:
👩‍💻 @KSA_Admin"""

plans_en = """💎 Premium your account now

✅ Increasing the price view list from 10 to 100 prices
✅ Increasing the calculator list from 10 to 100 prices
✅ Increase price warning from 3 to 30 warnings
✅ Remove ads

⭐️ Add a bot to one of your channels
(to send the prices you want according to your desired schedule in your channel)

⭐️ Add a bot to one of your groups
(direct use of price visibility and calculator within the group by all members)

📌 Tariffs:
💳 30 day tariff: 5 USDT
💳 90 day tariff: 15 USDT
💳 180 day tariff: 30 USDT
💳 365 day tariff: 50 USDT

For advice or subscription, send the word [ Premium ] to the administrator:
👩‍💻 @KSA_Admin"""

from tools.manuwriter import fwrite_from_scratch
import json

json_string = json.dumps(
    {
        "premiums_plans_text": {"fa": plans_fa, "FA": plans_en, "en": plans_en},
        "premiums_plans_file_id": {"fa": None, "FA": None, "en": None},
        "rules": {
            "token_selection": {"free": 10, "plus": 100, "admin": 200},
            "calculator_token_selection": {
                "free": 10,
                "plus": 100,
                "admin": 200,
            },
            "community_token_selection": {"free": 10, "plus": 100, "admin": 200},
            "alarm_selection": {"free": 3, "plus": 30, "admin": 100},
        },
    }
)

fwrite_from_scratch('settings', json_string)