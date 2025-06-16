"""Utility for segmenting markdown content and storing it in a vector database."""

import re
import uuid
import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from utils.vector_store.vector_store import ChromaVectorStore
from utils.vector_store.embedding_service import EmbeddingInterface, SentenceTransformerEmbedding

# Set up logger for this module
logger = logging.getLogger(__name__)


class MarkdownSegmenter:
    """
    Utility for segmenting markdown content (both text and tables) and storing in a vector database.
    """

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        table_max_rows: int = 500,
        embedding_service: Optional[EmbeddingInterface] = None,
    ):
        """
        Initialize the markdown segmenter with an embedding model and vector store.

        Args:
            vector_store: An instance of ChromaVectorStore to use for storing segments.
            model_name: Name of the sentence transformer model to use for embeddings (deprecated, use embedding_service)
            chunk_size: Maximum size of text chunks in characters
            chunk_overlap: Overlap between text chunks in characters
            table_max_rows: Maximum number of rows in a table before splitting
            embedding_service: Optional embedding service. If not provided, creates SentenceTransformerEmbedding with model_name
        """
        from utils.vector_store.markdown_table_segmenter import MarkdownTableSegmenter

        # Prevent invalid configurations
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size - 1)

        # Initialize embedding service (new architecture) or fallback to old model approach
        if embedding_service is not None:
            self.embedding_service = embedding_service
            # For backward compatibility, also set self.model if it's a SentenceTransformerEmbedding
            if hasattr(embedding_service, '_model'):
                self.model = embedding_service._model  # type: ignore
            else:
                self.model = self._initialize_model(model_name)  # Fallback for non-SentenceTransformer services
        else:
            # Backward compatibility: create embedding service from model_name
            self.embedding_service = SentenceTransformerEmbedding(model_name=model_name)
            # For backward compatibility with existing code that might access self.model
            self.model = self.embedding_service._model

        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.table_max_rows = table_max_rows

        # Create a table segmenter for handling tables, reusing the same embedding service
        self.markdown_table_segmenter = MarkdownTableSegmenter(
            vector_store=self.vector_store,
            model=self.model,  # Pass the actual model for backward compatibility
            embedding_service=self.embedding_service
        )

    def _initialize_model(self, model_name: str):
        """
        Initialize the sentence transformer model with fallback support.

        Args:
            model_name: Name of the sentence transformer model to use

        Returns:
            SentenceTransformer: Initialized model instance

        Raises:
            RuntimeError: If both primary and fallback models fail to load
        """
        from sentence_transformers import SentenceTransformer

        # List of fallback models to try if the primary model fails
        fallback_models = [
            "all-mpnet-base-v2",
            "all-MiniLM-L12-v2",
            "paraphrase-MiniLM-L6-v2"
        ]

        # Try to load the primary model
        try:
            logger.info(f"Attempting to load primary model: {model_name}")
            return SentenceTransformer(model_name)
        except ValueError as e:
            if "Unrecognized model" in str(e):
                logger.warning(f"Failed to load primary model {model_name}: {e}")

                # Try fallback models
                for fallback_model in fallback_models:
                    try:
                        logger.info(f"Attempting fallback model: {fallback_model}")
                        model = SentenceTransformer(fallback_model)
                        logger.warning(f"Successfully loaded fallback model: {fallback_model}")
                        return model
                    except Exception as fallback_error:
                        logger.warning(f"Fallback model {fallback_model} also failed: {fallback_error}")
                        continue

                # If all fallback models fail, raise an error
                raise RuntimeError(
                    f"Failed to load primary model '{model_name}' and all fallback models. "
                    f"This may be due to a compatibility issue between sentence-transformers and transformers libraries. "
                    f"Tried fallback models: {fallback_models}"
                ) from e
            else:
                # Re-raise if it's a different type of ValueError
                raise
        except Exception as e:
            # Handle other types of exceptions
            logger.error(f"Unexpected error loading model {model_name}: {e}")
            raise

    def segment_markdown(self, markdown_content: str) -> List[Dict[str, Any]]:
        """
        Segment markdown content into text chunks and tables.

        Args:
            markdown_content: Markdown content to segment

        Returns:
            List of dictionaries containing segment information
        """
        # Extract all headings from the full markdown
        global_headings = self._extract_headings(markdown_content)

        # First, extract tables and their positions
        tables = self.markdown_table_segmenter.extract_tables(markdown_content)

        # Ensure all tables have a 'type' key
        for table in tables:
            table["type"] = "table"

        # Create a list of table positions to avoid including tables in text chunks
        table_positions = []
        for table in tables:
            start_pos = table["position"]
            # Approximate the end position based on content length
            end_pos = start_pos + len(table["content"])
            table_positions.append((start_pos, end_pos))

        # Sort table positions by start position
        table_positions.sort(key=lambda x: x[0])

        # Extract text segments between tables
        segments = []
        last_end = 0

        # Process text before, between, and after tables
        for start, end in table_positions:
            if start > last_end:
                # There's text between the last table and this one
                original_text_piece = markdown_content[last_end:start]
                text_segment_stripped = original_text_piece.strip()
                if text_segment_stripped:
                    leading_whitespace_len = len(original_text_piece) - len(
                        original_text_piece.lstrip()
                    )
                    effective_offset = last_end + leading_whitespace_len
                    text_chunks = self._chunk_text(
                        text_segment_stripped, global_headings, effective_offset
                    )
                    segments.extend(text_chunks)
            last_end = end

        # Add text after the last table
        if last_end < len(markdown_content):
            original_text_piece = markdown_content[last_end:]
            text_segment_stripped = original_text_piece.strip()
            if text_segment_stripped:
                leading_whitespace_len = len(original_text_piece) - len(
                    original_text_piece.lstrip()
                )
                effective_offset = last_end + leading_whitespace_len
                text_chunks = self._chunk_text(
                    text_segment_stripped, global_headings, effective_offset
                )
                segments.extend(text_chunks)

        # Process tables - potentially splitting large tables
        table_segments = []
        for table in tables:
            table_chunks = self._process_table(table)
            table_segments.extend(table_chunks)

        # Combine all segments and sort by position in the document
        all_segments = segments + table_segments
        all_segments.sort(key=lambda x: x["position"])

        return all_segments

    def _chunk_text(
        self, text: str, global_headings=None, offset=0
    ) -> List[Dict[str, Any]]:
        chunks = []
        if global_headings is None:
            headings = self._extract_headings(text)
            # offset parameter is still relevant for the initial position of this 'text' block
        else:
            headings = global_headings

        if not text.strip():  # Handle empty or whitespace-only text
            return chunks

        # If the entire text is smaller than or equal to chunk_size, treat it as a single chunk.
        if len(text) <= self.chunk_size:
            chunk_content = text.strip()
            if chunk_content:  # Only add if there's actual content after stripping
                chunk_info = {
                    "id": f"text_{uuid.uuid4().hex[:8]}",
                    "content": chunk_content,
                    "type": "text",
                    "position": offset,  # Global position of the start of this text block
                    "heading": self._get_nearest_heading(headings, offset),
                }
                chunks.append(chunk_info)
            return chunks

        start = 0
        chunk_id_counter = 0
        # When to attempt to extend a chunk if it's too short. e.g., 60% of chunk_size.
        min_chunk_len_factor = 0.6
        # Allow chunks to slightly exceed chunk_size if an extension is made, e.g., by 10%.
        max_chunk_len_factor_after_extension = 1.1

        while start < len(text):
            current_chunk_actual_start_in_text = start  # Relative to 'text'

            # Determine the ideal end of the chunk
            potential_end = start + self.chunk_size

            # Find the initial split point
            final_split_point: int
            if potential_end >= len(text):
                final_split_point = len(text)
            else:
                # Try to split at a newline first, looking backwards from potential_end
                p1 = text.rfind("\\n", start, potential_end)
                # If no newline or if it's at the very start (not useful), try space
                if p1 == -1 or p1 <= start:  # Check p1 <= start, not just p1 == start
                    p1 = text.rfind(" ", start, potential_end)

                if p1 != -1 and p1 > start:  # Found a good split point
                    final_split_point = p1
                else:  # No good split point before potential_end, so take up to potential_end
                    final_split_point = potential_end

            current_chunk_content = text[start:final_split_point].strip()

            # Extension Logic: If chunk is too short and there's more text, try to extend it
            if len(
                current_chunk_content
            ) < self.chunk_size * min_chunk_len_factor and final_split_point < len(
                text
            ):

                space_to_fill = self.chunk_size - len(current_chunk_content)
                extension_search_start = (
                    final_split_point  # Start searching from end of current short chunk
                )
                extension_search_end = min(
                    len(text), extension_search_start + space_to_fill
                )

                if (
                    extension_search_end > extension_search_start
                ):  # Only if there's a zone to search for extension
                    extended_split_candidate = -1
                    # Find best split in the extension zone (newline then space)
                    p_ext = text.rfind(
                        "\\n", extension_search_start, extension_search_end
                    )
                    if p_ext == -1 or p_ext <= extension_search_start:
                        p_ext = text.rfind(
                            " ", extension_search_start, extension_search_end
                        )

                    # If a split is found within the extension zone (and it's forward)
                    if p_ext != -1 and p_ext > extension_search_start:
                        extended_split_candidate = p_ext
                    else:
                        # If no clean break, consider extending to the end of the search zone
                        # if it means we grab more meaningful content.
                        # This might happen if the extension zone is all one long word/line.
                        extended_split_candidate = extension_search_end

                    if (
                        extended_split_candidate > final_split_point
                    ):  # Ensure we actually extend
                        candidate_content_text = text[
                            start:extended_split_candidate
                        ].strip()
                        # Only accept extension if it adds content and is within reasonable size limits
                        if (
                            len(candidate_content_text) > len(current_chunk_content)
                            and len(candidate_content_text)
                            <= self.chunk_size * max_chunk_len_factor_after_extension
                        ):
                            current_chunk_content = candidate_content_text
                            final_split_point = extended_split_candidate

            if current_chunk_content:
                # Global position for this chunk
                global_chunk_start_position = (
                    offset + current_chunk_actual_start_in_text
                )
                nearest_heading = self._get_nearest_heading(
                    headings, global_chunk_start_position
                )
                chunk_info = {
                    "id": f"text_{chunk_id_counter}_{uuid.uuid4().hex[:8]}",
                    "content": current_chunk_content,
                    "type": "text",
                    "position": global_chunk_start_position,
                    "heading": nearest_heading,
                }
                chunks.append(chunk_info)
                chunk_id_counter += 1

            if final_split_point >= len(text):  # Reached the end of the text
                break

            # Advance start for the next iteration, ensuring progress
            new_start_raw = final_split_point - self.chunk_overlap
            # Ensure 'start' advances by at least 1 from its value at the beginning of this iteration
            # or from old 'start' if new_start_raw is too small.
            start = max(current_chunk_actual_start_in_text + 1, new_start_raw)
            start = max(0, start)  # Ensure start is not negative

            if start >= len(
                text
            ):  # Safety break if overlap calculation itself goes beyond text length
                break

        return chunks

    def _extract_headings(self, text: str) -> List[Tuple[int, str, int]]:
        """
        Extract all headings and their positions from text.

        Args:
            text: Text to extract headings from

        Returns:
            List of tuples (position, heading_text, heading_level)
        """
        headings = []
        for match in re.finditer(r"^(#{1,6})\s+(.+?)$", text, re.MULTILINE):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            position = match.start()
            headings.append((position, heading_text, level))

        return headings

    def _get_nearest_heading(
        self, headings: List[Tuple[int, str, int]], position: int
    ) -> str:
        """
        Get the nearest heading before a given position.

        Args:
            headings: List of heading tuples (position, text, level)
            position: Position to find heading for

        Returns:
            Heading text or empty string if no heading found
        """
        nearest_heading = ""
        nearest_position = -1
        nearest_level = 100  # Start with a high level

        for head_pos, head_text, head_level in headings:
            if head_pos <= position and head_pos > nearest_position:
                # If we have multiple headings at the same position, prefer the one with lower level (## over ###)
                if head_pos > nearest_position or head_level < nearest_level:
                    nearest_heading = head_text
                    nearest_position = head_pos
                    nearest_level = head_level

        return nearest_heading

    def _process_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a table, potentially splitting it if it's too large. Robust version to avoid edge cases.

        Args:
            table: Dictionary containing table information

        Returns:
            List of table segment dictionaries
        """
        content = table["content"]
        rows = content.strip().split("\n")
        if len(rows) <= self.table_max_rows + 2:  # +2 for header and separator rows
            return [table]
        header_row = rows[0]
        separator_row = rows[1]
        data_rows = rows[2:]
        table_chunks = []
        parent_id = table["id"]
        total_chunks = (len(data_rows) + self.table_max_rows - 1) // self.table_max_rows
        for chunk_id, i in enumerate(range(0, len(data_rows), self.table_max_rows)):
            chunk_rows = data_rows[i : i + self.table_max_rows]
            chunk_content = "\n".join([header_row, separator_row] + chunk_rows)
            chunk_info = {
                "id": f"{parent_id}_chunk_{chunk_id}",
                "content": chunk_content,
                "type": "table",
                "position": table["position"],
                "heading": table["heading"],
                "context": table["context"],
                "is_chunk": True,
                "chunk_index": chunk_id,
                "total_chunks": total_chunks,
                "parent_id": parent_id,
            }
            table_chunks.append(chunk_info)
        return table_chunks

    def _create_embedding(self, segment: Dict[str, Any]) -> List[float]:
        """
        Create an embedding for a segment based on its content and context.

        Args:
            segment: Dictionary containing segment information

        Returns:
            Embedding vector
        """
        if segment["type"] == "table":
            # For tables, include heading and context
            text_to_embed = (
                f"{segment['heading']} {segment['context']} {segment['content']}"
            )
        else:
            # For text, include heading
            text_to_embed = f"{segment['heading']} {segment['content']}"

        # Generate embedding using the embedding service
        embedding = self.embedding_service.encode(text_to_embed)
        # Ensure we return a single embedding vector
        if isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], list):
            return embedding[0]  # Return first embedding if batch was returned
        return embedding  # type: ignore

    def segment_and_store(
        self,
        markdown_content: str,
        file_name: Optional[str] = None,
        rel_path: Optional[str] = None,
        file_size: Optional[int] = None,
        file_date: Optional[str] = None,
    ) -> Tuple[int, Dict[str, List[str]]]:
        """
        Segment markdown content and store it in the vector database.

        Args:
            markdown_content: Markdown content to segment and store

        Returns:
            Tuple of (total segments stored, dictionary of segment IDs by type)
        """
        # Segment the markdown
        segments = self.segment_markdown(markdown_content)

        if not segments:
            return 0, {"text": [], "table": []}

        # Prepare data for vector store
        ids = [segment["id"] for segment in segments]
        embeddings = [self._create_embedding(segment) for segment in segments]
        metadatas = []
        documents = []

        for segment in segments:
            metadata = {
                "type": segment["type"],
                "position": segment["position"],
                "heading": segment["heading"],
            }
            # Add file-level metadata if present
            if file_name is not None:
                metadata["file_name"] = file_name
            if rel_path is not None:
                metadata["rel_path"] = rel_path
            if file_size is not None:
                metadata["file_size"] = file_size
            if file_date is not None:
                metadata["file_date"] = file_date
            metadatas.append(metadata)
            documents.append(segment.get("content", ""))

        self.vector_store.add(
            ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
        )

        # Group IDs by segment type
        segment_ids = {"text": [], "table": []}
        for segment in segments:
            segment_ids[segment["type"]].append(segment["id"])

        return len(segments), segment_ids

    def search(
        self, query: str, n_results: int = 5, filter_by_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for segments based on semantic similarity to the query.

        Args:
            query: Search query
            n_results: Number of results to return
            filter_by_type: Optional filter for segment type ("text" or "table")

        Returns:
            Search results with matching segments
        """
        # Generate embedding for the query using the embedding service
        query_embedding = self.embedding_service.encode(query)
        # Ensure query_embedding is a single vector (List[float])
        if isinstance(query_embedding, list) and len(query_embedding) > 0 and isinstance(query_embedding[0], list):
            query_embedding = query_embedding[0]  # Extract first embedding if batch was returned

        # Prepare filter if needed
        where_filter = None
        if filter_by_type:
            where_filter = {"type": filter_by_type}

        # Query the vector store
        results = self.vector_store.query(
            query_embeddings=[query_embedding], n_results=n_results, where=where_filter  # type: ignore
        )

        return results
