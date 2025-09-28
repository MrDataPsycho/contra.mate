from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Pydantic model for document chunk data structure."""

    id: str = Field(..., description="Unique identifier for the document chunk")
    project_id: str = Field(..., description="Project identifier")
    reference_doc_id: str = Field(..., description="Reference document identifier")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_title: str = Field(..., description="Title of the document")
    project_reference_doc_id: str = Field(..., description="Unique project reference document identifier")
    doc_source: str = Field(..., description="Document source: 'system' or 'upload'")
    contract_type: str = Field(..., description="Type of contract")
    content: str = Field(..., description="Text content for BM25 search")
    enriched_content: str = Field(..., description="Enhanced content used for embedding generation")
    embedding: List[float] = Field(..., description="Embedding vector for similarity search")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when chunk was created")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DocumentIndexConfig:
    """OpenSearch index configuration for document chunks with hybrid search capabilities."""

    @staticmethod
    def get_index_mapping(vector_dimension: int = 3072) -> Dict[str, Any]:
        """Get complete OpenSearch index configuration including settings and mappings."""
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "custom_text_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "stop",
                                "stemmer"
                            ]
                        }
                    }
                },
                "knn": True,
                "knn.algo_param.ef_search": 100,
                "knn.algo_param.ef_construction": 128,
                "knn.space_type": "cosinesimil"
            },
            "mappings": {
                "properties": {
                "id": {
                    "type": "keyword",
                    "index": True
                },
                "project_id": {
                    "type": "keyword",
                    "index": True
                },
                "reference_doc_id": {
                    "type": "keyword",
                    "index": True
                },
                "chunk_id": {
                    "type": "keyword",
                    "index": True
                },
                "document_title": {
                    "type": "text",
                    "analyzer": "custom_text_analyzer",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "doc_source": {
                    "type": "text",
                    "analyzer": "custom_text_analyzer",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "project_reference_doc_id": {
                    "type": "keyword",
                    "index": True
                },
                "created_at": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_millis"
                },
                "contract_type": {
                    "type": "keyword",
                    "index": True
                },
                "content": {
                    "type": "text",
                    "analyzer": "custom_text_analyzer",
                    "term_vector": "with_positions_offsets"
                },
                "enriched_content": {
                    "type": "text",
                    "analyzer": "custom_text_analyzer",
                    "index": False,
                    "store": True
                },
                "embedding": {
                    "type": "knn_vector",
                    "dimension": vector_dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 24
                        }
                    }
                }
            }
        }
    }


