# WHO Malaria ETL Pipeline

A Python pipeline that pulls estimated malaria data from the
[WHO GHO API](https://www.who.int/data/gho/info/gho-odata-api),
validates it, and loads it into PostgreSQL.

---

## Indicators

| Code | Description |
|---|---|
| `MALARIA_EST_CASES` | Estimated malaria cases per country per year |
| `MALARIA_EST_DEATHS` | Estimated malaria deaths per country per year |

Covers 195 countries from 2000 to 2024.

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/eliekayitare/who_etl.git
cd who_etl
```

### 2. Create and activate a virtual environment

**Linux / macOS**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows**
```bash
python -m venv venv
.\venv\Scripts\Activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure credentials
```bash
cp .env.example .env
```

Open `.env` and fill in your PostgreSQL credentials:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=who_health
DB_USER=postgres
DB_PASSWORD=your_password
```

### 5. Create the database

Run this in pgAdmin or psql:
```sql
CREATE DATABASE who_health;
```

Tables are created automatically on first run.

---

## Running the Pipeline

```bash
# Incremental — only fetches data newer than the last run
python pipeline.py

# Full reload
python pipeline.py --full

# Single indicator
python pipeline.py --indicator MALARIA_EST_CASES
```

---

## Running Tests

```bash
pytest tests/ -v
```

13 tests covering validation and normalisation logic.

---

## How It Works

**Incremental loads** — after each run the pipeline saves the last year
loaded. Next run it only fetches newer data. Use `--full` to reload
everything.

**Safe re-runs** — upsert logic ensures re-running never creates
duplicate rows. Rows that have not changed are not touched.

**Transaction safety** — all writes happen in one transaction. If
something fails, the database rolls back completely.

**Validation** — bad rows are logged with a reason and skipped. One
bad row never crashes the entire run.

**Retries** — network failures are retried up to 3 times with
exponential backoff before giving up.

---

## What I Would Improve With More Time

- **Automated scheduling** — use Celery with Redis as the message
  broker to schedule pipeline runs as background tasks on a timer,
  with built-in retries and task monitoring. For larger deployments,
  wrap the pipeline in an Airflow DAG or Prefect flow for SLA
  monitoring and failure alerting via email or Slack.
- **Parallel extraction** — fetch multiple indicators concurrently
  to reduce total run time.
- **Schema versioning** — use Alembic instead of
  `CREATE TABLE IF NOT EXISTS` for proper migration management.
- **Docker Compose** — one command to spin up PostgreSQL, Redis,
  and the pipeline together.
- **Run summary report** — emit a structured JSON report per run
  showing rows loaded, drop rate, and year range.