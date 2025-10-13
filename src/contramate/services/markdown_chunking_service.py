import re
import unicodedata
from enum import StrEnum
from loguru import logger
import tiktoken
from typing import List, Dict, Tuple
from neopipe import Result, Ok, Err

from contramate.models import DocumentInfo, Chunk, ChunkedDocument


class EncodingName(StrEnum):
    """Enum for encoding names used by tiktoken."""
    DEFAULT = "o200k_base"
    O200K_BASE = "o200k_base"


class MarkdownChunkingService:
    def __init__(
        self,
        markdown_content: str,
        doc_info: DocumentInfo,
        encoding_name: EncodingName = EncodingName.DEFAULT,
        token_limit: int = 5000,
        min_chunk_size: int = 100,
    ):
        """
        Initializes the MarkdownChunkingService with the given markdown content and encoding.

        Parameters:
            markdown_content (str): The markdown content to be chunked.
            doc_info (DocumentInfo): Document information object (required).
            encoding_name (str): The encoding name used by tiktoken.
            token_limit (int): Maximum tokens per chunk.
            min_chunk_size (int): Minimum tokens for a chunk to be valid.
        """
        if not markdown_content:
            raise ValueError("markdown_content is required")

        if doc_info is None:
            raise ValueError("doc_info is required")

        if not isinstance(doc_info, DocumentInfo):
            raise TypeError(f"doc_info must be DocumentInfo instance, got {type(doc_info).__name__}")

        self.markdown_content = markdown_content
        self.doc_info = doc_info
        self.token_limit = token_limit
        self.min_chunk_size = min_chunk_size
        self.encoding_name = encoding_name
        self.encoding = tiktoken.get_encoding(encoding_name)

    def normalize_text(self, text: str) -> str:
        """
        IMPROVEMENT #10: Normalize unicode and special characters.
        """
        # Normalize unicode to NFC form
        text = unicodedata.normalize('NFC', text)
        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200f\u2028-\u202f\ufeff]', '', text)
        return text

    def detect_table_size(self, table_content: str) -> int:
        """
        IMPROVEMENT #4: Detect if a table is oversized.
        Returns token count of the table.
        """
        return len(self.encoding.encode(table_content))

    def split_large_table(self, table_content: str, limit: int) -> List[str]:
        """
        IMPROVEMENT #4: Split large tables by rows.
        Preserves header row in each chunk.
        """
        lines = table_content.strip().split('\n')
        if len(lines) < 3:  # Need at least header, separator, and one data row
            return [table_content]
        
        # Extract header and separator
        header_row = lines[0]
        separator_row = lines[1] if '|' in lines[1] and ('-' in lines[1] or ':' in lines[1]) else ""
        data_rows = lines[2:] if separator_row else lines[1:]
        
        header_block = f"{header_row}\n{separator_row}\n" if separator_row else f"{header_row}\n"
        header_tokens = len(self.encoding.encode(header_block))
        
        chunks = []
        current_chunk = header_block
        current_tokens = header_tokens
        
        for row in data_rows:
            row_tokens = len(self.encoding.encode(row + "\n"))
            if current_tokens + row_tokens > limit:
                chunks.append(current_chunk.strip())
                current_chunk = header_block + row + "\n"
                current_tokens = header_tokens + row_tokens
            else:
                current_chunk += row + "\n"
                current_tokens += row_tokens
        
        if current_chunk.strip() != header_block.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def extract_section_hierarchy(self, section_header: str) -> Tuple[int, str]:
        """
        IMPROVEMENT #3: Extract hierarchy level and clean header text.
        Returns (level, clean_header_text)
        """
        # Match headers: *, #, or numbered (1., 1.1., etc.)
        if section_header.startswith('*'):
            level = len(section_header) - len(section_header.lstrip('*'))
            clean = section_header.lstrip('*').strip()
        elif section_header.startswith('#'):
            level = len(section_header) - len(section_header.lstrip('#'))
            clean = section_header.lstrip('#').strip()
        else:
            # Numbered format: 1., 1.1., 1.1.1.
            match = re.match(r'^(\d+(\.\d+)*)\.\s*(.*)', section_header)
            if match:
                level = match.group(1).count('.') + 1
                clean = match.group(1) + '. ' + match.group(3)
            else:
                level = 0
                clean = section_header.strip()
        
        return level, clean

    def split_into_sections(self, markdown_content: str) -> List[Dict]:
        """
        IMPROVEMENT #3, #6, #9: Better section splitting with hierarchy tracking.
        IMPROVEMENT #6: Explicitly handle preamble content.
        """
        sections = []
        
        # IMPROVEMENT #6: Check for preamble (content before first header)
        header_pattern = r"^(\*+|#+|\d+(\.\d+)*\.)"
        lines = markdown_content.splitlines(keepends=True)

        preamble = []

        for line in lines:
            if re.match(header_pattern, line.strip()):
                break
            preamble.append(line)
        
        # Add preamble as first section if it exists and has content
        preamble_text = ''.join(preamble).strip()
        if preamble_text:
            sections.append({
                "type": "preamble",
                "content": preamble_text + "\n",
                "level": 0,
                "header": "Document Preamble"
            })
            logger.info("Found preamble content before first header")
        
        # Now process the rest
        current_section = {"type": "text", "content": "", "level": 0, "header": ""}
        table_pattern = r"^\|.*$"
        code_block_pattern = r"^```"  # IMPROVEMENT #9: Track code blocks
        in_code_block = False
        
        start_idx = len(preamble) if preamble_text else 0
        
        for line in lines[start_idx:]:
            # IMPROVEMENT #9: Track code blocks to avoid splitting them
            if re.match(code_block_pattern, line.strip()):
                in_code_block = not in_code_block
                current_section["content"] += line
                continue
            
            if in_code_block:
                current_section["content"] += line
                continue
            
            if re.match(header_pattern, line.strip()):
                # Save current section
                if current_section["content"].strip():
                    sections.append(current_section)
                
                # Extract hierarchy
                level, header_text = self.extract_section_hierarchy(line.strip())
                
                # Start new section
                current_section = {
                    "type": "text",
                    "content": line,
                    "level": level,
                    "header": header_text
                }
            elif re.match(table_pattern, line):
                current_section["content"] += line
                if "type" not in current_section or current_section["type"] != "table":
                    current_section["has_table"] = True
            else:
                current_section["content"] += line
        
        # Append last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections

    def clean_markdown(self, markdown_content: str) -> str:
        """
        IMPROVEMENT #11: More careful newline cleaning.
        Preserves code blocks and intentional spacing.
        """
        # First, normalize text
        markdown_content = self.normalize_text(markdown_content)
        
        # Protect code blocks from cleaning
        code_blocks = []
        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f"___CODE_BLOCK_{len(code_blocks) - 1}___"
        
        # Extract code blocks
        markdown_content = re.sub(
            r'```.*?```',
            save_code_block,
            markdown_content,
            flags=re.DOTALL
        )
        
        # Now clean newlines (but not inside code blocks)
        # Replace 3+ newlines with exactly 2
        cleaned_content = re.sub(r'(\r?\n){3,}', r'\n\n', markdown_content)
        
        # Restore code blocks
        for idx, code_block in enumerate(code_blocks):
            cleaned_content = cleaned_content.replace(
                f"___CODE_BLOCK_{idx}___",
                code_block
            )
        
        return cleaned_content

    def build_hierarchy_context(self, sections: List[Dict], current_idx: int) -> str:
        """
        IMPROVEMENT #3: Build parent header context for a section.
        Returns a string with parent headers to prepend.
        """
        if current_idx == 0:
            return ""
        
        current_level = sections[current_idx].get("level", 0)
        parent_headers = []
        
        # Look backwards for parent headers
        for i in range(current_idx - 1, -1, -1):
            section = sections[i]
            section_level = section.get("level", 0)
            
            if section_level < current_level:
                header = section.get("header", "")
                if header:
                    parent_headers.insert(0, header)
                current_level = section_level
            
            if section_level == 0:
                break
        
        if parent_headers:
            return "Context: " + " > ".join(parent_headers) + "\n\n"
        return ""

    def process_markdown_to_chunks(
        self
    ) -> ChunkedDocument:
        """
        Process markdown content into chunks and return structured document.

        Returns:
            ChunkedDocument: Structured document with file metadata and chunks
        """
        if not self.markdown_content or not self.markdown_content.strip():
            logger.warning("Empty markdown content provided")
            return ChunkedDocument(
                project_id=self.doc_info.project_id,
                reference_doc_id=self.doc_info.reference_doc_id,
                contract_type=self.doc_info.contract_type,
                total_chunks=0,
                original_markdown_length=0,
                chunks=[]
            )

        try:
            markdown_content = self.clean_markdown(self.markdown_content)

            # No header prepended to chunks - metadata is in parent object
            effective_limit = self.token_limit
            logger.info(f"Token limit per chunk: {effective_limit}")
            
            sections = self.split_into_sections(markdown_content)
            logger.info(f"Sections count in document: {len(sections)}")
            
            if not sections:
                logger.warning("No sections found in document")
                return [], markdown_content
            
            def encode(text: str) -> List[int]:
                return self.encoding.encode(text)
            
            def decode(tokens: List[int]) -> str:
                return self.encoding.decode(tokens)

            chunks: List[Chunk] = []
            char_position = 0
            
            # Case A: Single section - split by token limit
            if len(sections) == 1:
                section_content = sections[0]["content"].strip()
                tokens = encode(section_content)
                
                if not tokens:
                    return [], markdown_content
                
                # Split into fixed-size chunks
                for i in range(0, len(tokens), effective_limit):
                    token_slice = tokens[i:i + effective_limit]

                    # IMPROVEMENT #7: Skip chunks below minimum size (except last)
                    if len(token_slice) < self.min_chunk_size and i + effective_limit < len(tokens):
                        logger.info(f"Skipping small chunk with {len(token_slice)} tokens")
                        continue

                    chunk_text = decode(token_slice).strip()

                    # IMPROVEMENT #5: Create Chunk object directly
                    chunk_obj = Chunk(
                        content=chunk_text,
                        chunk_index=0,
                        section_hierarchy=[sections[0].get("header", "Document")],
                        char_start=char_position,
                        char_end=char_position + len(chunk_text),
                        token_count=len(token_slice),
                        has_tables=sections[0].get("has_table", False)
                    )

                    chunks.append(chunk_obj)
                    char_position += len(chunk_text)
            
            # Case B: Multiple sections - greedy packing
            else:
                current_chunk_parts: List[str] = []
                current_chunk_tokens = 0
                current_hierarchy: List[str] = []
                chunk_start_pos = 0
                has_tables_in_chunk = False
                
                for i, section in enumerate(sections):
                    section_content = section["content"].strip()
                    section_tokens_list = encode(section_content)
                    section_token_count = len(section_tokens_list)
                    
                    # IMPROVEMENT #3: Build hierarchy context
                    hierarchy_context = self.build_hierarchy_context(sections, i)
                    section_with_context = hierarchy_context + section_content
                    
                    # Update hierarchy tracking
                    section_header = section.get("header", "")
                    if section_header:
                        current_hierarchy.append(section_header)
                    
                    has_table = section.get("has_table", False)
                    
                    # IMPROVEMENT #4: Handle oversized sections (including tables)
                    if section_token_count > effective_limit:
                        # Flush current chunk first
                        if current_chunk_parts:
                            chunk_body = "\n\n".join(current_chunk_parts).strip()

                            chunk_obj = Chunk(
                                content=chunk_body,
                                chunk_index=0,
                                section_hierarchy=current_hierarchy.copy(),
                                char_start=chunk_start_pos,
                                char_end=chunk_start_pos + len(chunk_body),
                                token_count=current_chunk_tokens,
                                has_tables=has_tables_in_chunk
                            )

                            chunks.append(chunk_obj)
                            current_chunk_parts = []
                            current_chunk_tokens = 0
                            chunk_start_pos += len(chunk_body)
                            has_tables_in_chunk = False
                        
                        # Split oversized section
                        if has_table:
                            logger.info(f"Splitting oversized table in section: {section_header}")
                            table_chunks = self.split_large_table(section_content, effective_limit)
                            for table_chunk in table_chunks:
                                chunk_content = hierarchy_context + table_chunk

                                chunk_obj = Chunk(
                                    content=chunk_content,
                                    chunk_index=0,
                                    section_hierarchy=current_hierarchy.copy(),
                                    char_start=chunk_start_pos,
                                    char_end=chunk_start_pos + len(table_chunk),
                                    token_count=len(encode(table_chunk)),
                                    has_tables=True
                                )

                                chunks.append(chunk_obj)
                                chunk_start_pos += len(table_chunk)
                        else:
                            # Regular token-based splitting
                            for j in range(0, len(section_tokens_list), effective_limit):
                                token_slice = section_tokens_list[j:j + effective_limit]
                                chunk_text = decode(token_slice).strip()
                                chunk_content = hierarchy_context + chunk_text

                                chunk_obj = Chunk(
                                    content=chunk_content,
                                    chunk_index=0,
                                    section_hierarchy=current_hierarchy.copy(),
                                    char_start=chunk_start_pos,
                                    char_end=chunk_start_pos + len(chunk_text),
                                    token_count=len(token_slice),
                                    has_tables=False
                                )

                                chunks.append(chunk_obj)
                                chunk_start_pos += len(chunk_text)
                        
                        continue
                    
                    # Normal case: try to add section to current chunk
                    if current_chunk_tokens + section_token_count <= effective_limit:
                        current_chunk_parts.append(section_with_context)
                        current_chunk_tokens += len(encode(section_with_context))
                        if has_table:
                            has_tables_in_chunk = True
                    else:
                        # Flush current chunk
                        if current_chunk_parts:
                            chunk_body = "\n\n".join(current_chunk_parts).strip()

                            chunk_obj = Chunk(
                                content=chunk_body,
                                chunk_index=0,
                                section_hierarchy=current_hierarchy.copy(),
                                char_start=chunk_start_pos,
                                char_end=chunk_start_pos + len(chunk_body),
                                token_count=current_chunk_tokens,
                                has_tables=has_tables_in_chunk
                            )

                            chunks.append(chunk_obj)
                            chunk_start_pos += len(chunk_body)
                        
                        # Start new chunk
                        current_chunk_parts = [section_with_context]
                        current_chunk_tokens = len(encode(section_with_context))
                        has_tables_in_chunk = has_table
                
                # IMPROVEMENT #7: Flush remaining parts (check minimum size)
                if current_chunk_parts:
                    chunk_body = "\n\n".join(current_chunk_parts).strip()

                    # If last chunk is too small, merge with previous chunk
                    if current_chunk_tokens < self.min_chunk_size and len(chunks) > 0:
                        logger.info(f"Merging small final chunk ({current_chunk_tokens} tokens) with previous chunk")
                        prev_chunk = chunks[-1]
                        # Merge previous chunk with current chunk
                        merged_content = prev_chunk.content + "\n\n" + chunk_body

                        # Update previous chunk in place
                        prev_chunk.content = merged_content
                        prev_chunk.char_end = chunk_start_pos + len(chunk_body)
                        prev_chunk.token_count += current_chunk_tokens
                        prev_chunk.has_tables = prev_chunk.has_tables or has_tables_in_chunk
                    else:
                        chunk_obj = Chunk(
                            content=chunk_body,
                            chunk_index=0,
                            section_hierarchy=current_hierarchy.copy(),
                            char_start=chunk_start_pos,
                            char_end=chunk_start_pos + len(chunk_body),
                            token_count=current_chunk_tokens,
                            has_tables=has_tables_in_chunk
                        )

                        chunks.append(chunk_obj)
            
            # Update chunk indices and validate
            for i, chunk_obj in enumerate(chunks, 1):
                chunk_obj.chunk_index = i

                # Validate chunk
                if not chunk_obj.content.strip():
                    logger.error(f"Empty chunk detected at index {i}")

            logger.info(f"Number of chunks created: {len(chunks)}")

            # Create and return ChunkedDocument
            chunked_doc = ChunkedDocument(
                project_id=self.doc_info.project_id,
                reference_doc_id=self.doc_info.reference_doc_id,
                contract_type=self.doc_info.contract_type,
                total_chunks=len(chunks),
                original_markdown_length=len(markdown_content),
                chunks=chunks
            )

            return chunked_doc

        except Exception as e:
            logger.error(f"Error processing markdown to chunks: {e}", exc_info=True)

            return ChunkedDocument(
                project_id=self.doc_info.project_id,
                reference_doc_id=self.doc_info.reference_doc_id,
                contract_type=self.doc_info.contract_type,
                total_chunks=0,
                original_markdown_length=len(self.markdown_content) if self.markdown_content else 0,
                chunks=[]
            )

    def execute(self) -> Result[ChunkedDocument, str]:
        """
        Execute the chunking service and return Result type.

        Returns:
            Result[ChunkedDocument, str]: Ok with ChunkedDocument on success, Err with error message on failure
        """
        try:
            chunked_doc = self.process_markdown_to_chunks()

            # Check if processing failed (empty chunks indicates failure)
            if chunked_doc.total_chunks == 0 and len(self.markdown_content) > 0:
                return Err("Failed to process markdown into chunks")

            return Ok(chunked_doc)

        except Exception as e:
            error_msg = f"Error executing markdown chunking service: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def __call__(self) -> Result[ChunkedDocument, str]:
        """
        Make the service callable like a function.

        Returns:
            Result[ChunkedDocument, str]: Ok with ChunkedDocument on success, Err with error message on failure
        """
        return self.execute()