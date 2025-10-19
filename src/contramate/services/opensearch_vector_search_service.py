"""
OpenSearch Vector Search Service for advanced search operations.

This service provides semantic, text, and hybrid search capabilities for VectorModel documents,
with support for filtering, project-based search, and similarity matching.
"""

import time
from typing import Optional, List, Dict, Any, Union
from loguru import logger
from opensearchpy import OpenSearch
from neopipe import Result, Ok, Err
from pydantic import BaseModel

from contramate.models.vector import ContentSource
from contramate.models.filters import OpenSearchFilter
from contramate.llm.base import BaseEmbeddingClient
from contramate.llm.openai_embedding_client import OpenAIEmbeddingClient
from contramate.utils.settings.factory import settings_factory
from contramate.utils.settings.core import AppSettings, OpenAISettings, OpenSearchSettings
from contramate.integrations.aws.opensearch import create_opensearch_client
from contramate.llm.factory import create_default_embedding_client
from contramate.services.factory import ServiceFactoryABC
from pathlib import Path


class SearchResult(BaseModel):
    """Individual search result model."""
    record_id: str
    project_id: str
    reference_doc_id: str
    document_title: str
    content_source: ContentSource
    contract_type: Optional[str]
    content: str
    chunk_index: int
    section_hierarchy: Optional[Union[str, List[str]]]
    char_start: int
    char_end: int
    token_count: int
    has_tables: bool
    score: Optional[float]
    created_at: str
    
    @classmethod
    def from_opensearch_hit(cls, hit: Dict[str, Any]) -> "SearchResult":
        """Create SearchResult from OpenSearch hit."""
        source = hit["_source"]
        # Handle section_hierarchy as either string or list
        section_hierarchy = source.get("section_hierarchy")
        if isinstance(section_hierarchy, list):
            section_hierarchy = " > ".join(section_hierarchy) if section_hierarchy else None
        
        return cls(
            record_id=source["record_id"],
            project_id=source["project_id"],
            reference_doc_id=source["reference_doc_id"],
            document_title=source["document_title"],
            content_source=ContentSource(source["content_source"]),
            contract_type=source.get("contract_type"),
            content=source["content"],
            chunk_index=source["chunk_index"],
            section_hierarchy=section_hierarchy,
            char_start=source["char_start"],
            char_end=source["char_end"],
            token_count=source["token_count"],
            has_tables=source["has_tables"],
            score=hit.get("_score"),  # Use .get() to handle None when using sort
            created_at=source["created_at"]
        )


class SearchResponse(BaseModel):
    """Search response containing results and metadata."""
    results: List[SearchResult]
    total_results: int
    search_type: str
    query: str
    execution_time_ms: float
    size: int
    min_score: Optional[float] = None
    filters: Optional[Dict[str, Any]] = None
    semantic_weight: Optional[float] = None
    text_weight: Optional[float] = None




class OpenSearchVectorSearchService:
    """
    Advanced search service for OpenSearch vector documents with semantic, text, and hybrid search capabilities.

    Usage Example:
        >>> from dotenv import load_dotenv
        >>> load_dotenv(".envs/local.env")
        >>> from contramate.utils.settings.factory import settings_factory
        >>> from contramate.integrations.aws.opensearch import create_opensearch_client
        >>> from contramate.llm.factory import create_default_embedding_client
        >>>
        >>> # Create settings
        >>> app_config = settings_factory.create_app_settings()
        >>> opensearch_config = settings_factory.create_opensearch_settings()
        >>>
        >>> # Create clients
        >>> opensearch_client = create_opensearch_client(opensearch_config, pool_maxsize=10)
        >>> embedding_client = create_default_embedding_client()
        >>>
        >>> # Initialize service
        >>> service = OpenSearchVectorSearchService(
        ...     index_name=app_config.default_index_name,
        ...     client=opensearch_client,
        ...     embedding_client=embedding_client
        ... )
    """

    def __init__(self, index_name: str, client: OpenSearch, embedding_client: BaseEmbeddingClient):
        """
        Initialize the OpenSearch Vector Search Service.

        Args:
            index_name: Name of the OpenSearch index to search in (required)
            client: OpenSearch client instance (required)
            embedding_client: Embedding client for semantic search (required)
        """
        self.index_name = index_name
        self.client = client
        self.embedding_client = embedding_client
    
    def _create_opensearch_filter(self, filters_dict: Optional[Dict[str, Any]]) -> Optional[OpenSearchFilter]:
        """
        Convert dictionary filters to OpenSearchFilter object.

        Args:
            filters_dict: Dictionary containing filter parameters

        Returns:
            OpenSearchFilter object or None if no filters provided
        """
        if not filters_dict:
            return None

        try:
            return OpenSearchFilter(**filters_dict)
        except Exception as e:
            logger.warning(f"⚠️ Failed to create OpenSearchFilter from dict {filters_dict}: {e}")
            return None
    
    def semantic_search(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        min_score: float = 0.5,
    ) -> Result[SearchResponse, str]:
        """
        Perform semantic search using vector similarity.

        Args:
            query: Text to search for semantically
            k: Number of nearest neighbors to find (default: 10)
            filters: Optional filters as dictionary (will be converted to OpenSearchFilter)
            size: Number of results to return (default: 10)
            min_score: Minimum similarity score threshold (default: 0.5)

        Returns:
            Result[SearchResponse, str]: Ok with search results, Err with error message
        """
        start_time = time.time()
        try:
            # Convert dict filters to OpenSearchFilter object
            opensearch_filter = self._create_opensearch_filter(filters)
            
            # Generate embedding for the query text
            logger.info(f"🔍 Generating embedding for query: '{query[:50]}...'")
            try:
                embedding_response = self.embedding_client.create_embeddings(query)
                query_vector = embedding_response.embeddings[0]  # Get first embedding
            except Exception as e:
                return Err(f"Failed to generate embedding: {str(e)}")
            logger.info(f"✅ Generated embedding vector with {len(query_vector)} dimensions")
            
            # Build the k-NN search query
            excludes = ["vector"]  # Always exclude vector fields
                
            search_query = {
                "size": size,
                "query": {
                    "knn": {
                        "vector": {
                            "vector": query_vector,
                            "k": k
                        }
                    }
                },
                "_source": {
                    "excludes": excludes
                }
            }
            
            # Apply filters if provided
            if opensearch_filter:
                filter_clauses = opensearch_filter.to_opensearch_filters()

                if filter_clauses:
                    search_query["query"] = {
                        "bool": {
                            "must": [
                                search_query["query"]
                            ],
                            "filter": filter_clauses
                        }
                    }
            
            # Execute search
            response = self.client.search(index=self.index_name, body=search_query)
            
            # Process results
            search_results = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                
                # Apply minimum score threshold
                if score >= min_score:
                    search_result = SearchResult.from_opensearch_hit(hit)
                    search_results.append(search_result)
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            logger.info(f"✅ Semantic search returned {len(search_results)} results above threshold {min_score}")
            
            search_response = SearchResponse(
                results=search_results,
                total_results=response["hits"]["total"]["value"],
                search_type="semantic",
                query=query,
                execution_time_ms=execution_time,
                size=size,
                min_score=min_score,
                filters=filters if isinstance(filters, dict) else None
            )
            
            return Ok(search_response)
            
        except Exception as e:
            error_msg = f"Error performing semantic search: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def text_search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.5,
    ) -> Result[SearchResponse, str]:
        """
        Perform text-based search using full-text search capabilities.

        Args:
            query: Text to search for
            fields: Fields to search in (default: ["content", "section_hierarchy"])
            size: Number of results to return (default: 10)
            filters: Optional filters as dictionary (will be converted to OpenSearchFilter)
            min_score: Minimum score threshold for results (default: 0.0)

        Returns:
            Result[SearchResponse, str]: Ok with search results, Err with error message
        """
        start_time = time.time()
        try:
            if not fields:
                fields = ["content", "section_hierarchy"]

            # Convert dict filters to OpenSearchFilter object
            opensearch_filter = self._create_opensearch_filter(filters)
            
            # Build multi-match query
            excludes = ["vector"]  # Always exclude vector fields
                
            search_query = {
                "size": size,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": fields,
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                "_source": {
                    "excludes": excludes
                }
            }
            
            # Apply filters if provided
            if opensearch_filter:
                filter_clauses = opensearch_filter.to_opensearch_filters()

                if filter_clauses:
                    search_query["query"] = {
                        "bool": {
                            "must": [
                                search_query["query"]
                            ],
                            "filter": filter_clauses
                        }
                    }
            
            # Execute search
            response = self.client.search(index=self.index_name, body=search_query)

            # Process results
            search_results = []
            for hit in response["hits"]["hits"]:
                score = hit.get("_score", 0.0)

                # Apply minimum score threshold
                if score and score >= min_score:
                    search_result = SearchResult.from_opensearch_hit(hit)
                    search_results.append(search_result)

            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            logger.info(f"✅ Text search returned {len(search_results)} results above threshold {min_score}")
            
            search_response = SearchResponse(
                results=search_results,
                total_results=response["hits"]["total"]["value"],
                search_type="text",
                query=query,
                execution_time_ms=execution_time,
                size=size,
                min_score=min_score,
                filters=filters if isinstance(filters, dict) else None
            )
            
            return Ok(search_response)
            
        except Exception as e:
            error_msg = f"Error performing text search: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def hybrid_search(
        self,
        query: str,
        size: int = 10,
        semantic_weight: float = 0.7,
        text_weight: float = 0.3,
        min_score: float = 0.5,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[SearchResponse, str]:
        """
        Perform hybrid search combining semantic and text search with weighted scoring.

        Args:
            query: Text to search for
            size: Number of results to return (default: 10)
            semantic_weight: Weight for semantic search results (default: 0.7)
            text_weight: Weight for text search results (default: 0.3)
            min_score: Minimum combined score threshold (default: 0.5)
            fields: Fields to search in for text search
            filters: Optional filters as dictionary (will be converted to OpenSearchFilter)

        Returns:
            Result[SearchResponse, str]: Ok with combined results, Err with error message
        """
        start_time = time.time()
        try:
            # Convert dict filters to OpenSearchFilter object
            opensearch_filter = self._create_opensearch_filter(filters)
            
            # Generate embedding for semantic search
            logger.info(f"🔍 Performing hybrid search for: '{query[:50]}...'")
            try:
                embedding_response = self.embedding_client.create_embeddings(query)
                query_vector = embedding_response.embeddings[0]  # Get first embedding
            except Exception as e:
                return Err(f"Failed to generate embedding for hybrid search: {str(e)}")
            logger.info(f"✅ Generated embedding vector with {len(query_vector)} dimensions")
            
            # Set default fields if not provided
            if not fields:
                fields = ["content^2", "section_hierarchy^1"]  # Boost content more
            
            # Build excludes
            excludes = ["vector"]  # Always exclude vector fields
            
            # Build the function_score query
            search_query = {
                "size": size,
                "query": {
                    "function_score": {
                        "query": {
                            "bool": {
                                "should": [
                                    {
                                        "multi_match": {
                                            "query": query,
                                            "fields": fields,
                                            "type": "best_fields",
                                            "fuzziness": "AUTO"
                                        }
                                    },
                                    {
                                        "knn": {
                                            "vector": {
                                                "vector": query_vector,
                                                "k": size * 2  # Get more candidates for better hybrid results
                                            }
                                        }
                                    }
                                ],
                                "minimum_should_match": 1
                            }
                        },
                        "functions": [
                            {
                                "filter": {
                                    "exists": {
                                        "field": "content"
                                    }
                                },
                                "weight": text_weight
                            },
                            {
                                "filter": {
                                    "exists": {
                                        "field": "vector"
                                    }
                                },
                                "weight": semantic_weight
                            }
                        ],
                        "score_mode": "sum",
                        "boost_mode": "sum"
                    }
                },
                "_source": {
                    "excludes": excludes
                },
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 150, "number_of_fragments": 2},
                        "section_hierarchy": {"fragment_size": 100, "number_of_fragments": 1}
                    }
                }
            }
            
            # Apply filters if provided
            if opensearch_filter:
                filter_clauses = opensearch_filter.to_opensearch_filters()

                if filter_clauses:
                    # Add filter to the bool query inside function_score
                    search_query["query"]["function_score"]["query"]["bool"]["filter"] = filter_clauses
            
            # Execute search
            response = self.client.search(index=self.index_name, body=search_query)
            
            # Process results
            search_results = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                
                # Apply minimum score threshold
                if score >= min_score:
                    search_result = SearchResult.from_opensearch_hit(hit)
                    search_results.append(search_result)
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            logger.info(f"✅ Hybrid search returned {len(search_results)} results")
            
            search_response = SearchResponse(
                results=search_results,
                total_results=response["hits"]["total"]["value"],
                search_type="hybrid",
                query=query,
                execution_time_ms=execution_time,
                size=size,
                min_score=min_score,
                filters=filters if isinstance(filters, dict) else None,
                semantic_weight=semantic_weight,
                text_weight=text_weight
            )
            
            return Ok(search_response)
            
        except Exception as e:
            error_msg = f"Error performing hybrid search: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def search_by_project(
        self,
        project_id: str,
        query: Optional[str] = None,
        search_type: str = "hybrid",
        size: int = 10,
    ) -> Result[SearchResponse, str]:
        """
        Search within a specific project.
        
        Args:
            project_id: Project ID to filter by
            query: Optional text to search for (if None, returns all documents in project)
            search_type: Type of search ("semantic", "text", "hybrid")
            size: Number of results to return
            
        Returns:
            Result[SearchResponse, str]: Ok with search results, Err with error message
        """
        if not query:
            # Return all documents in the project
            try:
                start_time = time.time()
                excludes = ["vector"]  # Always exclude vector fields
                    
                search_query = {
                    "size": size,
                    "query": {
                        "term": {
                            "project_id": project_id
                        }
                    },
                    "_source": {
                        "excludes": excludes
                    },
                    "sort": [
                        {"chunk_index": {"order": "asc"}}  # Sort by chunk index
                    ]
                }
                
                response = self.client.search(index=self.index_name, body=search_query)
                
                # Process results
                search_results = []
                for hit in response["hits"]["hits"]:
                    search_result = SearchResult.from_opensearch_hit(hit)
                    search_results.append(search_result)
                
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                logger.info(f"✅ Retrieved {len(search_results)} documents for project {project_id}")
                
                search_response = SearchResponse(
                    results=search_results,
                    total_results=response["hits"]["total"]["value"],
                    search_type="project",
                    query=f"project_id: {project_id}",
                    execution_time_ms=execution_time,
                    size=size,
                    filters={"project_id": [project_id]}
                )
                
                return Ok(search_response)
                
            except Exception as e:
                error_msg = f"Error retrieving documents for project {project_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                return Err(error_msg)
        
        # Perform search with project filter
        project_filter_dict = {"project_id": [project_id]}
        
        if search_type == "semantic":
            return self.semantic_search(query, size=size, filters=project_filter_dict)
        elif search_type == "text":
            return self.text_search(query, size=size, filters=project_filter_dict)
        elif search_type == "hybrid":
            return self.hybrid_search(query, size=size, filters=project_filter_dict)
        else:
            return Err(f"Unknown search type: {search_type}")
    
    def search_similar_documents(
        self,
        record_id: str,
        size: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[SearchResponse, str]:
        """
        Find documents similar to a given document using its vector.

        Args:
            record_id: Record ID of the reference document
            size: Number of similar documents to return
            filters: Optional filters as dictionary (will be converted to OpenSearchFilter)

        Returns:
            Result[SearchResponse, str]: Ok with similar documents, Err with error message
        """
        try:
            start_time = time.time()

            # Convert dict filters to OpenSearchFilter object
            opensearch_filter = self._create_opensearch_filter(filters)
            
            # First, get the vector of the reference document
            get_query = {
                "query": {
                    "term": {
                        "record_id": record_id
                    }
                },
                "_source": ["vector"],
                "size": 1
            }
            
            response = self.client.search(index=self.index_name, body=get_query)
            
            if response["hits"]["total"]["value"] == 0:
                return Err(f"No document found with record_id: {record_id}")
            
            reference_vector = response["hits"]["hits"][0]["_source"]["vector"]
            
            # Now search for similar documents using the reference vector
            excludes = ["vector"]  # Always exclude vector fields
                
            search_query = {
                "size": size + 1,  # +1 to account for the reference document itself
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "vector": {
                                        "vector": reference_vector,
                                        "k": size + 1
                                    }
                                }
                            }
                        ],
                        "must_not": [
                            {
                                "term": {
                                    "record_id": record_id
                                }
                            }
                        ]
                    }
                },
                "_source": {
                    "excludes": excludes
                }
            }
            
            # Apply additional filters if provided
            if opensearch_filter:
                filter_clauses = opensearch_filter.to_opensearch_filters()
                if filter_clauses:
                    search_query["query"]["bool"]["filter"] = filter_clauses
            
            response = self.client.search(index=self.index_name, body=search_query)
            
            # Convert OpenSearch hits to SearchResult objects
            search_results = []
            for hit in response["hits"]["hits"]:
                search_result = SearchResult.from_opensearch_hit(hit)
                search_results.append(search_result)
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Create SearchResponse
            search_response = SearchResponse(
                results=search_results,
                total_results=response["hits"]["total"]["value"],
                search_type="similar",
                query=f"similar to record_id: {record_id}",
                execution_time_ms=execution_time,
                size=size,
                filters=filters if isinstance(filters, dict) else None
            )
            
            logger.info(f"✅ Found {len(search_results)} similar documents to record_id: {record_id}")
            return Ok(search_response)
            
        except Exception as e:
            error_msg = f"Error finding similar documents for record_id {record_id}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)

    def search_by_document(
        self,
        project_id: str,
        reference_doc_id: str,
        size: Optional[int] = None,
    ) -> Result[SearchResponse, str]:
        """
        Retrieve all chunks from a specific document within a project.
        
        Args:
            project_id: Project ID to filter by
            reference_doc_id: Reference document ID to retrieve chunks from
            size: Optional maximum number of results to return (if None, returns all chunks)
            
        Returns:
            Result[SearchResponse, str]: Ok with all document chunks, Err with error message
        """
        try:
            start_time = time.time()
            
            # Build excludes
            excludes = ["vector"]  # Always exclude vector fields
            
            # Build query to get all chunks from the specific document
            search_query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "project_id": project_id
                                }
                            },
                            {
                                "term": {
                                    "reference_doc_id": reference_doc_id
                                }
                            }
                        ]
                    }
                },
                "_source": {
                    "excludes": excludes
                },
                "sort": [
                    {"chunk_index": {"order": "asc"}}  # Sort by chunk_index to maintain order
                ]
            }
            
            # Set size if provided, otherwise use default large size to get all chunks
            if size is not None:
                search_query["size"] = size
            else:
                search_query["size"] = 10000  # Large number to get all chunks
            
            # Execute search
            response = self.client.search(index=self.index_name, body=search_query)
            
            # Process results
            search_results = []
            for hit in response["hits"]["hits"]:
                search_result = SearchResult.from_opensearch_hit(hit)
                search_results.append(search_result)
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            logger.info(f"✅ Retrieved {len(search_results)} chunks from document {reference_doc_id} in project {project_id}")
            
            search_response = SearchResponse(
                results=search_results,
                total_results=response["hits"]["total"]["value"],
                search_type="document_chunks",
                query=f"project_id: {project_id}, reference_doc_id: {reference_doc_id}",
                execution_time_ms=execution_time,
                size=size or len(search_results),
                filters={"project_id": [project_id], "reference_doc_id": [reference_doc_id]}
            )
            
            return Ok(search_response)
            
        except Exception as e:
            error_msg = f"Error retrieving chunks for document {reference_doc_id} in project {project_id}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)



class OpenSearchVectorSearchServiceFactory(ServiceFactoryABC[OpenSearchVectorSearchService]):
    """Factory for creating OpenSearchVectorSearchService instances."""
    
    @classmethod
    def create_default(cls) -> OpenSearchVectorSearchService:
        """
        Create a default OpenSearchVectorSearchService instance using app settings.
        
        Returns:
            Configured OpenSearchVectorSearchService instance
        """
        app_settings = settings_factory.create_app_settings()
        opensearch_settings = settings_factory.create_opensearch_settings()
        opensearch_client = create_opensearch_client(opensearch_settings)
        embedding_client = create_default_embedding_client()
        
        return OpenSearchVectorSearchService(
            index_name=app_settings.default_index_name,
            client=opensearch_client,
            embedding_client=embedding_client
        )
    
    @classmethod
    def from_env_file(cls, env_path: str | Path) -> OpenSearchVectorSearchService:
        """
        Create an OpenSearchVectorSearchService instance using settings from a specific environment file.

        Args:
            env_path: Path to the .env file to load settings from
        Returns:
            Configured OpenSearchVectorSearchService instance
        """
        app_settings = AppSettings.from_env_file(env_path=env_path)
        opensearch_settings = OpenSearchSettings.from_env_file(env_path=env_path)
        openai_settings = OpenAISettings.from_env_file(env_path=env_path)

        opensearch_client = create_opensearch_client(opensearch_settings)

        # Create embedding client directly with settings from env file
        embedding_client = OpenAIEmbeddingClient(
            api_key=openai_settings.api_key,
            embedding_model=openai_settings.embedding_model,
            openai_settings=openai_settings
        )

        return OpenSearchVectorSearchService(
            index_name=app_settings.default_index_name,
            client=opensearch_client,
            embedding_client=embedding_client
        )


if __name__ == "__main__":
    # Test factory methods
    logger.info("🔍 Testing OpenSearchVectorSearchServiceFactory")
