from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError, AuthenticationException, RequestError
from typing import Dict, Any
import logging
from contramate.utils.settings.core import settings

logger = logging.getLogger(__name__)

class OpenSearchStatusService:
    """Service for OpenSearch connection status checks"""

    def __init__(self):
        self.config = settings.opensearch

    def get_client(self):
        """Get OpenSearch client"""
        client_config = {
            'hosts': [{'host': self.config.host, 'port': self.config.port}],
            'use_ssl': self.config.use_ssl,
            'verify_certs': self.config.verify_certs,
            'ssl_show_warn': False
        }

        # Add authentication if credentials are provided
        if self.config.username and self.config.password:
            client_config['http_auth'] = (self.config.username, self.config.password)

        return OpenSearch(**client_config)

    async def check_status(self) -> Dict[str, Any]:
        """Check OpenSearch connection status"""
        try:
            client = self.get_client()

            # Test connection with cluster health
            health = client.cluster.health()
            info = client.info()

            # Get indices count
            indices = client.cat.indices(format='json')
            indices_count = len(indices) if indices else 0

            return {
                "connected": True,
                "status": "healthy",
                "host": self.config.host,
                "port": self.config.port,
                "cluster_name": health.get('cluster_name'),
                "cluster_status": health.get('status'),
                "number_of_nodes": health.get('number_of_nodes'),
                "number_of_data_nodes": health.get('number_of_data_nodes'),
                "active_primary_shards": health.get('active_primary_shards'),
                "active_shards": health.get('active_shards'),
                "indices_count": indices_count,
                "version": info.get('version', {}).get('number'),
                "message": "OpenSearch connection successful"
            }

        except ConnectionError as e:
            logger.error(f"OpenSearch connection failed: {e}")
            return {
                "connected": False,
                "status": "connection_error",
                "host": self.config.host,
                "port": self.config.port,
                "error": str(e),
                "message": "OpenSearch connection failed"
            }
        except AuthenticationException as e:
            logger.error(f"OpenSearch authentication failed: {e}")
            return {
                "connected": False,
                "status": "authentication_error",
                "host": self.config.host,
                "port": self.config.port,
                "error": str(e),
                "message": "OpenSearch authentication failed"
            }
        except RequestError as e:
            logger.error(f"OpenSearch request error: {e}")
            return {
                "connected": False,
                "status": "request_error",
                "host": self.config.host,
                "port": self.config.port,
                "error": str(e),
                "message": "OpenSearch request error"
            }
        except Exception as e:
            logger.error(f"Unexpected error checking OpenSearch status: {e}")
            return {
                "connected": False,
                "status": "error",
                "host": self.config.host,
                "port": self.config.port,
                "error": str(e),
                "message": "Unexpected error occurred"
            }

if __name__ == "__main__":
    import asyncio
    service = OpenSearchStatusService()
    status = asyncio.run(service.check_status())
    print(status)