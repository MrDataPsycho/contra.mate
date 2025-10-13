"""
OpenSearch Vector CRUD Service for managing document vector operations.

This service provides CRUD operations for VectorModel documents in OpenSearch,
including automatic embedding generation using OpenAI clients.
"""

from typing import Dict, Any, Optional, List
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError
from loguru import logger
from neopipe import Result, Ok, Err

from contramate.models.vector import VectorModel, ContentSource
from contramate.utils.settings.factory import settings_factory
from contramate.llm.factory import create_default_embedding_client


class OpenSearchVectorCRUDService:
    """
    Service for CRUD operations on OpenSearch vector documents.
    """
    
    def __init__(self, index_name: Optional[str] = None, client: Optional[OpenSearch] = None):
        """
        Initialize the OpenSearch Vector CRUD Service.
        
        Args:
            index_name: Name of the OpenSearch index to operate on. If None, uses app settings default
            client: OpenSearch client instance. If None, creates client from settings
        """
        self.app_config = settings_factory.create_app_settings()
        self.opensearch_config = settings_factory.create_opensearch_settings()
        
        self.index_name = index_name or self.app_config.default_index_name
        self.client = client or self._create_client()
        self.embedding_client = create_default_embedding_client()
    
    def _create_client(self) -> OpenSearch:
        """Create OpenSearch client from settings"""
        client_config = {
            'hosts': [{'host': self.opensearch_config.host, 'port': self.opensearch_config.port}],
            'use_ssl': self.opensearch_config.use_ssl,
            'verify_certs': self.opensearch_config.verify_certs,
            'ssl_show_warn': False
        }

        # Add authentication if credentials are provided
        if self.opensearch_config.username and self.opensearch_config.password:
            client_config['http_auth'] = (self.opensearch_config.username, self.opensearch_config.password)

        return OpenSearch(**client_config)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text using the embedding client.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.embedding_client.create_embeddings(text)
            # Return the first embedding (since we're passing a single text)
            return response.embeddings[0]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def insert_document(self, document: VectorModel, auto_embed: bool = True) -> Result[VectorModel, str]:
        """
        Insert a document into the OpenSearch index.
        
        Args:
            document: VectorModel to insert
            auto_embed: If True, automatically generate embedding from content
            
        Returns:
            Result[VectorModel, str]: Ok with inserted document if successful, Err with error message if failed
        """
        try:
            # Generate embedding if requested and not already present
            if auto_embed and not document.vector:
                logger.info(f"Generating embedding for document: {document.record_id}")
                embedding = self._generate_embedding(document.content)
                # Create new document with embedding
                doc_data = document.model_dump()
                doc_data["vector"] = embedding
                document = VectorModel(**doc_data)
            
            # Convert to OpenSearch format
            formatted_document = document.to_opensearch_doc()
            
            # Insert document using record_id as OpenSearch _id
            response = self.client.index(
                index=self.index_name,
                id=document.record_id,
                body=formatted_document
            )
            
            if response.get('result') in ('created', 'updated'):
                logger.info(f"✅ Successfully inserted document with record_id: {document.record_id}")
                return Ok(document)
            else:
                error_msg = f"Failed to insert document. Response: {response}"
                logger.error(f"❌ {error_msg}")
                return Err(error_msg)
                
        except Exception as e:
            error_msg = f"Error inserting document: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def get_document_by_record_id(self, record_id: str) -> Result[Optional[VectorModel], str]:
        """
        Get a document by its record_id.
        
        Args:
            record_id: The record ID to search for
            
        Returns:
            Result[Optional[VectorModel], str]: Ok with document if found (None if not found), Err with error message if failed
        """
        try:
            response = self.client.get(index=self.index_name, id=record_id)
            
            if response.get('found'):
                doc_data = response['_source']
                logger.info(f"Found document with record_id: {record_id}")
                document = VectorModel.from_opensearch_doc(doc_data)
                return Ok(document)
            else:
                logger.info(f"No document found with record_id: {record_id}")
                return Ok(None)
                
        except NotFoundError:
            logger.info(f"No document found with record_id: {record_id}")
            return Ok(None)
        except Exception as e:
            error_msg = f"Error retrieving document with record_id '{record_id}': {str(e)}"
            logger.error(error_msg)
            return Err(error_msg)
    
    def update_document(self, document: VectorModel, auto_embed: bool = True) -> Result[VectorModel, str]:
        """
        Update a document using its record_id.
        
        Args:
            document: Updated VectorModel
            auto_embed: If True, automatically regenerate embedding from content
            
        Returns:
            Result[VectorModel, str]: Ok with updated document if successful, Err with error message if failed
        """
        try:
            # Generate embedding if requested
            if auto_embed:
                logger.info(f"Regenerating embedding for document: {document.record_id}")
                embedding = self._generate_embedding(document.content)
                # Create new document with updated embedding
                doc_data = document.model_dump()
                doc_data["vector"] = embedding
                document = VectorModel(**doc_data)
            
            # Convert to OpenSearch format
            formatted_document = document.to_opensearch_doc()
            
            # Update document
            response = self.client.index(
                index=self.index_name,
                id=document.record_id,
                body=formatted_document
            )
            
            if response.get('result') in ('updated', 'created'):
                logger.info(f"✅ Successfully updated document with record_id: {document.record_id}")
                return Ok(document)
            else:
                error_msg = f"Failed to update document. Response: {response}"
                logger.error(f"❌ {error_msg}")
                return Err(error_msg)
                
        except Exception as e:
            error_msg = f"Error updating document with record_id {document.record_id}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def delete_document_by_record_id(self, record_id: str) -> Result[str, str]:
        """
        Delete a document using its record_id.
        
        Args:
            record_id: Record ID of the document to delete
            
        Returns:
            Result[str, str]: Ok with success message if deletion was successful, Err with error message if failed
        """
        try:
            response = self.client.delete(index=self.index_name, id=record_id)
            
            if response.get('result') == 'deleted':
                success_msg = f"Successfully deleted document with record_id: {record_id}"
                logger.info(f"✅ {success_msg}")
                return Ok(success_msg)
            else:
                error_msg = f"Document with record_id {record_id} not found or could not be deleted. Response: {response}"
                logger.warning(f"⚠️ {error_msg}")
                return Err(error_msg)
                
        except NotFoundError:
            error_msg = f"Document with record_id {record_id} not found"
            logger.warning(f"⚠️ {error_msg}")
            return Err(error_msg)
        except Exception as e:
            error_msg = f"Error deleting document with record_id {record_id}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)

    def upsert_document(self, document: VectorModel, auto_embed: bool = True) -> Result[VectorModel, str]:
        """
        Upsert (insert or update) a document based on record_id.
        
        Args:
            document: VectorModel to upsert
            auto_embed: If True, automatically generate/regenerate embedding
            
        Returns:
            Result[VectorModel, str]: Ok with upserted document if successful, Err with error message if failed
        """
        try:
            # Check if document exists
            get_result = self.get_document_by_record_id(document.record_id)
            
            if get_result.is_err():
                return Err(f"Error checking if document exists: {get_result.err()}")
            
            existing_doc = get_result.unwrap()
            
            if existing_doc:
                logger.info(f"Document with record_id '{document.record_id}' exists. Updating...")
                return self.update_document(document, auto_embed=auto_embed)
            else:
                logger.info(f"No existing document found with record_id '{document.record_id}'. Inserting new document...")
                return self.insert_document(document, auto_embed=auto_embed)
                
        except Exception as e:
            error_msg = f"Error upserting document: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def insert_document_if_not_exists(self, document: VectorModel, auto_embed: bool = True) -> Result[Optional[VectorModel], str]:
        """
        Insert a document only if no document with the same record_id exists.
        
        Args:
            document: VectorModel to insert
            auto_embed: If True, automatically generate embedding
            
        Returns:
            Result[Optional[VectorModel], str]: Ok with inserted document if successful (None if already exists), Err with error message if failed
        """
        try:
            # Check if document already exists
            get_result = self.get_document_by_record_id(document.record_id)
            
            if get_result.is_err():
                return Err(f"Error checking if document exists: {get_result.err()}")
            
            existing_doc = get_result.unwrap()
            
            if existing_doc:
                logger.info(f"Document with record_id '{document.record_id}' already exists. Skipping insertion.")
                return Ok(None)
            else:
                logger.info(f"No existing document found with record_id '{document.record_id}'. Inserting new document...")
                insert_result = self.insert_document(document, auto_embed=auto_embed)
                if insert_result.is_err():
                    return Err(insert_result.err())
                return Ok(insert_result.unwrap())
                
        except Exception as e:
            error_msg = f"Error inserting document if not exists: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def bulk_insert_documents(self, documents: List[VectorModel], auto_embed: bool = True) -> Result[Dict[str, int], str]:
        """
        Bulk insert multiple documents (will overwrite existing documents with same record_id).
        For upsert behavior that checks existence, use bulk_upsert_documents instead.
        
        Args:
            documents: List of VectorModel documents to insert
            auto_embed: If True, automatically generate embeddings
            
        Returns:
            Result[Dict[str, int], str]: Ok with success/failure counts if successful, Err with error message if failed
        """
        try:
            bulk_body = []
            
            for document in documents:
                # Generate embedding if requested and not already present
                if auto_embed and not document.vector:
                    logger.info(f"Generating embedding for document: {document.record_id}")
                    embedding = self._generate_embedding(document.content)
                    doc_data = document.model_dump()
                    doc_data["vector"] = embedding
                    document = VectorModel(**doc_data)
                
                # Add index action
                bulk_body.append({
                    "index": {
                        "_index": self.index_name,
                        "_id": document.record_id
                    }
                })
                
                # Add document
                bulk_body.append(document.to_opensearch_doc())
            
            # Execute bulk operation
            response = self.client.bulk(body=bulk_body)
            
            success_count = 0
            error_count = 0
            
            for item in response.get('items', []):
                if 'index' in item:
                    if item['index'].get('status') in [200, 201]:
                        success_count += 1
                    else:
                        error_count += 1
                        logger.error(f"Failed to index document: {item}")
            
            logger.info(f"✅ Bulk insert completed: {success_count} successful, {error_count} failed")
            
            return Ok({
                "success": success_count,
                "failed": error_count,
                "total": len(documents)
            })
            
        except Exception as e:
            error_msg = f"Error in bulk insert: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)

    def bulk_upsert_documents(self, documents: List[VectorModel], auto_embed: bool = True) -> Result[Dict[str, int], str]:
        """
        Bulk upsert multiple documents - checks if record exists and only updates if it exists, 
        otherwise inserts new records. Prevents duplicates at OpenSearch level.
        
        Args:
            documents: List of VectorModel documents to upsert
            auto_embed: If True, automatically generate embeddings
            
        Returns:
            Result[Dict[str, int], str]: Ok with counts (inserted, updated, failed), Err with error message if failed
        """
        try:
            # First, check which documents already exist
            record_ids = [doc.record_id for doc in documents]
            existing_docs = {}
            
            if record_ids:
                # Use multi-get to check existence efficiently
                try:
                    mget_response = self.client.mget(
                        index=self.index_name,
                        body={"ids": record_ids},
                        _source=False  # We only need to know if they exist
                    )
                    
                    for doc_info in mget_response.get("docs", []):
                        if doc_info.get("found"):
                            existing_docs[doc_info["_id"]] = True
                except Exception as e:
                    logger.warning(f"Could not check existing documents, proceeding with upsert: {e}")
            
            bulk_body = []
            inserted_count = 0
            updated_count = 0
            
            for document in documents:
                # Generate embedding if requested and not already present
                if auto_embed and not document.vector:
                    logger.info(f"Generating embedding for document: {document.record_id}")
                    embedding = self._generate_embedding(document.content)
                    doc_data = document.model_dump()
                    doc_data["vector"] = embedding
                    document = VectorModel(**doc_data)
                
                # Determine if this is an insert or update
                is_update = document.record_id in existing_docs
                
                if is_update:
                    # Use update operation for existing documents
                    bulk_body.append({
                        "update": {
                            "_index": self.index_name,
                            "_id": document.record_id
                        }
                    })
                    bulk_body.append({
                        "doc": document.to_opensearch_doc(),
                        "doc_as_upsert": True
                    })
                    updated_count += 1
                    logger.debug(f"Updating existing document: {document.record_id}")
                else:
                    # Use index operation for new documents
                    bulk_body.append({
                        "index": {
                            "_index": self.index_name,
                            "_id": document.record_id
                        }
                    })
                    bulk_body.append(document.to_opensearch_doc())
                    inserted_count += 1
                    logger.debug(f"Inserting new document: {document.record_id}")
            
            # Execute bulk operation
            response = self.client.bulk(body=bulk_body)
            
            success_count = 0
            error_count = 0
            
            for item in response.get('items', []):
                # Check both index and update operations
                operation_result = item.get('index') or item.get('update')
                if operation_result:
                    if operation_result.get('status') in [200, 201]:
                        success_count += 1
                    else:
                        error_count += 1
                        logger.error(f"Failed to upsert document: {item}")
            
            logger.info(f"✅ Bulk upsert completed: {success_count} successful ({inserted_count} inserted, {updated_count} updated), {error_count} failed")
            
            return Ok({
                "success": success_count,
                "failed": error_count,
                "total": len(documents),
                "inserted": inserted_count,
                "updated": updated_count
            })
            
        except Exception as e:
            error_msg = f"Error in bulk upsert: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return Err(error_msg)
    
    def search_by_project_id(self, project_id: str, limit: int = 100) -> Result[List[VectorModel], str]:
        """
        Search documents by project_id.
        
        Args:
            project_id: Project ID to search for
            limit: Maximum number of documents to return
            
        Returns:
            Result[List[VectorModel], str]: Ok with document list if successful, Err with error message if failed
        """
        try:
            search_query = {
                "query": {
                    "term": {
                        "project_id": project_id
                    }
                },
                "size": limit
            }
            
            response = self.client.search(index=self.index_name, body=search_query)
            
            documents = []
            for hit in response["hits"]["hits"]:
                doc_data = hit["_source"]
                documents.append(VectorModel.from_opensearch_doc(doc_data))
            
            logger.info(f"Found {len(documents)} documents for project_id: {project_id}")
            return Ok(documents)
            
        except Exception as e:
            error_msg = f"Error searching documents by project_id '{project_id}': {str(e)}"
            logger.error(error_msg)
            return Err(error_msg)
    
    def semantic_search(self, query_text: str, limit: int = 10, project_id: Optional[str] = None) -> Result[List[Dict[str, Any]], str]:
        """
        Perform semantic search using vector similarity.
        
        Args:
            query_text: Text to search for
            limit: Maximum number of results to return
            project_id: Optional project_id filter
            
        Returns:
            Result[List[Dict[str, Any]], str]: Ok with search results if successful, Err with error message if failed
        """
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)
            
            # Build search query
            search_query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "vector": {
                                        "vector": query_embedding,
                                        "k": limit
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": limit
            }
            
            # Add project filter if specified
            if project_id:
                search_query["query"]["bool"]["filter"] = [
                    {"term": {"project_id": project_id}}
                ]
            
            response = self.client.search(index=self.index_name, body=search_query)
            
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "document": VectorModel.from_opensearch_doc(hit["_source"]),
                    "score": hit["_score"],
                    "record_id": hit["_id"]
                }
                results.append(result)
            
            logger.info(f"Semantic search returned {len(results)} results for query: '{query_text[:50]}...'")
            return Ok(results)
            
        except Exception as e:
            error_msg = f"Error in semantic search: {str(e)}"
            logger.error(error_msg)
            return Err(error_msg)
    
    def get_document_count(self) -> Result[int, str]:
        """
        Get the total number of documents in the index.
        
        Returns:
            Result[int, str]: Ok with document count if successful, Err with error message if failed
        """
        try:
            response = self.client.count(index=self.index_name)
            count = response.get("count", 0)
            logger.info(f"Index '{self.index_name}' contains {count} documents")
            return Ok(count)
        except Exception as e:
            error_msg = f"Error getting document count for index '{self.index_name}': {str(e)}"
            logger.error(error_msg)
            return Err(error_msg)


class OpenSearchVectorCRUDServiceFactory:
    """
    Factory class for creating OpenSearchVectorCRUDService instances.
    """
    
    @staticmethod
    def create_default(
        index_name: Optional[str] = None, 
        client: Optional[OpenSearch] = None
    ) -> OpenSearchVectorCRUDService:
        """
        Create default OpenSearchVectorCRUDService instance.
        
        Args:
            index_name: Optional index name (uses app settings default if None)
            client: Optional OpenSearch client instance
            
        Returns:
            OpenSearchVectorCRUDService instance
        """
        return OpenSearchVectorCRUDService(index_name=index_name, client=client)
    
    @staticmethod
    def create(
        index_name: Optional[str] = None, 
        client: Optional[OpenSearch] = None
    ) -> OpenSearchVectorCRUDService:
        """
        Create OpenSearchVectorCRUDService instance with custom configuration.
        
        Args:
            index_name: Optional index name (uses app settings default if None)
            client: Optional OpenSearch client instance
            
        Returns:
            OpenSearchVectorCRUDService instance
        """
        return OpenSearchVectorCRUDService(index_name=index_name, client=client)


def main():
    """Main function to test the CRUD service"""
    from datetime import datetime, timezone
    
    # Test the CRUD service
    crud_service = OpenSearchVectorCRUDServiceFactory.create_default()
    
    # Create a test document
    test_doc = VectorModel(
        chunk_id=1,
        project_id="test-project",
        reference_doc_id="test-doc",
        document_title="Test Contract",
        content_source=ContentSource.upload,
        contract_type="service_agreement",
        content="This is a test contract with important legal terms and conditions.",
        chunk_index=0,
        section_hierarchy=["Introduction"],
        char_start=0,
        char_end=100,
        token_count=20,
        has_tables=False,
        vector=[],  # Will be auto-generated
        created_at=datetime.now(timezone.utc)
    )
    
    logger.info(f"Test document record_id: {test_doc.record_id}")
    
    # Test insertion with auto-embedding
    insert_result = crud_service.insert_document(test_doc, auto_embed=True)
    if insert_result.is_ok():
        inserted_doc = insert_result.unwrap()
        logger.info(f"✅ Insert successful: {inserted_doc.record_id}")
    else:
        logger.error(f"❌ Insert failed: {insert_result.err()}")
        return
    
    # Test retrieval
    get_result = crud_service.get_document_by_record_id(test_doc.record_id)
    if get_result.is_ok():
        retrieved_doc = get_result.unwrap()
        if retrieved_doc:
            logger.info(f"✅ Retrieved document: {retrieved_doc.document_title}")
            logger.info(f"Vector dimension: {len(retrieved_doc.vector)}")
        else:
            logger.info("Document not found")
    else:
        logger.error(f"❌ Retrieval failed: {get_result.err()}")
    
    # Test document count
    count_result = crud_service.get_document_count()
    if count_result.is_ok():
        count = count_result.unwrap()
        logger.info(f"✅ Total documents in index: {count}")
    else:
        logger.error(f"❌ Count failed: {count_result.err()}")
    
    # Test semantic search
    search_result = crud_service.semantic_search("legal contract terms", limit=5)
    if search_result.is_ok():
        search_results = search_result.unwrap()
        logger.info(f"✅ Semantic search returned {len(search_results)} results")
    else:
        logger.error(f"❌ Semantic search failed: {search_result.err()}")


if __name__ == "__main__":
    main()