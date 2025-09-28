import asyncio
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger

from contramate.dbs.interfaces.metadata_store import AbstractMetadataStore
from contramate.utils.settings.core import PostgresSettings


class PostgresMetadataAdapter(AbstractMetadataStore):
    """PostgreSQL adapter for structured metadata queries."""

    def __init__(self, settings: PostgresSettings):
        self.settings = settings

    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(
            self.settings.connection_string,
            cursor_factory=RealDictCursor
        )

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dictionaries."""
        def _execute():
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)

                        results = cursor.fetchall()
                        return [dict(row) for row in results]
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                raise

        return await asyncio.get_event_loop().run_in_executor(None, _execute)

    async def execute_query_single(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a SQL query and return single result or None."""
        def _execute():
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)

                        result = cursor.fetchone()
                        return dict(result) if result else None
            except Exception as e:
                logger.error(f"Error executing single query: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                raise

        return await asyncio.get_event_loop().run_in_executor(None, _execute)

    async def execute_query_scalar(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a SQL query and return single scalar value."""
        def _execute():
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)

                        result = cursor.fetchone()
                        return result[0] if result else None
            except Exception as e:
                logger.error(f"Error executing scalar query: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                raise

        return await asyncio.get_event_loop().run_in_executor(None, _execute)

    async def health_check(self) -> bool:
        """Check if the metadata store connection is healthy."""
        try:
            result = await self.execute_query_scalar("SELECT 1")
            return result == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False