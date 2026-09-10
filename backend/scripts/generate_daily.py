"""Manually generate or recover a Daily Discovery collection."""

import argparse
from datetime import date

from database.db import create_session_local
from services.daily_generation_service import DailyGenerationService, application_date


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Daily Discovery content")
    parser.add_argument("--date", dest="discovery_date", help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    discovery_date = date.fromisoformat(args.discovery_date) if args.discovery_date else application_date()

    session = create_session_local()()
    try:
        result = DailyGenerationService(session).generate_daily_discovery(discovery_date)
        print(
            f"{result.discovery_date}: {result.status}; "
            f"{len(result.discoveries)} discoveries; "
            f"failed={','.join(result.failed_categories) or 'none'}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()