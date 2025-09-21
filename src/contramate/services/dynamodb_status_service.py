import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError, ConnectTimeoutError
from botocore.config import Config
from typing import Dict, Any
import asyncio
from contramate.utils.settings.core import settings
from loguru import logger

class DynamoDBStatusService:
    """Service for DynamoDB connection status checks"""

    def __init__(self):
        self.config = settings.dynamodb

    def get_client(self):
        """Get DynamoDB client with timeout configuration"""
        # Configure timeouts to prevent hanging
        config = Config(
            connect_timeout=5,  # 5 seconds to establish connection
            read_timeout=10,    # 10 seconds to read response
            retries={'max_attempts': 1}  # Don't retry on failure for status check
        )

        return boto3.client(
            'dynamodb',
            endpoint_url=self.config.endpoint_url,
            region_name=self.config.region,
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key,
            config=config
        )

    async def check_status(self) -> Dict[str, Any]:
        """Check DynamoDB connection status"""
        try:
            client = self.get_client()
            logger.info("DynamoDB client created successfully")

            # Run the blocking boto3 call in an executor with timeout
            loop = asyncio.get_event_loop()

            # Wrap the blocking call in asyncio with timeout
            response = await asyncio.wait_for(
                loop.run_in_executor(None, client.list_tables),
                timeout=10.0  # 10 second timeout
            )

            table_count = len(response.get('TableNames', []))
            logger.info(f"DynamoDB connection successful, found {table_count} tables")

            return {
                "connected": True,
                "status": "healthy",
                "endpoint_url": self.config.endpoint_url,
                "region": self.config.region,
                "table_count": table_count,
                "tables": response.get('TableNames', []),
                "message": "DynamoDB connection successful"
            }

        except asyncio.TimeoutError:
            logger.error("DynamoDB connection timed out")
            return {
                "connected": False,
                "status": "timeout_error",
                "endpoint_url": self.config.endpoint_url,
                "region": self.config.region,
                "error": "Connection timed out after 10 seconds",
                "message": "DynamoDB connection timed out - service may not be running"
            }
        except (EndpointConnectionError, ConnectTimeoutError) as e:
            logger.error(f"DynamoDB endpoint connection failed: {e}")
            return {
                "connected": False,
                "status": "connection_error",
                "endpoint_url": self.config.endpoint_url,
                "region": self.config.region,
                "error": str(e),
                "message": "DynamoDB endpoint unreachable"
            }
        except NoCredentialsError as e:
            logger.error(f"DynamoDB credentials error: {e}")
            return {
                "connected": False,
                "status": "credentials_error",
                "endpoint_url": self.config.endpoint_url,
                "region": self.config.region,
                "error": str(e),
                "message": "DynamoDB credentials not found or invalid"
            }
        except ClientError as e:
            logger.error(f"DynamoDB client error: {e}")
            return {
                "connected": False,
                "status": "client_error",
                "endpoint_url": self.config.endpoint_url,
                "region": self.config.region,
                "error": str(e),
                "error_code": e.response.get('Error', {}).get('Code'),
                "message": "DynamoDB client error occurred"
            }
        except Exception as e:
            logger.error(f"Unexpected error checking DynamoDB status: {e}")
            return {
                "connected": False,
                "status": "error",
                "endpoint_url": self.config.endpoint_url,
                "region": self.config.region,
                "error": str(e),
                "message": "Unexpected error occurred"
            }

if __name__ == "__main__":
    import asyncio
    service = DynamoDBStatusService()
    status = asyncio.run(service.check_status())
    print(status)