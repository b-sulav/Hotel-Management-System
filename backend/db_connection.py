import os
import logging
import mysql.connector
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

def _read_secret(name: str, env_var: str) -> str:
    """Read secret from file (Docker secrets) or environment variable."""
    secret_path = f"/run/secrets/{name}"
    if os.path.exists(secret_path):
        with open(secret_path, "r") as f:
            return f.read().strip()
    return os.getenv(env_var, "")

db_host = os.getenv("DB_HOST", "localhost")
db_port_raw = os.getenv("DB_PORT", "3306")
db_user = os.getenv("DB_USER")
db_password = _read_secret("db_app_password", "DB_PASSWORD")
db_name = os.getenv("DB_NAME")

# Validate required
missing_vars = [
    name
    for name, val in [
        ("DB_USER", db_user),
        ("DB_PASSWORD", db_password),
        ("DB_NAME", db_name),
    ]
    if not val
]
if missing_vars:
    raise ValueError(
        f"Missing required environment variable(s): {', '.join(missing_vars)}. "
        "Set them in your .env file or environment before starting."
    )

# Reject root
if db_user == "root":
    raise ValueError(
        "DB_USER=root is not permitted. Create a least-privilege MySQL user and "
        "update DB_USER. The 'resort_app' user should be used in production."
    )

# Parse optional
try:
    db_port = int(db_port_raw)
except ValueError:
    logger.warning("Invalid DB_PORT value '%s'; defaulting to 3306.", db_port_raw)
    db_port = 3306

try:
    connection_pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
    if not (1 <= connection_pool_size <= 32):
        raise ValueError("Pool size out of range")
except ValueError:
    logger.warning("Invalid DB_POOL_SIZE; defaulting to 10.")
    connection_pool_size = 10

# Lazy Connection
_pool = None

def get_db_pool():
    global _pool
    if _pool is None:
        try:
            _pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="resort_pool",
                pool_size=connection_pool_size,
                pool_reset_session=True,
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                autocommit=False,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                connection_timeout=10,
            )
            logger.info(
                "Database connection pool initialised (host=%s:%d, db=%s, pool_size=%d).",
                db_host,
                db_port,
                db_name,
                connection_pool_size,
            )
        except mysql.connector.Error as e:
            logger.critical("Failed to initialise database pool: %s", e)
            raise
    return _pool


def get_db_connection():
    """Return a connection from the pool. Caller is responsible for closing it."""
    pool = get_db_pool()
    return pool.get_connection()