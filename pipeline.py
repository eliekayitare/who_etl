"""
WHO Malaria ETL Pipeline — Entry point.

Usage:
    python pipeline.py                            # incremental (default)
    python pipeline.py --full                     # force full reload
    python pipeline.py --indicator MALARIA_EST_CASES  # single indicator
"""

import argparse
import logging
import sys
from typing import List, Optional

from config import INDICATORS
from db import get_connection, setup_schema
from extract import fetch_indicator
from transform import transform_records
from load import upsert_records, record_pipeline_run, get_last_loaded_year

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pipeline")


def run(incremental: bool = True, indicators: Optional[List[str]] = None):
    targets = indicators or INDICATORS
    logger.info(f"Pipeline starting | indicators={targets} | incremental={incremental}")

    conn = get_connection()
    try:
        setup_schema(conn)
        for indicator in targets:
            _run_indicator(conn, indicator, incremental)
    finally:
        conn.close()

    logger.info("Pipeline finished.")


def _run_indicator(conn, indicator: str, incremental: bool):
    logger.info(f"{'─' * 50}")
    logger.info(f"Processing: {indicator}")

    since_year = None
    if incremental:
        since_year = get_last_loaded_year(conn, indicator)
        if since_year:
            logger.info(f"Incremental mode: fetching records with year > {since_year}")
        else:
            logger.info("No previous run found — performing full load")

    status = "success"
    rows_loaded = 0
    last_year = None

    try:
        raw_records   = fetch_indicator(indicator, since_year=since_year)
        clean_records = transform_records(raw_records, indicator)
        rows_loaded   = upsert_records(conn, clean_records)

        if clean_records:
            last_year = max(r["year"] for r in clean_records)

    except Exception as exc:
        logger.error(f"Pipeline failed for {indicator}: {exc}", exc_info=True)
        status = "failed"

    record_pipeline_run(conn, indicator, last_year, rows_loaded, status)
    logger.info(f"Done: {indicator} | status={status} | rows={rows_loaded} | last_year={last_year}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WHO Malaria ETL Pipeline")
    parser.add_argument("--full", action="store_true", help="Force full reload")
    parser.add_argument("--indicator", metavar="CODE", help="Run a single indicator")
    args = parser.parse_args()

    selected = [args.indicator] if args.indicator else None
    run(incremental=not args.full, indicators=selected)