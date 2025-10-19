"""OpenSearch client integration for AWS"""

from opensearchpy import OpenSearch, RequestsHttpConnection
from loguru import logger

from contramate.utils.settings.core import OpenSearchSettings


def create_opensearch_client(
    opensearch_settings: OpenSearchSettings,
    pool_maxsize: int = 10
) -> OpenSearch:
    """
    Create an OpenSearch client with the given settings.

    Args:
        opensearch_settings: OpenSearch configuration settings
        pool_maxsize: Maximum number of connections in the pool (default: 10)

    Returns:
        OpenSearch: Configured OpenSearch client instance

    Example:
        >>> from contramate.utils.settings.factory import settings_factory
        >>> opensearch_settings = settings_factory.create_opensearch_settings()
        >>> client = create_opensearch_client(opensearch_settings)
    """
    client_config = {
        'hosts': [
            {
                'host': opensearch_settings.host,
                'port': opensearch_settings.port
            }
        ],
        'use_ssl': opensearch_settings.use_ssl,
        'verify_certs': opensearch_settings.verify_certs,
        'ssl_show_warn': False,
        'connection_class': RequestsHttpConnection,
        'pool_maxsize': pool_maxsize,
        'timeout': 30,
    }

    # Add authentication if credentials are provided
    if opensearch_settings.username and opensearch_settings.password:
        client_config['http_auth'] = (
            opensearch_settings.username,
            opensearch_settings.password
        )

    opensearch_client = OpenSearch(**client_config)

    logger.info(
        f"Created OpenSearch client for {opensearch_settings.host}:{opensearch_settings.port}"
    )

    return opensearch_client


if __name__ == "__main__":
    # Example usage
    from contramate.utils.settings.factory import settings_factory

    opensearch_settings = settings_factory.create_opensearch_settings()
    client = create_opensearch_client(opensearch_settings)
    info = client.info()
    logger.info(f"OpenSearch cluster info: {info}")
