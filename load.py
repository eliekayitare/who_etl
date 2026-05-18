import logging
import psycopg2.extras
from typing import Optional

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def upsert_records(conn, records: list[dict]) -> int:
    """
    Upsert records into malaria_indicators.
    Runs inside a single transaction — if anything fails, rolls back completely.
    Returns the number of rows actually written (inserted or updated).
    Rows skipped because nothing changed are not counted.
    """
    if not records:
        logger.warning("upsert_records called with empty list — nothing to do.")
        return 0

    sql = """
        INSERT INTO malaria_indicators (
            indicator_code, country_code, region,
            year, sex, value, low_value, high_value
        ) VALUES (
            %(indicator_code)s, %(country_code)s, %(region)s,
            %(year)s, %(sex)s, %(value)s, %(low_value)s, %(high_value)s
        )
        ON CONFLICT (indicator_code, country_code, year, sex)
        DO UPDATE SET
            value      = EXCLUDED.value,
            low_value  = EXCLUDED.low_value,
            high_value = EXCLUDED.high_value,
            loaded_at  = NOW()
        WHERE
            malaria_indicators.value      IS DISTINCT FROM EXCLUDED.value
            OR malaria_indicators.low_value  IS DISTINCT FROM EXCLUDED.low_value
            OR malaria_indicators.high_value IS DISTINCT FROM EXCLUDED.high_value;
    """

    rows_written = 0
    try:
        with conn.cursor() as cur:
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i : i + BATCH_SIZE]
                psycopg2.extras.execute_batch(cur, sql, batch, page_size=BATCH_SIZE)
                rows_written += cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        logger.error("Load failed — transaction rolled back.")
        raise

    logger.info(
        f"Upserted into malaria_indicators: "
        f"{rows_written} rows written / {len(records)} records processed"
    )
    return rows_written


def record_pipeline_run(
    conn,
    indicator_code: str,
    last_year_loaded: Optional[int],
    rows_loaded: int,
    status: str,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_runs
                (indicator_code, last_year_loaded, rows_loaded, status)
            VALUES (%s, %s, %s, %s)
            """,
            (indicator_code, last_year_loaded, rows_loaded, status),
        )
        conn.commit()
    logger.info(f"Recorded pipeline run: {indicator_code} | {status} | {rows_loaded} rows")


def get_last_loaded_year(conn, indicator_code: str) -> Optional[int]:
    """
    Return the highest year successfully loaded for this indicator,
    or None if no successful run exists yet.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT last_year_loaded
            FROM   pipeline_runs
            WHERE  indicator_code = %s AND status = 'success'
            ORDER  BY run_at DESC
            LIMIT  1
            """,
            (indicator_code,),
        )
        row = cur.fetchone()
    return row[0] if row else None