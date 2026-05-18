from decouple import config

# ---------------------------------------------------------------------------
# API constants — safe to expose, no secrets here
# ---------------------------------------------------------------------------

GHO_BASE_URL = "https://ghoapi.azureedge.net/api"

# To add a new indicator, append its code here.
# The rest of the pipeline picks it up automatically.
INDICATORS = ["MALARIA_EST_CASES", "MALARIA_EST_DEATHS"]

# WHO API supports up to 1000 records per page
PAGE_SIZE = 1000

# Pause between paginated requests — avoids overwhelming the API
REQUEST_DELAY = 0.2

# ---------------------------------------------------------------------------
# Database config — all values come from .env, never hardcoded
# ---------------------------------------------------------------------------
# config("DB_PASSWORD") with no default means it is REQUIRED.
# If missing, decouple raises UndefinedValueError immediately at startup.

DB_CONFIG = {
    "host":     config("DB_HOST",     default="localhost"),
    "port":     config("DB_PORT",     default=5432, cast=int),
    "dbname":   config("DB_NAME",     default="who_health"),
    "user":     config("DB_USER",     default="postgres"),
    "password": config("DB_PASSWORD"),
}