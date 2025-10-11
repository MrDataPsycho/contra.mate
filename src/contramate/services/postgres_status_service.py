import psycopg2
from typing import Dict, Any
import logging
from neopipe import Result, Ok, Err

from contramate.utils.settings.core import settings

logger = logging.getLogger(__name__)

class PostgresService:
    """Service for PostgreSQL database operations and status checks"""

    def __init__(self):
        self.config = settings.postgres

    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return self.config.connection_string

    async def check_status(self) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Check PostgreSQL connection status

        Returns:
            Result[Ok, Err]: Ok with status data if successful, Err with error details if failed
        """
        try:
            # Test connection
            conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )

            # Test basic query
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]

            conn.close()

            return Ok({
                "connected": True,
                "status": "healthy",
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "version": version,
                "message": "PostgreSQL connection successful"
            })

        except psycopg2.OperationalError as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return Err({
                "connected": False,
                "status": "error",
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "error": str(e),
                "message": "PostgreSQL connection failed"
            })
        except Exception as e:
            logger.error(f"Unexpected error checking PostgreSQL status: {e}")
            return Err({
                "connected": False,
                "status": "error",
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "error": str(e),
                "message": "Unexpected error occurred"
            })

if __name__ == "__main__":
    import asyncio
    service = PostgresService()
    status = asyncio.run(service.check_status())
    print(status)