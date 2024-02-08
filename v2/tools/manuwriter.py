from datetime import datetime
import os
from tools.mathematix import timezone, short_timestamp


LOG_FOLDER_PATH = 'logs'
def prepare_folder(folder_path, sub_folder_path=None):
    # Check if the folder exists
    main_folder_created, sub_folder_created = True, True
    if not os.path.exists(folder_path):
        # Create the folder if it doesn't exist
        os.makedirs(folder_path)
        if sub_folder_path:
            try: # This is for cache section; cache subfolder is for archiving and its not impoortant asthe main foldert itself
                # so the function just inforns the caller of its existence/creation_status, so if it was ok the caller will use it as an archive place, o.w it ignores this archiving section
                os.makedirs(f'./{folder_path}/{sub_folder_path}')
            except:
                sub_folder_created = False
        return main_folder_created, sub_folder_created
    if sub_folder_path:
        subfp = f'./{folder_path}/{sub_folder_path}'
        if not os.path.exists(subfp):
            try:
                os.makedirs(subfp)
            except:
                sub_folder_created = False
    return main_folder_created, sub_folder_created


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
    logfile.write('%s\t=>\t%s\n\n' % (short_timestamp(time_delimiter=':', datetime_delimiter='\t'), content))
    logfile.close()


def fwrite_from_scratch(fpath: str, fdata: str, source: str=None) -> bool:
    try:
        f = open(fpath, 'w')
        f.write(fdata)
        f.close()
    except Exception as ex:
        data_trunc = fdata[:20] if len(fdata) > 20 else fdata
        log(f'File write failure; filename: {fpath}, data: {data_trunc}', ex, source)
        return False
    return True
