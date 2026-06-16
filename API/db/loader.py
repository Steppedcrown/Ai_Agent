import os
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse


def get_conn():
    """Return a new psycopg2 connection using DATABASE_URL."""
    url = os.environ["DATABASE_URL"]
    parsed = urlparse(url)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
