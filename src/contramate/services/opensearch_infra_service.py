"""
OpenSearch Infrastructure Service for managing indices.

This service provides infrastructure operations for OpenSearch including
creating, deleting, and managing indices with proper configuration.
"""

from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError, AuthenticationException, RequestError
from loguru import logger

from contramate.utils.settings.factory import settings_factory
from contramate.dbs.models.index_config import DocumentIndexConfig


class OpenSearchInfraService:
    """
    Service for managing OpenSearch infrastructure operations like creating and deleting indices.
    """
    
    def __init__(self, client: Optional[OpenSearch] = None):
        """
        Initialize the OpenSearch Infrastructure Service.
        
        Args:
            client: OpenSearch client instance. If None, creates client from settings
        """
        self.config = settings_factory.create_opensearch_settings()
        self.app_config = settings_factory.create_app_settings()
        self.client = client or self._create_client()
        
    def _create_client(self) -> OpenSearch:
        """Create OpenSearch client from settings"""
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
        
    def list_indices(self) -> List[str]:
        """
        List all available indices in the OpenSearch cluster.
        
        Returns:
            List of index names
        """
        try:
            indices = self.client.indices.get(index="*")
            index_names = list(indices.keys())
            logger.info(f"Found {len(index_names)} indices")
            return index_names
        except Exception as e:
            logger.error(f"Error listing indices: {e}")
            return []
    
    def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.
        
        Args:
            index_name: Name of the index to check
            
        Returns:
            True if index exists, False otherwise
        """
        try:
            return self.client.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"Error checking if index '{index_name}' exists: {e}")
            return False
    
    def create_index(
        self, 
        index_name: str, 
        vector_dimension: Optional[int] = None,
        force_recreate: bool = False
    ) -> bool:
        """
        Create a new OpenSearch index with document mapping configuration.
        
        Args:
            index_name: Name of the index to create
            vector_dimension: Vector dimension for embeddings. If None, uses value from app settings
            force_recreate: If True, delete existing index before creating new one
            
        Returns:
            True if index was created successfully, False otherwise
        """
        try:            
            # Check if index already exists
            if self.index_exists(index_name):
                if force_recreate:
                    logger.info(f"Index '{index_name}' exists. force_recreate=True, deleting first...")
                    if not self.delete_index(index_name):
                        logger.error(f"Failed to delete existing index '{index_name}'")
                        return False
                else:
                    logger.info(f"Index '{index_name}' already exists. Skipping creation.")
                    return True
            
            # Get vector dimension from settings if not provided
            dimension = vector_dimension or self.app_config.vector_dimension
            
            # Get index mapping configuration
            index_mapping = DocumentIndexConfig.get_index_mapping(vector_dimension=dimension)
            
            logger.info(f"Creating index '{index_name}' with vector dimension: {dimension}")
            
            # Create the index
            response = self.client.indices.create(
                index=index_name,
                body=index_mapping
            )
            
            logger.info(f"✅ Successfully created index '{index_name}'")
            logger.debug(f"Create response: {response}")
            
            return True
            
        except ConnectionError as e:
            logger.error(f"❌ Connection error creating index '{index_name}': {e}")
            return False
        except AuthenticationException as e:
            logger.error(f"❌ Authentication error creating index '{index_name}': {e}")
            return False
        except RequestError as e:
            logger.error(f"❌ Request error creating index '{index_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error creating index '{index_name}': {e}")
            return False
    
    def delete_index(self, index_name: str) -> bool:
        """
        Delete an OpenSearch index.
        
        Args:
            index_name: Name of the index to delete
            
        Returns:
            True if index was deleted successfully, False otherwise
        """
        try:            
            # Check if index exists before attempting to delete
            if not self.index_exists(index_name):
                logger.warning(f"⚠️ Index '{index_name}' does not exist. No action taken.")
                return True
            
            logger.info(f"Deleting index '{index_name}'...")
            
            # Delete the index
            response = self.client.indices.delete(index=index_name)
            
            logger.info(f"✅ Successfully deleted index '{index_name}'")
            logger.debug(f"Delete response: {response}")
            
            return True
            
        except ConnectionError as e:
            logger.error(f"❌ Connection error deleting index '{index_name}': {e}")
            return False
        except AuthenticationException as e:
            logger.error(f"❌ Authentication error deleting index '{index_name}': {e}")
            return False
        except RequestError as e:
            logger.error(f"❌ Request error deleting index '{index_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting index '{index_name}': {e}")
            return False
    
    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific index.
        
        Args:
            index_name: Name of the index to get stats for
            
        Returns:
            Dictionary containing index statistics
        """
        try:            
            if not self.index_exists(index_name):
                logger.warning(f"Index '{index_name}' does not exist")
                return {
                    "index_name": index_name,
                    "exists": False,
                    "total_documents": 0
                }
            
            # Get index statistics using cat indices API
            response = self.client.cat.indices(index=index_name, format="json")
            
            if not response:
                logger.warning(f"Could not retrieve stats for index '{index_name}'")
                return {
                    "index_name": index_name,
                    "exists": True,
                    "total_documents": 0
                }
            
            stats = response[0] if response else {}
            total_docs = int(stats.get("docs.count", 0))
            
            return {
                "index_name": index_name,
                "exists": True,
                "total_documents": total_docs,
                "index_size": stats.get("store.size", "unknown"),
                "health": stats.get("health", "unknown"),
                "status": stats.get("status", "unknown")
            }
            
        except ConnectionError as e:
            logger.error(f"Connection error getting stats for index '{index_name}': {e}")
            return {
                "index_name": index_name,
                "exists": False,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error getting stats for index '{index_name}': {e}")
            return {
                "index_name": index_name,
                "exists": False,
                "error": str(e)
            }
    
    def get_cluster_health(self) -> Dict[str, Any]:
        """
        Get OpenSearch cluster health information.
        
        Returns:
            Dictionary containing cluster health information
        """
        try:
            health = self.client.cluster.health()
            info = self.client.info()
            
            return {
                "cluster_name": health.get('cluster_name'),
                "status": health.get('status'),
                "number_of_nodes": health.get('number_of_nodes'),
                "number_of_data_nodes": health.get('number_of_data_nodes'),
                "active_primary_shards": health.get('active_primary_shards'),
                "active_shards": health.get('active_shards'),
                "relocating_shards": health.get('relocating_shards'),
                "initializing_shards": health.get('initializing_shards'),
                "unassigned_shards": health.get('unassigned_shards'),
                "version": info.get('version', {}).get('number'),
                "healthy": health.get('status') in ['green', 'yellow']
            }
        except Exception as e:
            logger.error(f"Error getting cluster health: {e}")
            return {
                "error": str(e),
                "healthy": False
            }
    
    def create_default_index(self, vector_dimension: Optional[int] = None, force_recreate: bool = False) -> bool:
        """
        Create the default index using app settings default index name.
        
        Args:
            vector_dimension: Vector dimension for embeddings. If None, uses value from app settings
            force_recreate: If True, delete existing index before creating new one
            
        Returns:
            True if index was created successfully, False otherwise
        """
        default_index = self.app_config.default_index_name
        return self.create_index(
            index_name=default_index,
            vector_dimension=vector_dimension,
            force_recreate=force_recreate
        )


def create_opensearch_infra_service(client: Optional[OpenSearch] = None) -> OpenSearchInfraService:
    """
    Factory function to create OpenSearchInfraService instance.
    
    Args:
        client: Optional OpenSearch client instance
        
    Returns:
        OpenSearchInfraService instance
    """
    return OpenSearchInfraService(client=client)


if __name__ == "__main__":
    from time import sleep
    
    # Test the infrastructure service
    infra_service = create_opensearch_infra_service()
    
    # Get cluster health
    health = infra_service.get_cluster_health()
    logger.info(f"Cluster health: {health}")
    
    # List indices
    indices = infra_service.list_indices()
    logger.info(f"Available indices: {indices}")
    
    # Test with default index
    test_index = infra_service.app_config.default_index_name
    
    # Get stats
    stats = infra_service.get_index_stats(test_index)
    logger.info(f"Stats for index '{test_index}': {stats}")
    
    # Delete and recreate test index
    delete_response = infra_service.delete_index(test_index)
    logger.info(f"Delete index response: {delete_response}")
    
    create_response = infra_service.create_index(test_index)
    logger.info(f"Create index response: {create_response}")
    
    # # Wait for index to be ready
    # sleep(5)
    
    # # Get updated stats
    # stats = infra_service.get_index_stats(test_index)
    # logger.info(f"Updated stats for index '{test_index}': {stats}")