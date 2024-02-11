from datetime import datetime
import pytz
from persiantools import digits
from dateutil.relativedelta import relativedelta


timezone = pytz.timezone('Asia/Tehran')

def separate_by3(number: float, precision: int=None):
    return f"{number:,.{precision}f}" if precision else f'{number:,}'


def cut(number: float|int, return_string: bool=False):
    intnum = int(number)
    if intnum == number or intnum >= 1000:
        return str(intnum) if return_string else intnum, 0

    strnum = str(number)
    if 'e' in strnum:
        strnum = f"{number:.16f}"
    if '.' not in strnum:  # just to double-check
        return strnum if return_string else int(strnum), 0

    dot_index = strnum.index('.')
    end = len(strnum)

    if number >= 10:  # limit number to two digits after .
        if dot_index + 3 <= end:
            end = dot_index + 3
    elif number >= 1:  # limit number to four digits after .
        if dot_index + 5 <= end:
            end = dot_index + 5

    ei = dot_index + 1
    while ei < end and strnum[ei] == '0':
        ei += 1
    if ei >= end:
        return str(intnum) if return_string else intnum, 0
    if number >= 1:
        if ei >= end:  # no meaning zeros
            return intnum, 0
        return strnum[:end] if return_string else float(strnum[:end]), end - dot_index - 1

    # num < 1 => write till 4 digits after the first zero after .
    end -= 1
    if ei + 3 <= end:
        end = ei + 3
    while end > ei and strnum[end] == '0':
        end -= 1

    return strnum[:end + 1] if return_string else float(strnum[:end + 1]), end - dot_index


def persianify(number: str|float|int):
    if not isinstance(number, str):
        number = str(number)
    return digits.en_to_fa(number)  #.replace('.', '/').replace(',', '،')

def cut_and_separate(num: float|int):
    num, precision = cut(num)

    return  separate_by3(num, precision)



def tz_today() -> datetime:  # today date in a specific timezone
    return datetime.now(tz=timezone)

WEEKDAYS = ('دوشنبه', 'سه شنبه', 'چهارشنبه', 'پنج شنبه', 'جمعه', 'شنبه', 'یکشنبه')

def timestamp() -> str:
    # today date and time as persian
    try:
        now = tz_today()  # timezone.localize(datetime.now())
        year, month, day = gregorian_to_jalali(now.year, now.month, now.day)
        weekday = WEEKDAYS[now.weekday()]
        date = digits.en_to_fa(f'{year}/{month:02d}/{day:02d}')
        time = digits.en_to_fa(now.strftime("%H:%M"))
        return f'📆 {date} {weekday} {time}'

    except Exception as ex:
        print('Calculating jalili date and time encountered with error: ', ex)
        try:
            now = tz_today()  # timezone.localize(datetime.now())
            return f'📆 {now.year}/{now.month:02d}/{now.day:02d} {weekday} {now.strftime("%H:%M")}'
        except:
            return 'تاریخ نامعلوم: دریافت تاریخ روز با مشکل مواجه شد!'


def short_timestamp(date_delimiter='-', time_delimiter='.', datetime_delimiter='_', show_minutes: bool=False) -> str:
    # today date and time as persian
    try:
        now = tz_today()  # timezone.localize(datetime.now())
        year, month, day = gregorian_to_jalali(now.year, now.month, now.day)

        time = now.strftime(f"%H{time_delimiter}%M")
        return f'{year}{date_delimiter}{month:02d}{date_delimiter}{day:02d}{datetime_delimiter}{time}'

    except Exception as ex:
        now = tz_today()  # timezone.localize(datetime.now())
        return f'{now.year}{date_delimiter}{now.month:02d}{date_delimiter}{now.day:02d}{datetime_delimiter}{now.strftime("%H" if not show_minutes else f"%H{time_delimiter}%M")}'
    return None

def gregorian_to_jalali(gy: int, gm: int, gd: int):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gm > 2:
        gy2 = gy + 1
    else:
        gy2 = gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int):
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += ((days - 1) // 365)
        days = (days - 1) % 365
    gd = days + 1
    if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
        kab = 29
    else:
        kab = 28
    sal_a = [0, 31, kab, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


def extend_date(date:datetime, months_count: int) -> datetime:
    return date + relativedelta(months=months_count)


def after_n_months(n: int = 2) -> datetime:
    # this is used for vip end date calculation
    return extend_date(date=datetime.now(), months_count=n)


if __name__ == "__main__":
    d = datetime.today()
    j = gregorian_to_jalali(d.year, d.month, d.day)

    while True:
        x = float(input("> "))
        print("\t=> ", cut_and_separate(x))
