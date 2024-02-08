from datetime import datetime
import os
from tools.mathematix import timezone


LOG_FOLDER_PATH = 'logs'
def prepare_folder(folder_path):
    # Check if the folder exists
    if not os.path.exists(folder_path):
        # Create the folder if it doesn't exist
        os.makedirs(folder_path)


def log(msg, exception=None, category_name=None):
    ts = datetime.now(tz=timezone)
    content = ts.strftime('%Y-%m-%d %H:%M:%S')
    log_folder_path = LOG_FOLDER_PATH
    if exception:
        content = f'{content}\t->\tSHIT: {msg}\n\t\tX: {exception}'
    else:
        content += f'\t->\t{msg}'
    try:
        prepare_folder(LOG_FOLDER_PATH)
    except:
        log_folder_path = ''
    suffix = 'fux' if (not category_name) or ('info' not in category_name.lower()) else 'sux'
    log_file_name = f'total.{suffix}' if not category_name else f'{category_name}.{suffix}'
    logfile = open(f'./{log_folder_path}/{log_file_name}', 'a')
    logfile.write(content + "\n\n")
    logfile.close()
