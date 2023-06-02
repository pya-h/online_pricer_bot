from datetime import datetime
import pytz


def separate_by3(number):
    return f"{number:,}"

def cut(number):
    if int(number) == number:
        return int(number), 0
    strnum = str(number)
    if 'e' in strnum:
        strnum = f"{number:.16f}"

    if not '.' in strnum:  # just to double check
        return int(strnum), 0

    dot_index = strnum.index('.')
    ei = dot_index + 1
    end = len(strnum)
    while ei < end and strnum[ei] == '0':
        ei += 1

    if ei + 2 <= end:
        return float(strnum[:ei + 2]), ei + 1 - dot_index
    elif ei + 1 <= end:
        return float(strnum[:ei + 1]), ei - dot_index
    return int(strnum[:dot_index + 1]), 0

def cut_and_separate(num):
    num, precision = cut(num)
    res = str(num)
    # or CHECK IF PRECISION > 5
    if not precision or not 'e' in res:
        return separate_by3(num)
    # if res is in scientific notion:
    res = f"{num:,.16f}"
    i = len(res) - 1
    while i >= 0 and (res[i] == "0" or res[i] == ","):
        i -= 1
    return res[:i + 1]

WEEKDAYS = ('دوشنبه', 'سه شنبه', 'چهارشنبه', 'پنج شنبه', 'جمعه', 'شنبه', 'یکشنبه')
timezone = pytz.timezone('Asia/Tehran')

def timestamp() -> str:
    # today date and time as persian
    try:
        now = datetime.now(tz=timezone) # timezone.localize(datetime.now())
        year, month, day = gregorian_to_jalali(now.year, now.month, now.day)
        weekday = WEEKDAYS[now.weekday()]

        return f'📆 تاریخ: {weekday}، {year}/{month}/{day}\n⏰ ساعت: {now.strftime("%H:%M")}'

    except Exception as ex:
        print('Calculating jalili date and time encountered with error: ', ex)
        try:
            now = datetime.now(tz=timezone) # timezone.localize(datetime.now())
            return f'📆 تاریخ: {weekday}، {now.year}/{now.month}/{now.day}\n⏰ ساعت: {now.strftime("%H:%M")}'
        except:
            return 'تاریخ نامعلوم: دریافت تاریخ روز با مشکل مواجه شد!'

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if (gm > 2):
        gy2 = gy + 1
    else:
        gy2 = gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if (days > 365):
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if (days < 186):
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return (jy, jm, jd)


def jalali_to_gregorian(jy, jm, jd):
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if (jm < 7):
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if (days > 36524):
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if (days >= 365):
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if (days > 365):
        gy += ((days - 1) // 365)
        days = (days - 1) % 365
    gd = days + 1
    if ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        kab = 29
    else:
        kab = 28
    sal_a = [0, 31, kab, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while (gm < 13 and gd > sal_a[gm]):
        gd -= sal_a[gm]
        gm += 1
    return (gy, gm, gd)

def log(msg, exception=None):
    ts = datetime.now(tz=timezone)
    content = ts.strftime('%Y-%m-%d %H:%M:%S')
    if exception:
        content = f'{content}\t->\tSHIT: {msg}\n\t\tX: {exception}'
    else:
        content += f'\t->\t{msg}'
    logfile = open('logs.fux', 'a')
    logfile.write(content + "\n\n")
    logfile.close()

if __name__ == "__main__":
    d = datetime.today()
    j = gregorian_to_jalali(d.year, d.month, d.day)

    while True:
        x = float(input("> "))
        print("\t=> ", cut_and_separate(x))


