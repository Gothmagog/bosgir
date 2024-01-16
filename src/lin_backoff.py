import time
import botocore.exceptions
import logging

retry_codes = ["throttlingException"]

def lin_backoff(func, status_win, *args, **kwargs):
    retry = True
    retry_seconds = 0
    ret = None
    while retry:
        try:
            retry_seconds += 10
            ret = func(*args, **kwargs)
            retry = False
        except botocore.exceptions.EventStreamError as e:
            error = e.response.get("Error", {})
            code = error.get("Code", "Unknown")
            if code in retry_codes:
                cur_second = 0
                while cur_second < retry_seconds:
                    if status_win:
                        status_win.erase()
                        status_win.addstr(0, 0, f"Received {code} error, waiting to retry in {retry_seconds - cur_second}...")
                        status_win.refresh()
                    time.sleep(1)
                    cur_second += 1
            else:
                raise e
    return ret
