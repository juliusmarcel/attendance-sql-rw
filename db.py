import pyodbc
import os
from dotenv import load_dotenv

from contextlib import contextmanager

load_dotenv()


@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = get_connection()
        yield conn
    except Exception as e:
        print(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_connection():
    conn = pyodbc.connect(
        f"DRIVER={os.getenv('DB_DRIVER')};"
        f"SERVER={os.getenv('DB_SERVER')};"
        f"DATABASE={os.getenv('DB_NAME')};"
        f"UID={os.getenv('DB_USER')};"
        f"PWD={os.getenv('DB_PASSWORD')};"
    )
    return conn