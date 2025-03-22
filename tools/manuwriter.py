from datetime import datetime
import os
from tools.mathematix import timezone, short_timestamp
import json
import traceback
import sys


LOG_FOLDER_PATH = "logs"


def prepare_folder(folder_path):
    # Check if the folder exists
    main_folder_created = True
    if not os.path.exists(folder_path):
        # Create the folder if it doesn't exist
        os.makedirs(folder_path)
        return main_folder_created
    return main_folder_created

def prepare_folder_with_subs(folder_path, sub_folder_path=None):
    # Check if the folder exists
    main_folder_created, sub_folder_created = True, True
    if not os.path.exists(folder_path):
        # Create the folder if it doesn't exist
        os.makedirs(folder_path)
        if sub_folder_path:
            try:  # This is for cache section; cache sub folder is for archiving and it's not important as the main folder itself
                # so the function just informs the caller of its existence/creation_status, so if it was ok the caller will use it as an archive place, o.w it ignores this archiving section
                os.makedirs(f"./{folder_path}/{sub_folder_path}")
            except:
                sub_folder_created = False
        return main_folder_created, sub_folder_created
    if sub_folder_path:
        subfp = f"./{folder_path}/{sub_folder_path}"
        if not os.path.exists(subfp):
            try:
                os.makedirs(subfp)
            except:
                sub_folder_created = False
    return main_folder_created, sub_folder_created


# FIXME: This log system is so basic; create a Log class, and LogType enum and you know what else.
def log(msg, exception: Exception=None, category_name=None):
    ts = datetime.now(tz=timezone)
    content = ts.strftime("%Y-%m-%d %H:%M:%S")
    log_folder_path = LOG_FOLDER_PATH
    if exception:
        ex_info = '\n\t\t\t\t\t'.join(traceback.format_exception(*sys.exc_info()))
        content = f"{content}\t->\tSHIT: {msg}\n\t\tX: {exception}\n\t\t\t{ex_info}"
    else:
        content += f"\t->\t{msg}"
    try:
        prepare_folder(LOG_FOLDER_PATH)
    except:
        log_folder_path = ""
    suffix = (
        "fux" if (not category_name) or ("info" not in category_name.lower()) else "sux"
    )
    log_file_name = (
        f"total.{suffix}" if not category_name else f"{category_name}.{suffix}"
    )
    logfile = open(f"./{log_folder_path}/{log_file_name}", "a")
    logfile.write(
        "%s\t=>\t%s\n%s\n"
        % (
            short_timestamp(
                time_delimiter=":", datetime_delimiter="\t", show_minutes=True
            ),
            content,
            '=' * 40
        )
    )
    logfile.close()


def fwrite_from_scratch(fpath: str, fdata: str, source: str = None) -> bool:
    try:
        f = open(fpath, "w")
        f.write(fdata)
        f.close()
    except Exception as ex:
        data_trunc = fdata[:20] if len(fdata) > 20 else fdata
        log(f"File write failure; filename: {fpath}, data: {data_trunc}", ex, source)
        return False
    return True


def load_json(json_filename: str, parent_folder: str = "."):
    if json_filename[-5:] != ".json":
        json_filename = f"{json_filename}.json"
    str_json: str = "{}"
    try:
        json_file = open(f"./{parent_folder}/{json_filename}", "r")
        str_json = json_file.read()
        json_file.close()
    except:
        return None
    return json.loads(str_json)


def random_string(
    length: int,
    capital_case: bool = True,
    lower_case: bool = False,
    *signs_or_special_chars,
) -> str:
    """Generate a random meaningless string. by default its just upper and lowercase characters. if there's any sign needed, they can be added as extra params to function call.
    for increasing the possibility of occurring a sign/character in string multiply it by a int like: random_text(15, True, False, ':' * 5, 's' * 4, ' ' * 10)
    """
    from random import randint

    characters = "abcdefghijklmnopqrstuvwxyz"
    if signs_or_special_chars:
        characters += "".join(signs_or_special_chars)
    while len(characters) < length:
        characters *= 2
    chars_count = len(characters)
    res = ""
    for _ in range(length if length < chars_count else chars_count):
        rnd = randint(0, chars_count - 1)
        lwr = lower_case or randint(0, 10) >= 5
        res += characters[rnd] if lwr else characters[rnd].upper()

    if not lower_case and capital_case and (res[0] >= "a" or res[0] <= "z"):
        return f"{res[0].upper()}{res[1:]}"
    return res.capitalize() if capital_case else res


def archive_price_data(
    cache_folder: str,
    archive_subfolder: str,
    filename: str,
    price_data_json: str,
    data_tag: str,
):
    fwrite_from_scratch(
        "./%s/%s/%s_%s.json"
        % (cache_folder, archive_subfolder, filename, short_timestamp()),
        price_data_json,
        data_tag,
    )
