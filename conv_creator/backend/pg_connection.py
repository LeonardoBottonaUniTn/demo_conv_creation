"""Helpers for direct PostgreSQL access via psycopg2."""
import psycopg2
from dotenv import load_dotenv
import os

# Ensure DATABASE_URL is available even if the module is executed standalone.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")




def get_pg_connection() -> psycopg2.extensions.connection:
    """Return a psycopg2 connection to the Supabase Postgres instance."""
    # Load environment variables from .env
    load_dotenv()

    # Fetch variables
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Connect to the database
    connection = psycopg2.connect(DATABASE_URL)
    return connection