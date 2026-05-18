import psycopg2
import logging
from config import DB_CONFIG

logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def setup_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS malaria_indicators (
                id             SERIAL PRIMARY KEY,
                indicator_code VARCHAR(50)  NOT NULL,
                country_code   CHAR(3)      NOT NULL,
                region         VARCHAR(100),
                year           INT          NOT NULL,
                sex            VARCHAR(10),
                value          NUMERIC,
                low_value      NUMERIC,
                high_value     NUMERIC,
                loaded_at      TIMESTAMP    DEFAULT NOW(),
                UNIQUE (indicator_code, country_code, year, sex)
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id               SERIAL PRIMARY KEY,
                indicator_code   VARCHAR(50) NOT NULL,
                last_year_loaded INT,
                rows_loaded      INT,
                status           VARCHAR(20),
                run_at           TIMESTAMP   DEFAULT NOW()
            );
        """)
        conn.commit()
    logger.info("Schema ready.")