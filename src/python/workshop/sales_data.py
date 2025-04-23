import json
import logging
from pathlib import Path
from typing import Optional

import aiosqlite
import pandas as pd

from terminal_colors import TerminalColors as tc
from utilities import Utilities

DATA_BASE = "contoso-sales.db"
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

class SalesData:
    conn: Optional[aiosqlite.Connection]

    def __init__(self) -> None:
        self.conn = None
        self.utilities = Utilities()

    async def connect(self) -> None:
        """
        Connect to the SQLite database, preferring shared/database. Then
        verify the presence of tables and print schema info.
        """
        # Determine database file location
        shared_path = self.utilities.shared_files_path / "database" / DATA_BASE
        local_path = Path(__file__).parent / "database" / DATA_BASE

        if shared_path.exists():
            db_file = shared_path
        elif local_path.exists():
            db_file = local_path
        else:
            raise FileNotFoundError(
                f"Database file not found. Tried: {shared_path} and {local_path}"
            )

        db_uri = f"file:{db_file}?mode=ro"
        try:
            self.conn = await aiosqlite.connect(db_uri, uri=True)
            logger.debug(f"Connected to database at {db_file}")
        except aiosqlite.Error as e:
            logger.exception("Failed to open database", exc_info=e)
            raise

        # Verify available tables and their schema
        try:
            tables = await self._get_table_names()
            print(f"\n{tc.GREEN}Available tables:{tc.RESET} {tables}")
            for tbl in tables:
                cols = await self._get_column_info(tbl)
                print(f"{tc.CYAN}Schema for {tbl}:{tc.RESET} {cols}")
        except Exception as e:
            logger.exception("Error verifying database schema", exc_info=e)

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            logger.debug("Database connection closed.")

    async def _get_table_names(self) -> list[str]:
        """Return a list of user table names."""
        async with self.conn.execute("SELECT name FROM sqlite_master WHERE type='table';") as cursor:
            rows = await cursor.fetchall()
        return [row[0] for row in rows if row[0] != "sqlite_sequence"]

    async def _get_column_info(self, table_name: str) -> list[str]:
        """Return column info tuples as strings."""
        async with self.conn.execute(f"PRAGMA table_info('{table_name}');") as cursor:
            rows = await cursor.fetchall()
        return [f"{r[1]} ({r[2]})" for r in rows]

    async def async_fetch_sales_data_using_sqlite_query(self, sqlite_query: str) -> str:
        """
        Execute a SQLite query and return results as JSON.
        """
        print(f"{tc.BLUE}Executing query: {sqlite_query}{tc.RESET}")
        try:
            async with self.conn.execute(sqlite_query) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

            if not rows:
                return json.dumps([])

            df = pd.DataFrame(rows, columns=columns)
            return df.to_json(index=False, orient="split")

        except Exception as e:
            return json.dumps({"error": str(e), "query": sqlite_query})
