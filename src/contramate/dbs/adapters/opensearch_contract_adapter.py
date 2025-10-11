"""OpenSearch adapter for contract vector database operations"""

from typing import Any, List, Dict, Optional, Union
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import NotFoundError
from loguru import logger

from contramate.dbs.interfaces.vector_store import VectorDBABC
from contramate.utils.settings.core import OpenSearchSettings
from contramate.llm import OpenAIEmbeddingClient, LiteLLMEmbeddingClient, AzureOpenAIEmbeddingClient, BaseEmbeddingClient


class OpenSearchContractAdapter(VectorDBABC):
    """OpenSearch implementation for contract vector database operations"""

    def __init__(
        self,
        opensearch_settings: OpenSearchSettings,
        index_name: Optional[str] = None,
        embedding_dimension: int = 3072,  # Default for text-embedding-3-large
        embedding_client: Optional[BaseEmbeddingClient] = None
    ):
        """
        Initialize OpenSearch contract adapter

        Args:
            opensearch_settings: OpenSearch configuration settings
            index_name: Override index name (uses opensearch_settings.get_index_name() if None)
            embedding_dimension: Dimension of the embedding vectors
            embedding_client: Embedding client for generating vectors (auto-selected if None)
        """
        self.opensearch_settings = opensearch_settings
        self.index_name = index_name or opensearch_settings.get_index_name()
        self.embedding_dimension = embedding_dimension

        # Initialize embedding client
        self.embedding_client = embedding_client or self._get_default_embedding_client()

        # Initialize OpenSearch client
        self.client = OpenSearch(
            hosts=[{"host": opensearch_settings.host, "port": opensearch_settings.port}],
            http_auth=(opensearch_settings.username, opensearch_settings.password) if opensearch_settings.username else None,
            use_ssl=opensearch_settings.use_ssl,
            verify_certs=opensearch_settings.verify_certs,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )

        # Check that index exists
        self._ensure_index_exists()

    def _get_default_embedding_client(self) -> BaseEmbeddingClient:
        """Get default embedding client based on available settings"""
        try:
            # Try OpenAI first (most common)
            from contramate.utils.settings.core import settings
            if settings.openai.api_key:
                return OpenAIEmbeddingClient()
        except Exception:
            pass

        try:
            # Try Azure OpenAI with certificate auth
            return AzureOpenAIEmbeddingClient()
        except Exception:
            pass

        try:
            # Try LiteLLM as fallback
            return LiteLLMEmbeddingClient()
        except Exception:
            pass

        raise ValueError("No valid embedding client could be initialized. Please configure OpenAI, Azure OpenAI, or LiteLLM settings.")

    def _ensure_index_exists(self) -> None:
        """Check that the index exists, raise error if it doesn't"""
        if not self.client.indices.exists(index=self.index_name):
            raise ValueError(f"OpenSearch index '{self.index_name}' does not exist. Please create the index first using the ETL pipeline.")

        logger.info(f"OpenSearch index '{self.index_name}' exists and is ready")

    def save(self) -> None:
        """Save/flush any pending operations to OpenSearch"""
        try:
            self.client.indices.refresh(index=self.index_name)
            logger.info(f"Refreshed index: {self.index_name}")
        except Exception as e:
            logger.error(f"Error refreshing index {self.index_name}: {e}")
            raise

    def load(self) -> None:
        """Load/verify the OpenSearch index exists"""
        try:
            self._ensure_index_exists()
            logger.info(f"Index {self.index_name} loaded successfully")
        except Exception as e:
            logger.error(f"Error loading index {self.index_name}: {e}")
            raise

    def search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        text_weight: float = 0.3,
        embedding_weight: float = 0.7,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar contract documents using hybrid search (text + vector)

        Args:
            query: Text query to search for
            top_k: Number of top results to return
            filters: Additional filters to apply (contract_id, contract_type, etc.)
            text_weight: Weight for text search component (default 0.3)
            embedding_weight: Weight for vector search component (default 0.7)
            use_hybrid: Whether to use hybrid search or text-only (default True)

        Returns:
            List of search results with metadata
        """
        # Generate embedding for hybrid search
        query_embedding = None
        if use_hybrid:
            try:
                embedding_response = self.embedding_client.create_embeddings(query)
                query_embedding = embedding_response.embeddings[0]
                logger.info(f"Generated embedding for query: {query[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to generate embedding for query, falling back to text-only search: {e}")
                use_hybrid = False

        # Build search query
        if use_hybrid and query_embedding:
            # Hybrid search with both text and vector
            search_body = {
                "size": top_k,
                "query": {
                    "hybrid": {
                        "queries": [
                            {
                                "match": {
                                    "content": {
                                        "query": query,
                                        "boost": text_weight
                                    }
                                }
                            },
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_embedding,
                                        "k": top_k,
                                        "boost": embedding_weight
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["contract_id", "document_id", "content", "metadata"],
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        }
                    }
                }
            }
        else:
            # Text-only search fallback
            search_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "content": {
                                        "query": query,
                                        "boost": 1.0
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["contract_id", "document_id", "content", "metadata"],
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        }
                    }
                }
            }

        # Apply filters if provided
        if filters:
            filter_clauses = []

            # Handle documents filter with project_reference_doc_id construction
            if "documents" in filters:
                documents_filter = filters["documents"]
                project_reference_doc_ids = [
                    f"{doc.get('project_id', '')}-{doc.get('reference_doc_id', '')}"
                    for doc in documents_filter
                    if doc.get("project_id") and doc.get("reference_doc_id")
                ]

                if project_reference_doc_ids:
                    filter_clauses.append({"terms": {"project_reference_doc_id": project_reference_doc_ids}})

                    logger.info(f"Applied documents filter for project_reference_doc_ids: {project_reference_doc_ids}")

            if filter_clauses:
                if use_hybrid and query_embedding:
                    # For hybrid search, add filters to both text and vector queries
                    for query_item in search_body["query"]["hybrid"]["queries"]:
                        if "match" in query_item:
                            # Text query - wrap in bool with filter
                            original_match = query_item.pop("match")
                            query_item["bool"] = {
                                "must": [{"match": original_match}],
                                "filter": filter_clauses
                            }
                        elif "knn" in query_item:
                            # Vector query - add filter to knn
                            query_item["knn"]["embedding"]["filter"] = {
                                "bool": {"filter": filter_clauses}
                            }
                else:
                    # For text-only search
                    search_body["query"]["bool"]["filter"] = filter_clauses

        try:
            response = self.client.search(index=self.index_name, body=search_body)

            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "contract_id": hit["_source"].get("contract_id"),
                    "document_id": hit["_source"].get("document_id"),
                    "content": hit["_source"].get("content"),
                    "metadata": hit["_source"].get("metadata", {}),
                    "highlights": hit.get("highlight", {}).get("content", [])
                }
                results.append(result)

            search_type = "hybrid" if (use_hybrid and query_embedding) else "text-only"
            logger.info(f"Found {len(results)} results for {search_type} query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Error searching in OpenSearch: {e}")
            raise

    def vector_search(
        self,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar contract documents using vector similarity

        Args:
            query_vector: Embedding vector to search with
            top_k: Number of top results to return
            filters: Additional filters to apply

        Returns:
            List of search results with metadata
        """
        search_body = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_vector,
                                    "k": top_k
                                }
                            }
                        }
                    ]
                }
            },
            "_source": ["contract_id", "document_id", "content", "metadata"]
        }

        # Apply filters if provided
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                if key == "contract_id":
                    filter_clauses.append({"term": {"contract_id": value}})
                elif key == "contract_type":
                    filter_clauses.append({"term": {"metadata.contract_type": value}})
                elif key == "section":
                    filter_clauses.append({"term": {"metadata.section": value}})
                else:
                    filter_clauses.append({"term": {f"metadata.{key}": value}})

            if filter_clauses:
                search_body["query"]["bool"]["filter"] = filter_clauses

        try:
            response = self.client.search(index=self.index_name, body=search_body)

            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "contract_id": hit["_source"].get("contract_id"),
                    "document_id": hit["_source"].get("document_id"),
                    "content": hit["_source"].get("content"),
                    "metadata": hit["_source"].get("metadata", {})
                }
                results.append(result)

            logger.info(f"Found {len(results)} results for vector search")
            return results

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            raise

    def insert(self, documents: List[Dict[str, Any]]) -> None:
        """
        Insert contract documents into OpenSearch

        Args:
            documents: List of documents to insert, each containing:
                - contract_id: ID of the contract
                - document_id: Unique document identifier
                - content: Text content
                - embedding: Vector embedding
                - metadata: Additional metadata
        """
        try:
            for doc in documents:
                body = {
                    "contract_id": doc["contract_id"],
                    "document_id": doc["document_id"],
                    "content": doc["content"],
                    "embedding": doc["embedding"],
                    "metadata": doc.get("metadata", {})
                }

                # Use document_id as the OpenSearch document ID for consistency
                self.client.index(
                    index=self.index_name,
                    id=doc["document_id"],
                    body=body
                )

            logger.info(f"Inserted {len(documents)} documents into {self.index_name}")

        except Exception as e:
            logger.error(f"Error inserting documents: {e}")
            raise

    def delete(self, index_id: str) -> None:
        """
        Delete a document from OpenSearch

        Args:
            index_id: Document ID to delete
        """
        try:
            self.client.delete(index=self.index_name, id=index_id)
            logger.info(f"Deleted document {index_id} from {self.index_name}")
        except NotFoundError:
            logger.warning(f"Document {index_id} not found in {self.index_name}")
        except Exception as e:
            logger.error(f"Error deleting document {index_id}: {e}")
            raise

    def upsert(self, documents: List[Dict[str, Any]]) -> None:
        """
        Insert or update contract documents in OpenSearch

        Args:
            documents: List of documents to upsert
        """
        try:
            for doc in documents:
                body = {
                    "contract_id": doc["contract_id"],
                    "document_id": doc["document_id"],
                    "content": doc["content"],
                    "embedding": doc["embedding"],
                    "metadata": doc.get("metadata", {})
                }

                # Use document_id as the OpenSearch document ID for consistency
                self.client.index(
                    index=self.index_name,
                    id=doc["document_id"],
                    body=body
                )

            logger.info(f"Upserted {len(documents)} documents into {self.index_name}")

        except Exception as e:
            logger.error(f"Error upserting documents: {e}")
            raise

    def delete_by_contract_id(self, contract_id: str) -> int:
        """
        Delete all documents belonging to a specific contract

        Args:
            contract_id: Contract ID to delete documents for

        Returns:
            Number of deleted documents
        """
        try:
            delete_query = {
                "query": {
                    "term": {"contract_id": contract_id}
                }
            }

            response = self.client.delete_by_query(
                index=self.index_name,
                body=delete_query
            )

            deleted_count = response.get("deleted", 0)
            logger.info(f"Deleted {deleted_count} documents for contract {contract_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting documents for contract {contract_id}: {e}")
            raise

    def get_document_count(self) -> int:
        """Get total number of documents in the index"""
        try:
            response = self.client.count(index=self.index_name)
            return response["count"]
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            raise

    def get_contracts_list(self) -> List[str]:
        """Get list of unique contract IDs in the index"""
        try:
            search_body = {
                "size": 0,
                "aggs": {
                    "unique_contracts": {
                        "terms": {
                            "field": "contract_id",
                            "size": 10000
                        }
                    }
                }
            }

            response = self.client.search(index=self.index_name, body=search_body)

            contracts = [
                bucket["key"]
                for bucket in response["aggregations"]["unique_contracts"]["buckets"]
            ]

            logger.info(f"Found {len(contracts)} unique contracts")
            return contracts

        except Exception as e:
            logger.error(f"Error getting contracts list: {e}")
            raise