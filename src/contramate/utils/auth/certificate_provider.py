from typing import Callable
from azure.identity import CertificateCredential
from contramate.utils.settings.core import AOAICertSettings


def get_cert_token_provider(settings: AOAICertSettings) -> Callable[[], str]:
    """Returns a callable that provides a bearer token using certificate-based authentication.

    This function creates a token provider that can be used directly with AzureOpenAI client.
    
    Example:
        ```python
        from azure.identity import CertificateCredential
        from contramate.utils.auth.certificate_provider import get_cert_token_provider
        
        token_provider = get_cert_token_provider(settings)
        
        # Then use with AzureOpenAI client
        client = AzureOpenAI(
            azure_endpoint="https://your-endpoint.openai.azure.com",
            api_version="2023-05-15",
            azure_ad_token_provider=token_provider
        )
        ```

    Args:
        settings: An instance of AOAICertSettings containing the necessary certificate details.

    Returns:
        A callable that returns a bearer token when invoked
    """
    # Create the certificate credential
    credential = CertificateCredential(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        certificate_data=settings.certificate_string
    )
    
    # Define the token provider function
    def token_provider() -> str:
        # Get a fresh token when called
        token = credential.get_token(settings.resource)
        return token.token
    
    return token_provider