"""Run the Daily Discovery scheduler as a standalone process."""

import time

from database.db import create_session_local
from scheduler.daily import create_scheduler


def main() -> None:
    scheduler = create_scheduler(create_session_local())
    scheduler.start()
    print("Daily Discovery scheduler started; daily generation runs at 00:05 local time.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()