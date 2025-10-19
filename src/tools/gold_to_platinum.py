#!/usr/bin/env python3
"""
Tool to read chunked documents from gold layer and convert to platinum (vector) layer.

Pipeline:
1. Read contract metadata from database
2. Load chunked documents from gold layer (JSON files)
3. Convert to PlatinumModel instances with embeddings (async)
4. Index to OpenSearch vector database
5. Track indexing status in document_indexing_status table

Usage:
    # Read documents from gold layer
    uv run python src/tools/gold_to_platinum.py read --limit 1

    # Generate embeddings and create platinum models
    uv run python src/tools/gold_to_platinum.py embed --limit 1

    # Generate embeddings and index to OpenSearch (complete platinum pipeline with status tracking)
    uv run python src/tools/gold_to_platinum.py index --limit 10 --batch-size 20

    # Verify indexing status
    uv run python src/tools/gold_to_platinum.py verify --limit 10

    # Retry only failed documents (with slower delay to avoid rate limits)
    uv run python src/tools/gold_to_platinum.py retry-failed --delay 2.0

    # Clean database status and OpenSearch index (fresh start)
    uv run python src/tools/gold_to_platinum.py clean --confirm
"""

import asyncio
from pathlib import Path
from typing import Optional, List

from loguru import logger
from sqlmodel import Session, create_engine, select

from contramate.dbs.models.contract import ContractAsmd
from contramate.dbs.models.document_status import DocumentIndexingStatus, ProcessingStatus
from contramate.models.document import ChunkedDocument, Chunk
from contramate.models.platinum import PlatinumModel
from contramate.models.gold import DocumentSource
from contramate.llm.litellm_embedding_client import LiteLLMEmbeddingClient
from contramate.utils.settings.factory import settings_factory
from contramate.services import platinum_cache_service
from contramate.services.markdown_chunking_service import MarkdownChunkingService
from contramate.models import DocumentInfo
import tiktoken


# Paths
GOLD_BASE_PATH = Path("data/gold")


def rechunk_oversized_document(
    chunked_doc: ChunkedDocument,
    max_tokens: int = 8000,
    target_chunk_size: int = 4000
) -> ChunkedDocument:
    """
    Re-chunk a document with oversized chunks using the markdown chunking service.

    Args:
        chunked_doc: Original chunked document with oversized chunks
        max_tokens: Maximum token limit (chunks exceeding this will be split)
        target_chunk_size: Target size for new chunks

    Returns:
        New ChunkedDocument with properly sized chunks
    """
    logger.info(f"Re-chunking document {chunked_doc.filename} with oversized chunks")

    # Reconstruct markdown from chunks
    reconstructed_markdown = "\n\n".join([chunk.content for chunk in chunked_doc.chunks])

    # Create DocumentInfo for rechunking
    doc_info = DocumentInfo(
        project_id=chunked_doc.project_id,
        reference_doc_id=chunked_doc.reference_doc_id,
        filename=chunked_doc.filename,
        contract_type=chunked_doc.contract_type
    )

    # Use markdown chunking service to rechunk with smaller target size
    chunking_service = MarkdownChunkingService(
        markdown_content=reconstructed_markdown,
        doc_info=doc_info,
        token_limit=target_chunk_size,  # Use smaller chunks for safety
        min_chunk_size=100
    )

    rechunked_doc = chunking_service.process_markdown_to_chunks()

    # Verify and fix token counts (recalculate to ensure accuracy)
    encoding = tiktoken.get_encoding("o200k_base")
    for chunk in rechunked_doc.chunks:
        actual_token_count = len(encoding.encode(chunk.content))
        if actual_token_count != chunk.token_count:
            logger.debug(f"Fixing token count for chunk {chunk.chunk_index}: {chunk.token_count} → {actual_token_count}")
            chunk.token_count = actual_token_count

    max_tokens_after = max(c.token_count for c in rechunked_doc.chunks)

    # If still have oversized chunks, apply brute-force token-based splitting
    if max_tokens_after > max_tokens:
        logger.warning(f"Markdown chunking didn't fully split oversized chunks. Applying token-based splitting...")

        final_chunks = []
        for chunk in rechunked_doc.chunks:
            if chunk.token_count > max_tokens:
                logger.info(f"Force-splitting chunk {chunk.chunk_index} ({chunk.token_count} tokens)")

                # Tokenize and split by target size
                tokens = encoding.encode(chunk.content)
                for i in range(0, len(tokens), target_chunk_size):
                    token_slice = tokens[i:i + target_chunk_size]
                    sub_chunk_content = encoding.decode(token_slice)

                    # Create new sub-chunk
                    sub_chunk = Chunk(
                        content=sub_chunk_content,
                        chunk_index=0,  # Will be renumbered later
                        section_hierarchy=chunk.section_hierarchy,
                        char_start=chunk.char_start + i * 4,  # Approximate
                        char_end=chunk.char_start + (i + len(token_slice)) * 4,
                        token_count=len(token_slice),
                        has_tables=chunk.has_tables
                    )
                    final_chunks.append(sub_chunk)
            else:
                final_chunks.append(chunk)

        # Renumber chunks
        for i, chunk in enumerate(final_chunks, 1):
            chunk.chunk_index = i

        rechunked_doc.chunks = final_chunks
        rechunked_doc.total_chunks = len(final_chunks)

        max_tokens_after = max(c.token_count for c in rechunked_doc.chunks)
        logger.info(f"After force-splitting: {rechunked_doc.total_chunks} chunks, max {max_tokens_after} tokens")

    logger.info(f"Re-chunked: {chunked_doc.total_chunks} chunks → {rechunked_doc.total_chunks} chunks")
    logger.info(f"Max tokens in new chunks: {max_tokens_after}")

    return rechunked_doc


def find_gold_json_file(project_id: str, reference_doc_id: str, filename: str) -> Optional[Path]:
    """
    Find chunked JSON file in gold directory.

    Args:
        project_id: Project identifier
        reference_doc_id: Document identifier (internal doc ID)
        filename: Original filename (with .md extension)

    Returns:
        Path to JSON file or None if not found
    """
    json_path = GOLD_BASE_PATH / project_id / reference_doc_id / f"{filename}.json"

    if json_path.exists():
        return json_path

    logger.warning(f"JSON file not found: {json_path}")
    return None


def load_chunked_document(json_path: Path) -> ChunkedDocument:
    """
    Load chunked document from JSON file using ChunkedDocument model.

    Args:
        json_path: Path to JSON file

    Returns:
        ChunkedDocument instance
    """
    chunked_doc = ChunkedDocument.load_json(json_path)
    return chunked_doc


async def convert_chunk_to_platinum_model(
    chunk: Chunk,
    chunked_doc: ChunkedDocument,
    embedding_client: LiteLLMEmbeddingClient
) -> PlatinumModel:
    """
    Convert a single chunk to PlatinumModel with embedding (async).

    Args:
        chunk: Chunk instance
        chunked_doc: Parent ChunkedDocument for metadata
        embedding_client: Embedding client for generating embeddings

    Returns:
        PlatinumModel with embedding
    """
    # Generate embedding for chunk content
    embedding_response = await embedding_client.async_create_embeddings(
        texts=[chunk.content]
    )

    if not embedding_response.embeddings or len(embedding_response.embeddings) == 0:
        raise ValueError(f"Failed to generate embedding for chunk {chunk.chunk_index}")

    embedding_vector = embedding_response.embeddings[0]

    # Create PlatinumModel
    chunk_id = chunk.chunk_index + 1  # chunk_id starts from 1
    display_name = f"{chunked_doc.filename}-{chunk_id}"

    platinum_model = PlatinumModel(
        chunk_id=chunk_id,
        project_id=chunked_doc.project_id,
        reference_doc_id=chunked_doc.reference_doc_id,
        document_title=chunked_doc.filename,
        display_name=display_name,
        content_source=DocumentSource.system,
        contract_type=chunked_doc.contract_type,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        section_hierarchy=chunk.section_hierarchy,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
        token_count=chunk.token_count,
        has_tables=chunk.has_tables,
        vector=embedding_vector
    )

    return platinum_model


async def convert_document_to_platinum_models(
    chunked_doc: ChunkedDocument,
    embedding_client: LiteLLMEmbeddingClient
) -> List[PlatinumModel]:
    """
    Convert all chunks in a document to PlatinumModels with embeddings (async).

    Args:
        chunked_doc: ChunkedDocument instance
        embedding_client: Embedding client

    Returns:
        List of PlatinumModel instances with embeddings
    """
    logger.info(f"Converting {len(chunked_doc.chunks)} chunks to PlatinumModels for document {chunked_doc.reference_doc_id}")

    # Create tasks for parallel embedding generation
    tasks = [
        convert_chunk_to_platinum_model(chunk, chunked_doc, embedding_client)
        for chunk in chunked_doc.chunks
    ]

    # Run all embedding tasks in parallel
    platinum_models = await asyncio.gather(*tasks)

    logger.info(f"Successfully converted {len(platinum_models)} chunks to PlatinumModels")

    return platinum_models


if __name__ == "__main__":
    import typer

    app = typer.Typer()

    @app.command()
    def read(
        limit: Optional[int] = typer.Option(
            None,
            "--limit",
            "-l",
            help="Limit number of documents to process"
        )
    ):
        """Read and display documents from gold layer"""

        # Create database connection
        postgres_settings = settings_factory.create_postgres_settings()
        connection_string = postgres_settings.connection_string
        engine = create_engine(connection_string, echo=False)

        logger.info("Starting gold layer document reading")
        logger.info(f"Gold directory: {GOLD_BASE_PATH}")

        total_documents = 0
        loaded = 0
        not_found = 0
        failed = 0

        with Session(engine) as session:
            # Get contracts from database
            statement = select(ContractAsmd)
            if limit:
                statement = statement.limit(limit)

            contracts = session.exec(statement).all()
            total_documents = len(contracts)

            logger.info(f"Found {total_documents} contracts in database\n")

            for contract in contracts:
                project_id = contract.project_id
                reference_doc_id = contract.reference_doc_id

                # For now, we need to find the actual filename
                # We'll look for JSON files in the directory
                doc_dir = GOLD_BASE_PATH / project_id / reference_doc_id

                if not doc_dir.exists():
                    logger.warning(f"Directory not found: {doc_dir}")
                    not_found += 1
                    continue

                # Find JSON files in the directory
                json_files = list(doc_dir.glob("*.json"))

                if not json_files:
                    logger.warning(f"No JSON files found in: {doc_dir}")
                    not_found += 1
                    continue

                # Load the first JSON file found
                json_file = json_files[0]

                try:
                    chunked_doc = load_chunked_document(json_file)

                    logger.info(f"Successfully loaded:")
                    logger.info(f"  Project ID: {chunked_doc.project_id}")
                    logger.info(f"  Reference Doc ID: {chunked_doc.reference_doc_id}")
                    logger.info(f"  Filename: {chunked_doc.filename}")
                    logger.info(f"  Contract Type: {chunked_doc.contract_type}")
                    logger.info(f"  Total Chunks: {chunked_doc.total_chunks}")

                    # Show first chunk preview
                    if chunked_doc.chunks:
                        first_chunk = chunked_doc.chunks[0]
                        logger.info(f"  First Chunk - Index: {first_chunk.chunk_index}, Tokens: {first_chunk.token_count}")
                        logger.info(f"  Content Preview: {first_chunk.content[:100]}...")

                    logger.info("")
                    loaded += 1

                except Exception as e:
                    logger.error(f"Failed to load document from {json_file}: {e}")
                    failed += 1

        # Summary
        logger.info("\n=== Summary ===")
        logger.info(f"Total documents in database: {total_documents}")
        logger.info(f"Successfully loaded: {loaded}")
        logger.info(f"Not found in gold layer: {not_found}")
        logger.info(f"Failed to load: {failed}")

    @app.command()
    def embed(
        limit: Optional[int] = typer.Option(
            1,
            "--limit",
            "-l",
            help="Limit number of documents to process"
        )
    ):
        """Generate embeddings for documents from gold layer"""

        # Create database connection
        postgres_settings = settings_factory.create_postgres_settings()
        connection_string = postgres_settings.connection_string
        engine = create_engine(connection_string, echo=False)

        # Initialize embedding client
        logger.info("Initializing embedding client...")
        try:
            embedding_client = LiteLLMEmbeddingClient()
            logger.info("✓ Embedding client initialized\n")
        except Exception as e:
            logger.error(f"Failed to initialize embedding client: {e}")
            return

        logger.info("Starting embedding generation")
        logger.info(f"Gold directory: {GOLD_BASE_PATH}")

        total_documents = 0
        processed = 0
        not_found = 0
        failed = 0
        total_vectors_created = 0

        async def process_documents():
            nonlocal total_documents, processed, not_found, failed, total_vectors_created

            with Session(engine) as session:
                # Get contracts from database
                statement = select(ContractAsmd)
                if limit:
                    statement = statement.limit(limit)

                contracts = session.exec(statement).all()
                total_documents = len(contracts)

                logger.info(f"Found {total_documents} contracts in database\n")

                for contract in contracts:
                    project_id = contract.project_id
                    reference_doc_id = contract.reference_doc_id

                    # Find JSON file
                    doc_dir = GOLD_BASE_PATH / project_id / reference_doc_id

                    if not doc_dir.exists():
                        logger.warning(f"Directory not found: {doc_dir}")
                        not_found += 1
                        continue

                    json_files = list(doc_dir.glob("*.json"))

                    if not json_files:
                        logger.warning(f"No JSON files found in: {doc_dir}")
                        not_found += 1
                        continue

                    json_file = json_files[0]

                    try:
                        # Load chunked document
                        chunked_doc = load_chunked_document(json_file)

                        logger.info(f"Processing document: {chunked_doc.filename}")
                        logger.info(f"  Chunks to process: {len(chunked_doc.chunks)}")

                        # Convert to PlatinumModels with embeddings
                        platinum_models = await convert_document_to_platinum_models(
                            chunked_doc,
                            embedding_client
                        )

                        # Display sample results
                        logger.info(f"✓ Created {len(platinum_models)} platinum models")
                        if platinum_models:
                            first_model = platinum_models[0]
                            logger.info(f"  Sample Platinum Model:")
                            logger.info(f"    Record ID: {first_model.record_id}")
                            logger.info(f"    Chunk ID: {first_model.chunk_id}")
                            logger.info(f"    Display Name: {first_model.display_name}")
                            logger.info(f"    Vector dimension: {len(first_model.vector)}")
                            logger.info(f"    Content preview: {first_model.content[:100]}...")

                            # Show OpenSearch document format
                            opensearch_doc = first_model.to_opensearch_doc()
                            logger.info(f"  OpenSearch Document Keys: {list(opensearch_doc.keys())}")

                        processed += 1
                        total_vectors_created += len(platinum_models)
                        logger.info("")

                    except Exception as e:
                        logger.error(f"Failed to process document from {json_file}: {e}")
                        failed += 1

        # Run async processing
        asyncio.run(process_documents())

        # Summary
        logger.info("\n=== Embedding Summary ===")
        logger.info(f"Total documents in database: {total_documents}")
        logger.info(f"Successfully processed: {processed}")
        logger.info(f"Total platinum models created: {total_vectors_created}")
        logger.info(f"Not found in gold layer: {not_found}")
        logger.info(f"Failed to process: {failed}")

    @app.command()
    def index(
        limit: Optional[int] = typer.Option(
            None,
            "--limit",
            "-l",
            help="Limit number of documents to process (processes all if not specified)"
        ),
        batch_size: int = typer.Option(
            10,
            "--batch-size",
            "-b",
            help="Number of documents to index in each batch"
        ),
        index_name: Optional[str] = typer.Option(
            None,
            "--index",
            "-i",
            help="OpenSearch index name (uses default from settings if not provided)"
        ),
        skip_existing: bool = typer.Option(
            True,
            "--skip-existing/--reprocess",
            help="Skip documents already indexed in OpenSearch"
        ),
        delay_seconds: float = typer.Option(
            0.1,
            "--delay",
            "-d",
            help="Delay in seconds between processing documents (helps avoid rate limits)"
        ),
        skip_cache: bool = typer.Option(
            False,
            "--skip-cache",
            help="Skip cache and force regeneration of embeddings"
        )
    ):
        """Generate embeddings and index platinum models to OpenSearch"""
        import time
        from datetime import datetime, timezone
        from contramate.services.opensearch_vector_crud_service import OpenSearchVectorCRUDServiceFactory
        from contramate.services.opensearch_infra_service import create_opensearch_infra_service

        # Create database connection
        postgres_settings = settings_factory.create_postgres_settings()
        connection_string = postgres_settings.connection_string
        engine = create_engine(connection_string, echo=False)

        # Get app settings for vector dimension
        app_settings = settings_factory.create_app_settings()

        # Initialize embedding client
        logger.info("Initializing embedding client...")
        try:
            embedding_client = LiteLLMEmbeddingClient()
            logger.info("✓ Embedding client initialized\n")
        except Exception as e:
            logger.error(f"Failed to initialize embedding client: {e}")
            return

        # Initialize OpenSearch services
        logger.info("Initializing OpenSearch services...")
        try:
            infra_service = create_opensearch_infra_service()
            crud_service = OpenSearchVectorCRUDServiceFactory.create_default(index_name=index_name)

            # Get cluster health
            health = infra_service.get_cluster_health()
            if not health.get("healthy"):
                logger.error(f"OpenSearch cluster is not healthy: {health}")
                return

            logger.info(f"✓ OpenSearch cluster healthy: {health.get('status')}")
            logger.info(f"✓ Target index: {crud_service.index_name}\n")
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch services: {e}")
            return

        logger.info("Starting indexing process")
        logger.info(f"Gold directory: {GOLD_BASE_PATH}")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Skip existing: {skip_existing}")
        logger.info(f"Delay between docs: {delay_seconds}s\n")

        total_documents = 0
        processed = 0
        not_found = 0
        failed = 0
        skipped = 0
        total_indexed = 0

        async def process_and_index_documents():
            nonlocal total_documents, processed, not_found, failed, skipped, total_indexed

            with Session(engine) as session:
                # Get contracts from database
                statement = select(ContractAsmd)
                if limit:
                    statement = statement.limit(limit)

                contracts = session.exec(statement).all()
                total_documents = len(contracts)

                logger.info(f"Found {total_documents} contracts in database\n")

                # Batch processing
                batch = []
                batch_status_records = []  # Track status records for documents in current batch
                batch_count = 0

                for contract in contracts:
                    project_id = contract.project_id
                    reference_doc_id = contract.reference_doc_id

                    # Check if already processed (using database status)
                    if skip_existing:
                        existing_status = session.exec(
                            select(DocumentIndexingStatus).where(
                                DocumentIndexingStatus.project_id == project_id,
                                DocumentIndexingStatus.reference_doc_id == reference_doc_id,
                                DocumentIndexingStatus.status == ProcessingStatus.PROCESSED
                            )
                        ).first()

                        if existing_status:
                            logger.info(f"⊘ Skipping already processed document: {project_id}/{reference_doc_id}")
                            skipped += 1
                            continue

                    # Find JSON file
                    doc_dir = GOLD_BASE_PATH / project_id / reference_doc_id

                    if not doc_dir.exists():
                        logger.warning(f"Directory not found: {doc_dir}")
                        not_found += 1
                        continue

                    json_files = list(doc_dir.glob("*.json"))

                    if not json_files:
                        logger.warning(f"No JSON files found in: {doc_dir}")
                        not_found += 1
                        continue

                    json_file = json_files[0]

                    # Initialize status record
                    status_record = session.exec(
                        select(DocumentIndexingStatus).where(
                            DocumentIndexingStatus.project_id == project_id,
                            DocumentIndexingStatus.reference_doc_id == reference_doc_id
                        )
                    ).first()

                    if not status_record:
                        status_record = DocumentIndexingStatus(
                            project_id=project_id,
                            reference_doc_id=reference_doc_id,
                            status=ProcessingStatus.READY,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc)
                        )
                        session.add(status_record)
                    else:
                        status_record.status = ProcessingStatus.READY
                        status_record.updated_at = datetime.now(timezone.utc)

                    session.commit()
                    session.refresh(status_record)

                    # Track start time
                    doc_start_time = time.time()

                    try:
                        # Load chunked document
                        chunked_doc = load_chunked_document(json_file)

                        # Check for oversized chunks that exceed embedding model limit
                        max_tokens = max(chunk.token_count for chunk in chunked_doc.chunks)
                        if max_tokens > 8000:
                            logger.warning(f"⚠ Document has oversized chunk ({max_tokens} tokens > 8000 limit): {chunked_doc.filename}")
                            logger.info(f"  Attempting automatic re-chunking...")

                            try:
                                # Automatically rechunk the document with smaller target size
                                chunked_doc = rechunk_oversized_document(
                                    chunked_doc,
                                    max_tokens=8000,
                                    target_chunk_size=4000  # Use 4K chunks for safety margin
                                )

                                # Verify rechunking worked
                                new_max_tokens = max(chunk.token_count for chunk in chunked_doc.chunks)
                                if new_max_tokens > 8000:
                                    logger.error(f"✗ Re-chunking failed, still have {new_max_tokens} token chunk")
                                    skipped += 1
                                    continue

                                logger.info(f"✓ Successfully re-chunked document: max {new_max_tokens} tokens")
                            except Exception as e:
                                logger.error(f"✗ Re-chunking failed: {e}")
                                skipped += 1
                                continue

                        logger.info(f"Processing document: {chunked_doc.filename}")
                        logger.info(f"  Chunks to process: {len(chunked_doc.chunks)}")

                        # Try to load from cache first (unless skip_cache is True)
                        platinum_models = None
                        if not skip_cache:
                            # Check if cache is valid (exists and newer than gold file)
                            if platinum_cache_service.is_cache_valid(
                                project_id, reference_doc_id, chunked_doc.filename, json_file
                            ):
                                platinum_models = platinum_cache_service.load_platinum_models_from_cache(
                                    project_id, reference_doc_id, chunked_doc.filename
                                )
                                if platinum_models:
                                    logger.info(f"✓ Loaded {len(platinum_models)} platinum models from cache")

                        # If not in cache or skip_cache=True, generate embeddings
                        if platinum_models is None:
                            # Convert to PlatinumModels with embeddings
                            platinum_models = await convert_document_to_platinum_models(
                                chunked_doc,
                                embedding_client
                            )
                            logger.info(f"✓ Created {len(platinum_models)} platinum models")

                            # Save to cache for future use
                            try:
                                platinum_cache_service.save_platinum_models_to_cache(
                                    platinum_models,
                                    project_id,
                                    reference_doc_id,
                                    chunked_doc.filename
                                )
                                logger.debug(f"Cached platinum models for {chunked_doc.filename}")
                            except Exception as e:
                                logger.warning(f"Failed to cache platinum models: {e}")

                        # Add to batch
                        batch.extend(platinum_models)
                        batch_status_records.append({
                            "status_record": status_record,
                            "num_chunks": len(platinum_models),
                            "start_time": doc_start_time
                        })
                        processed += 1

                        # Add delay to avoid rate limits
                        if delay_seconds > 0:
                            await asyncio.sleep(delay_seconds)

                        # Index batch when it reaches batch_size
                        if len(batch) >= batch_size:
                            batch_count += 1
                            logger.info(f"\nIndexing batch {batch_count} ({len(batch)} documents)...")

                            result = crud_service.bulk_insert_documents(
                                documents=batch,
                                auto_embed=False  # Embeddings already generated
                            )

                            if result.is_ok():
                                stats = result.unwrap()
                                total_indexed += stats["success"]
                                logger.info(f"✓ Batch indexed: {stats['success']} successful, {stats['failed']} failed\n")

                                # Update all status records in batch to PROCESSED
                                for record_info in batch_status_records:
                                    execution_time = time.time() - record_info["start_time"]
                                    record_info["status_record"].status = ProcessingStatus.PROCESSED
                                    record_info["status_record"].indexed_chunks_count = record_info["num_chunks"]
                                    record_info["status_record"].vector_dimension = app_settings.vector_dimension
                                    record_info["status_record"].index_name = crud_service.index_name
                                    record_info["status_record"].execution_time = execution_time
                                    record_info["status_record"].updated_at = datetime.now(timezone.utc)
                                    session.add(record_info["status_record"])
                                session.commit()
                            else:
                                logger.error(f"✗ Batch indexing failed: {result.err()}\n")
                                failed += len(batch_status_records)

                                # Update all status records in batch to FAILED
                                for record_info in batch_status_records:
                                    execution_time = time.time() - record_info["start_time"]
                                    record_info["status_record"].status = ProcessingStatus.FAILED
                                    record_info["status_record"].execution_time = execution_time
                                    record_info["status_record"].error_message = str(result.err())[:1000]
                                    record_info["status_record"].updated_at = datetime.now(timezone.utc)
                                    session.add(record_info["status_record"])
                                session.commit()

                            # Clear batch
                            batch = []
                            batch_status_records = []

                    except Exception as e:
                        # Update status to FAILED
                        execution_time = time.time() - doc_start_time
                        status_record.status = ProcessingStatus.FAILED
                        status_record.execution_time = execution_time
                        status_record.error_message = str(e)[:1000]
                        status_record.updated_at = datetime.now(timezone.utc)
                        session.add(status_record)
                        session.commit()

                        logger.error(f"Failed to process document from {json_file}: {e}")
                        failed += 1

                # Index remaining documents in final batch
                if batch:
                    batch_count += 1
                    logger.info(f"\nIndexing final batch {batch_count} ({len(batch)} documents)...")

                    result = crud_service.bulk_insert_documents(
                        documents=batch,
                        auto_embed=False
                    )

                    if result.is_ok():
                        stats = result.unwrap()
                        total_indexed += stats["success"]
                        logger.info(f"✓ Final batch indexed: {stats['success']} successful, {stats['failed']} failed\n")

                        # Update all status records in final batch to PROCESSED
                        for record_info in batch_status_records:
                            execution_time = time.time() - record_info["start_time"]
                            record_info["status_record"].status = ProcessingStatus.PROCESSED
                            record_info["status_record"].indexed_chunks_count = record_info["num_chunks"]
                            record_info["status_record"].vector_dimension = app_settings.vector_dimension
                            record_info["status_record"].index_name = crud_service.index_name
                            record_info["status_record"].execution_time = execution_time
                            record_info["status_record"].updated_at = datetime.now(timezone.utc)
                            session.add(record_info["status_record"])
                        session.commit()
                    else:
                        logger.error(f"✗ Final batch indexing failed: {result.err()}\n")
                        failed += len(batch_status_records)

                        # Update all status records in final batch to FAILED
                        for record_info in batch_status_records:
                            execution_time = time.time() - record_info["start_time"]
                            record_info["status_record"].status = ProcessingStatus.FAILED
                            record_info["status_record"].execution_time = execution_time
                            record_info["status_record"].error_message = str(result.err())[:1000]
                            record_info["status_record"].updated_at = datetime.now(timezone.utc)
                            session.add(record_info["status_record"])
                        session.commit()

        # Run async processing
        asyncio.run(process_and_index_documents())

        # Summary
        logger.info("\n=== Indexing Summary ===")
        logger.info(f"Total documents in database: {total_documents}")
        logger.info(f"Successfully processed: {processed}")
        logger.info(f"Skipped (already indexed): {skipped}")
        logger.info(f"Total documents indexed: {total_indexed}")
        logger.info(f"Not found in gold layer: {not_found}")
        logger.info(f"Failed to process: {failed}")

    @app.command()
    def clean(
        confirm: bool = typer.Option(
            False,
            "--confirm",
            "-y",
            help="Confirm deletion without prompting"
        ),
        index_name: Optional[str] = typer.Option(
            None,
            "--index",
            "-i",
            help="OpenSearch index name (uses default from settings if not provided)"
        ),
        cache_only: bool = typer.Option(
            False,
            "--cache-only",
            help="Clean only platinum cache (preserve database and OpenSearch)"
        )
    ):
        """Clean document_indexing_status table, OpenSearch index, and/or platinum cache"""
        from contramate.services.opensearch_vector_crud_service import OpenSearchVectorCRUDServiceFactory

        # Determine what to clean
        if cache_only:
            clean_targets = "   - Platinum cache files"
        else:
            clean_targets = (
                "   - Records from document_indexing_status table\n"
                "   - Documents from OpenSearch index\n"
                "   - Platinum cache files"
            )

        if not confirm:
            import typer
            response = typer.prompt(
                f"⚠️  This will DELETE ALL:\n{clean_targets}\nContinue? (yes/no)",
                default="no"
            )
            if response.lower() not in ["yes", "y"]:
                logger.info("Operation cancelled")
                return

        # Step 1: Clean platinum cache (always clean cache)
        logger.info("=== Cleaning Platinum Cache ===")
        cache_deleted_count = platinum_cache_service.clear_cache()
        logger.info(f"✓ Deleted {cache_deleted_count} cached platinum files\n")

        # If cache-only, stop here
        if cache_only:
            logger.info("✓ Cache cleanup complete!")
            return

        # Step 2: Clean database and OpenSearch
        # Create database connection
        postgres_settings = settings_factory.create_postgres_settings()
        connection_string = postgres_settings.connection_string
        engine = create_engine(connection_string, echo=False)

        # Initialize OpenSearch service
        try:
            crud_service = OpenSearchVectorCRUDServiceFactory.create_default(index_name=index_name)
            logger.info(f"Connected to OpenSearch index: {crud_service.index_name}\n")
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            return

        # Step 3: Count and delete from database
        logger.info("=== Cleaning Database ===")
        with Session(engine) as session:
            statement = select(DocumentIndexingStatus)
            records = session.exec(statement).all()
            db_count = len(records)

            logger.info(f"Found {db_count} records in document_indexing_status table")

            if db_count > 0:
                for record in records:
                    session.delete(record)
                session.commit()
                logger.info(f"✓ Deleted {db_count} records from database\n")
            else:
                logger.info("Table is already empty\n")

        # Step 4: Count and delete from OpenSearch
        logger.info("=== Cleaning OpenSearch Index ===")
        try:
            # Count documents in index
            count_query = {"query": {"match_all": {}}}
            count_response = crud_service.client.count(
                index=crud_service.index_name,
                body=count_query
            )
            os_count = count_response["count"]

            logger.info(f"Found {os_count} documents in OpenSearch index '{crud_service.index_name}'")

            if os_count > 0:
                # Delete all documents
                delete_query = {"query": {"match_all": {}}}
                delete_response = crud_service.client.delete_by_query(
                    index=crud_service.index_name,
                    body=delete_query,
                    refresh=True
                )
                deleted_count = delete_response.get("deleted", 0)
                logger.info(f"✓ Deleted {deleted_count} documents from OpenSearch\n")
            else:
                logger.info("Index is already empty\n")

        except Exception as e:
            logger.error(f"Failed to clean OpenSearch index: {e}\n")

        # Step 5: Verify cleanup
        logger.info("=== Verification ===")
        with Session(engine) as session:
            remaining_db = session.exec(select(DocumentIndexingStatus)).all()
            logger.info(f"Database records remaining: {len(remaining_db)}")

        try:
            final_count = crud_service.client.count(
                index=crud_service.index_name,
                body={"query": {"match_all": {}}}
            )
            logger.info(f"OpenSearch documents remaining: {final_count['count']}")
        except Exception as e:
            logger.warning(f"Could not verify OpenSearch count: {e}")

        logger.info("\n✓ Cleanup complete! You can now re-run indexing from scratch")

    @app.command()
    def retry_failed(
        batch_size: int = typer.Option(
            5,
            "--batch-size",
            "-b",
            help="Number of documents to index in each batch"
        ),
        index_name: Optional[str] = typer.Option(
            None,
            "--index",
            "-i",
            help="OpenSearch index name (uses default from settings if not provided)"
        ),
        delay_seconds: float = typer.Option(
            2.0,
            "--delay",
            "-d",
            help="Delay in seconds between processing documents (helps avoid rate limits)"
        ),
        include_ready: bool = typer.Option(
            True,
            "--include-ready/--no-ready",
            help="Also retry documents stuck in READY status (default: True)"
        )
    ):
        """Retry indexing failed documents and documents stuck in READY status"""
        import time
        from datetime import datetime, timezone
        from contramate.services.opensearch_vector_crud_service import OpenSearchVectorCRUDServiceFactory
        from contramate.services.opensearch_infra_service import create_opensearch_infra_service

        # Create database connection
        postgres_settings = settings_factory.create_postgres_settings()
        connection_string = postgres_settings.connection_string
        engine = create_engine(connection_string, echo=False)

        # Get app settings for vector dimension
        app_settings = settings_factory.create_app_settings()

        # Initialize embedding client
        logger.info("Initializing embedding client...")
        try:
            embedding_client = LiteLLMEmbeddingClient()
            logger.info("✓ Embedding client initialized\n")
        except Exception as e:
            logger.error(f"Failed to initialize embedding client: {e}")
            return

        # Initialize OpenSearch services
        logger.info("Initializing OpenSearch services...")
        try:
            infra_service = create_opensearch_infra_service()
            crud_service = OpenSearchVectorCRUDServiceFactory.create_default(index_name=index_name)

            # Get cluster health
            health = infra_service.get_cluster_health()
            if not health.get("healthy"):
                logger.error(f"OpenSearch cluster is not healthy: {health}")
                return

            logger.info(f"✓ OpenSearch cluster healthy: {health.get('status')}")
            logger.info(f"✓ Target index: {crud_service.index_name}\n")
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch services: {e}")
            return

        logger.info("Retrying failed/stuck documents")
        logger.info(f"Gold directory: {GOLD_BASE_PATH}")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Delay between docs: {delay_seconds}s")
        logger.info(f"Include READY status: {include_ready}\n")

        total_to_retry = 0
        processed = 0
        still_failed = 0
        total_indexed = 0

        async def retry_failed_documents():
            nonlocal total_to_retry, processed, still_failed, total_indexed

            with Session(engine) as session:
                # Build query for FAILED and optionally READY documents
                if include_ready:
                    statement = select(DocumentIndexingStatus).where(
                        DocumentIndexingStatus.status.in_([ProcessingStatus.FAILED, ProcessingStatus.READY])
                    )
                else:
                    statement = select(DocumentIndexingStatus).where(
                        DocumentIndexingStatus.status == ProcessingStatus.FAILED
                    )

                docs_to_retry = session.exec(statement).all()
                total_to_retry = len(docs_to_retry)

                if total_to_retry == 0:
                    logger.info("No documents to retry!")
                    return

                # Count by status for logging
                failed_count = sum(1 for d in docs_to_retry if d.status == ProcessingStatus.FAILED)
                ready_count = sum(1 for d in docs_to_retry if d.status == ProcessingStatus.READY)

                logger.info(f"Found {total_to_retry} documents to retry:")
                logger.info(f"  - FAILED: {failed_count}")
                logger.info(f"  - READY (stuck): {ready_count}\n")

                # Also get corresponding contracts for metadata
                batch = []
                batch_status_records = []

                for doc_to_retry in docs_to_retry:
                    project_id = doc_to_retry.project_id
                    reference_doc_id = doc_to_retry.reference_doc_id

                    # Get contract metadata
                    contract = session.exec(
                        select(ContractAsmd).where(
                            ContractAsmd.project_id == project_id,
                            ContractAsmd.reference_doc_id == reference_doc_id
                        )
                    ).first()

                    if not contract:
                        logger.warning(f"Contract not found for {project_id}/{reference_doc_id}")
                        continue

                    # Find JSON file
                    doc_dir = GOLD_BASE_PATH / project_id / reference_doc_id

                    if not doc_dir.exists():
                        logger.warning(f"Directory not found: {doc_dir}")
                        continue

                    json_files = list(doc_dir.glob("*.json"))

                    if not json_files:
                        logger.warning(f"No JSON files found in: {doc_dir}")
                        continue

                    json_file = json_files[0]

                    # Reset status to READY and clear error
                    doc_to_retry.status = ProcessingStatus.READY
                    doc_to_retry.updated_at = datetime.now(timezone.utc)
                    doc_to_retry.error_message = None
                    session.commit()
                    session.refresh(doc_to_retry)

                    # Track start time
                    doc_start_time = time.time()

                    try:
                        # Load chunked document
                        chunked_doc = load_chunked_document(json_file)

                        # Check for oversized chunks and rechunk if needed
                        max_tokens = max(chunk.token_count for chunk in chunked_doc.chunks)
                        if max_tokens > 8000:
                            logger.warning(f"⚠ Document has oversized chunk ({max_tokens} tokens > 8000 limit): {chunked_doc.filename}")
                            logger.info(f"  Attempting automatic re-chunking...")

                            try:
                                chunked_doc = rechunk_oversized_document(
                                    chunked_doc,
                                    max_tokens=8000,
                                    target_chunk_size=4000
                                )

                                new_max_tokens = max(chunk.token_count for chunk in chunked_doc.chunks)
                                if new_max_tokens > 8000:
                                    logger.error(f"✗ Re-chunking failed, still have {new_max_tokens} token chunk")
                                    continue

                                logger.info(f"✓ Successfully re-chunked document: max {new_max_tokens} tokens")
                            except Exception as e:
                                logger.error(f"✗ Re-chunking failed: {e}")
                                continue

                        logger.info(f"Retrying document: {chunked_doc.filename}")
                        logger.info(f"  Chunks to process: {len(chunked_doc.chunks)}")

                        # Try cache first
                        platinum_models = None
                        if platinum_cache_service.is_cache_valid(
                            project_id, reference_doc_id, chunked_doc.filename, json_file
                        ):
                            platinum_models = platinum_cache_service.load_platinum_models_from_cache(
                                project_id, reference_doc_id, chunked_doc.filename
                            )
                            if platinum_models:
                                logger.info(f"✓ Loaded {len(platinum_models)} platinum models from cache")

                        # Generate if not cached
                        if platinum_models is None:
                            platinum_models = await convert_document_to_platinum_models(
                                chunked_doc,
                                embedding_client
                            )
                            logger.info(f"✓ Created {len(platinum_models)} platinum models")

                            # Save to cache
                            try:
                                platinum_cache_service.save_platinum_models_to_cache(
                                    platinum_models,
                                    project_id,
                                    reference_doc_id,
                                    chunked_doc.filename
                                )
                            except Exception as e:
                                logger.warning(f"Failed to cache platinum models: {e}")

                        # Add to batch
                        batch.extend(platinum_models)
                        batch_status_records.append({
                            "status_record": doc_to_retry,
                            "num_chunks": len(platinum_models),
                            "start_time": doc_start_time
                        })
                        processed += 1

                        # Add delay
                        if delay_seconds > 0:
                            await asyncio.sleep(delay_seconds)

                        # Index batch when ready
                        if len(batch) >= batch_size:
                            logger.info(f"\nIndexing batch ({len(batch)} chunks)...")

                            result = crud_service.bulk_insert_documents(
                                documents=batch,
                                auto_embed=False
                            )

                            if result.is_ok():
                                stats = result.unwrap()
                                total_indexed += stats["success"]
                                logger.info(f"✓ Batch indexed: {stats['success']} successful\n")

                                # Update status records
                                for record_info in batch_status_records:
                                    execution_time = time.time() - record_info["start_time"]
                                    record_info["status_record"].status = ProcessingStatus.PROCESSED
                                    record_info["status_record"].indexed_chunks_count = record_info["num_chunks"]
                                    record_info["status_record"].vector_dimension = app_settings.vector_dimension
                                    record_info["status_record"].index_name = crud_service.index_name
                                    record_info["status_record"].execution_time = execution_time
                                    record_info["status_record"].updated_at = datetime.now(timezone.utc)
                                    session.add(record_info["status_record"])
                                session.commit()
                            else:
                                logger.error(f"✗ Batch indexing failed: {result.err()}\n")
                                still_failed += len(batch_status_records)

                                # Update to FAILED
                                for record_info in batch_status_records:
                                    execution_time = time.time() - record_info["start_time"]
                                    record_info["status_record"].status = ProcessingStatus.FAILED
                                    record_info["status_record"].execution_time = execution_time
                                    record_info["status_record"].error_message = str(result.err())[:1000]
                                    record_info["status_record"].updated_at = datetime.now(timezone.utc)
                                    session.add(record_info["status_record"])
                                session.commit()

                            # Clear batch
                            batch = []
                            batch_status_records = []

                    except Exception as e:
                        # Update status to FAILED
                        execution_time = time.time() - doc_start_time
                        doc_to_retry.status = ProcessingStatus.FAILED
                        doc_to_retry.execution_time = execution_time
                        doc_to_retry.error_message = str(e)[:1000]
                        doc_to_retry.updated_at = datetime.now(timezone.utc)
                        session.add(doc_to_retry)
                        session.commit()

                        logger.error(f"Failed to retry document: {e}")
                        still_failed += 1

                # Index remaining documents
                if batch:
                    logger.info(f"\nIndexing final batch ({len(batch)} chunks)...")

                    result = crud_service.bulk_insert_documents(
                        documents=batch,
                        auto_embed=False
                    )

                    if result.is_ok():
                        stats = result.unwrap()
                        total_indexed += stats["success"]
                        logger.info(f"✓ Final batch indexed: {stats['success']} successful\n")

                        for record_info in batch_status_records:
                            execution_time = time.time() - record_info["start_time"]
                            record_info["status_record"].status = ProcessingStatus.PROCESSED
                            record_info["status_record"].indexed_chunks_count = record_info["num_chunks"]
                            record_info["status_record"].vector_dimension = app_settings.vector_dimension
                            record_info["status_record"].index_name = crud_service.index_name
                            record_info["status_record"].execution_time = execution_time
                            record_info["status_record"].updated_at = datetime.now(timezone.utc)
                            session.add(record_info["status_record"])
                        session.commit()
                    else:
                        logger.error(f"✗ Final batch indexing failed: {result.err()}\n")
                        still_failed += len(batch_status_records)

                        for record_info in batch_status_records:
                            execution_time = time.time() - record_info["start_time"]
                            record_info["status_record"].status = ProcessingStatus.FAILED
                            record_info["status_record"].execution_time = execution_time
                            record_info["status_record"].error_message = str(result.err())[:1000]
                            record_info["status_record"].updated_at = datetime.now(timezone.utc)
                            session.add(record_info["status_record"])
                        session.commit()

        # Run async processing
        asyncio.run(retry_failed_documents())

        # Summary
        logger.info("\n=== Retry Summary ===")
        logger.info(f"Total documents to retry: {total_to_retry}")
        logger.info(f"Successfully processed: {processed - still_failed}")
        logger.info(f"Still failed: {still_failed}")
        logger.info(f"Total chunks indexed: {total_indexed}")

    @app.command()
    def verify(
        limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show")
    ):
        """Verify indexing status from database"""

        # Create database connection
        postgres_settings = settings_factory.create_postgres_settings()
        connection_string = postgres_settings.connection_string
        engine = create_engine(connection_string, echo=False)

        with Session(engine) as session:
            # Get all status records
            statement = select(DocumentIndexingStatus)
            all_status = session.exec(statement).all()

            # Count by status
            ready_count = sum(1 for s in all_status if s.status == ProcessingStatus.READY)
            processed_count = sum(1 for s in all_status if s.status == ProcessingStatus.PROCESSED)
            failed_count = sum(1 for s in all_status if s.status == ProcessingStatus.FAILED)

            logger.info("\n=== Indexing Status Summary ===")
            logger.info(f"Total tracked: {len(all_status)}")
            logger.info(f"Ready: {ready_count}")
            logger.info(f"Processed: {processed_count}")
            logger.info(f"Failed: {failed_count}")

            # Calculate total chunks indexed
            total_chunks = sum(s.indexed_chunks_count or 0 for s in all_status if s.indexed_chunks_count)
            logger.info(f"Total chunks indexed: {total_chunks}")

            # Show sample processed documents
            if processed_count > 0:
                logger.info(f"\n=== Sample Processed Documents (first {limit}) ===\n")
                processed_docs = [s for s in all_status if s.status == ProcessingStatus.PROCESSED][:limit]

                for i, status in enumerate(processed_docs, 1):
                    logger.info(f"{i}. Project: {status.project_id}")
                    logger.info(f"   Reference Doc: {status.reference_doc_id}")
                    logger.info(f"   Status: {status.status.value}")
                    logger.info(f"   Indexed Chunks: {status.indexed_chunks_count}")
                    logger.info(f"   Vector Dimension: {status.vector_dimension}")
                    logger.info(f"   Index Name: {status.index_name}")
                    logger.info(f"   Execution Time: {status.execution_time:.2f}s")
                    logger.info("")

            # Show failed documents
            if failed_count > 0:
                logger.info(f"\n=== Failed Documents (first 5) ===\n")
                failed_docs = [s for s in all_status if s.status == ProcessingStatus.FAILED][:5]

                for i, status in enumerate(failed_docs, 1):
                    logger.info(f"{i}. Project: {status.project_id}")
                    logger.info(f"   Reference Doc: {status.reference_doc_id}")
                    logger.info(f"   Error: {status.error_message[:200] if status.error_message else 'N/A'}...")
                    logger.info("")

    app()
