"""
extract_tables_to_csv.py

Connects to a SQL Server database via pymssql and exports every user table
into its own CSV file. 

Usage:
    python extract_tables_to_csv.py

Requires:
    pip install pymssql pandas python-dotenv
"""

import os
import pymssql
import pandas as pd
from dotenv import load_dotenv


load_dotenv()  

DB_SERVER = os.getenv("DB_SERVER", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 1433))
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD") 
DB_NAME = os.getenv("DB_NAME", "AdventureWorksDW2025")

OUTPUT_DIR = "data/raw"  


SCHEMAS_TO_INCLUDE = ["dbo"]


def get_connection():
    """Open a pymssql connection to the target database."""
    if not DB_PASSWORD:
        raise ValueError(
            "DB_PASSWORD is not set. Add it to a .env file, e.g.:\n"
            "DB_PASSWORD=YourStr0ngPass!"
        )
    return pymssql.connect(
        server=DB_SERVER,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


def get_table_list(conn):
    """Return a list of (schema, table_name) tuples for all base tables."""
    query = """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    tables_df = pd.read_sql(query, conn)

    if SCHEMAS_TO_INCLUDE:
        tables_df = tables_df[tables_df["TABLE_SCHEMA"].isin(SCHEMAS_TO_INCLUDE)]

    return list(zip(tables_df["TABLE_SCHEMA"], tables_df["TABLE_NAME"]))


def export_table_to_csv(conn, schema, table_name, output_dir):
    """Read a single table into a DataFrame and write it to CSV."""
    query = f"SELECT * FROM [{schema}].[{table_name}]"
    df = pd.read_sql(query, conn)

    filename = f"{table_name}.csv"
    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False)

    print(f"  -> {filepath} ({len(df):,} rows, {len(df.columns)} columns)")
    return filepath


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Connecting to {DB_NAME} on {DB_SERVER}:{DB_PORT} ...")
    conn = get_connection()

    try:
        tables = get_table_list(conn)
        print(f"Found {len(tables)} table(s) to export.\n")

        exported_files = []
        for schema, table_name in tables:
            print(f"Exporting {schema}.{table_name} ...")
            try:
                filepath = export_table_to_csv(conn, schema, table_name, OUTPUT_DIR)
                exported_files.append(filepath)
            except Exception as e:
                print(f"  ! Failed to export {schema}.{table_name}: {e}")

        print(f"\nDone. {len(exported_files)}/{len(tables)} table(s) exported to '{OUTPUT_DIR}/'.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
