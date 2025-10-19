from typing import Dict, Any


class DocumentIndexConfig:
    """OpenSearch index configuration for document chunks with hybrid search capabilities."""

    @staticmethod
    def get_index_mapping(vector_dimension: int) -> Dict[str, Any]:
        """Get complete OpenSearch index configuration including settings and mappings.

        Args:
            vector_dimension: Vector dimension for embeddings (must match embedding model)
        """
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
                "record_id": {
                    "type": "keyword",
                    "index": True
                },
                "chunk_id": {
                    "type": "integer",
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
                "display_name": {
                    "type": "text",
                    "analyzer": "custom_text_analyzer",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "content_source": {
                    "type": "keyword",
                    "index": True
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
                "chunk_index": {
                    "type": "integer",
                    "index": True
                },
                "section_hierarchy": {
                    "type": "keyword",
                    "index": True
                },
                "char_start": {
                    "type": "integer",
                    "index": True
                },
                "char_end": {
                    "type": "integer",
                    "index": True
                },
                "token_count": {
                    "type": "integer",
                    "index": True
                },
                "has_tables": {
                    "type": "boolean",
                    "index": True
                },
                "vector": {
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
                },
                "project_reference_doc_id": {
                    "type": "keyword",
                    "index": True
                },
                "display_name_safe": {
                    "type": "keyword",
                    "index": True
                },
                "created_at": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_millis"
                }
            }
        }
    }


