"""Utility for segmenting markdown content and storing it in a vector database."""

import re
import uuid
import os
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from utils.vector_store.vector_store import ChromaVectorStore
from utils.vector_store.table_segmenter import MarkdownTableSegmenter

class MarkdownSegmenter:
    """
    Utility for segmenting markdown content (both text and tables) and storing in a vector database.
    """
    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2", 
        collection_name: str = "markdown_segments",
        persist_directory: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        table_max_rows: int = 15
    ):
        """
        Initialize the markdown segmenter with an embedding model and vector store.
        
        Args:
            model_name: Name of the sentence transformer model to use for embeddings
            collection_name: Name of the vector store collection
            persist_directory: Directory for persistent storage. If None, uses in-memory DB.
            chunk_size: Maximum size of text chunks in characters
            chunk_overlap: Overlap between text chunks in characters
            table_max_rows: Maximum number of rows in a table before splitting
        """
        # Prevent invalid configurations
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size - 1)
        self.model = SentenceTransformer(model_name)
        self.vector_store = ChromaVectorStore(
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.table_max_rows = table_max_rows
        
        # Create a table segmenter for handling tables
        self.table_segmenter = MarkdownTableSegmenter(
            model_name=model_name,
            collection_name=f"{collection_name}_tables",
            persist_directory=persist_directory
        )
    
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
        tables = self.table_segmenter.extract_tables(markdown_content)
        
        # Ensure all tables have a 'type' key
        for table in tables:
            table['type'] = 'table'
        
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
                    leading_whitespace_len = len(original_text_piece) - len(original_text_piece.lstrip())
                    effective_offset = last_end + leading_whitespace_len
                    text_chunks = self._chunk_text(text_segment_stripped, global_headings, effective_offset)
                    segments.extend(text_chunks)
            last_end = end
        
        # Add text after the last table
        if last_end < len(markdown_content):
            original_text_piece = markdown_content[last_end:]
            text_segment_stripped = original_text_piece.strip()
            if text_segment_stripped:
                leading_whitespace_len = len(original_text_piece) - len(original_text_piece.lstrip())
                effective_offset = last_end + leading_whitespace_len
                text_chunks = self._chunk_text(text_segment_stripped, global_headings, effective_offset)
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
    
    def _chunk_text(self, text: str, global_headings=None, offset=0) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks. Robust version to avoid infinite loops and handle edge cases.
        
        Args:
            text: Text to chunk
            global_headings: List of all headings in the markdown
            offset: Offset for text position
            
        Returns:
            List of dictionaries containing chunk information
        """
        chunks = []
        if global_headings is None:
            headings = self._extract_headings(text)
            offset = 0
        else:
            headings = global_headings
        if len(text) <= self.chunk_size:
            chunk_info = {
                "id": f"text_{uuid.uuid4().hex[:8]}",
                "content": text,
                "type": "text",
                "position": offset,
                "heading": self._get_nearest_heading(headings, offset)
            }
            chunks.append(chunk_info)
            return chunks
        start = 0
        chunk_id = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunk_text = text[start:].strip()
                if chunk_text:
                    nearest_heading = self._get_nearest_heading(headings, offset + start)
                    chunk_info = {
                        "id": f"text_{chunk_id}_{uuid.uuid4().hex[:8]}",
                        "content": chunk_text,
                        "type": "text",
                        "position": offset + start,
                        "heading": nearest_heading
                    }
                    chunks.append(chunk_info)
                break
            split_point = text.rfind("\n", start, end)
            if split_point == -1 or split_point <= start:
                split_point = text.rfind(" ", start, end)
            if split_point == -1 or split_point <= start:
                split_point = end
            chunk_text = text[start:split_point].strip()
            if chunk_text:
                nearest_heading = self._get_nearest_heading(headings, offset + start)
                chunk_info = {
                    "id": f"text_{chunk_id}_{uuid.uuid4().hex[:8]}",
                    "content": chunk_text,
                    "type": "text",
                    "position": offset + start,
                    "heading": nearest_heading
                }
                chunks.append(chunk_info)
                chunk_id += 1
            # Ensure we make progress by moving forward at least 1 character
            start = max(start + 1, split_point - self.chunk_overlap)
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
        for match in re.finditer(r'^(#{1,6})\s+(.+?)$', text, re.MULTILINE):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            position = match.start()
            headings.append((position, heading_text, level))
        
        return headings
    
    def _get_nearest_heading(self, headings: List[Tuple[int, str, int]], position: int) -> str:
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
            chunk_rows = data_rows[i:i + self.table_max_rows]
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
                "parent_id": parent_id
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
            text_to_embed = f"{segment['heading']} {segment['context']} {segment['content']}"
        else:
            # For text, include heading
            text_to_embed = f"{segment['heading']} {segment['content']}"
        
        # Generate embedding
        embedding = self.model.encode(text_to_embed)
        return embedding.tolist()
    
    def segment_and_store(self, markdown_content: str) -> Tuple[int, Dict[str, List[str]]]:
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
                "heading": segment["heading"]
            }
            
            # Add table-specific metadata
            if segment["type"] == "table":
                metadata["context"] = segment["context"][:100] + "..." if len(segment["context"]) > 100 else segment["context"]
                if segment.get("is_chunk", False):
                    metadata["is_chunk"] = True
                    metadata["chunk_index"] = segment["chunk_index"]
                    metadata["total_chunks"] = segment["total_chunks"]
                    metadata["parent_id"] = segment["parent_id"]
            
            metadatas.append(metadata)
            documents.append(segment["content"])
        
        # Store in vector database
        self.vector_store.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        # Group IDs by segment type
        segment_ids = {"text": [], "table": []}
        for segment in segments:
            segment_ids[segment["type"]].append(segment["id"])
        
        return len(segments), segment_ids
    
    def search(self, query: str, n_results: int = 5, filter_by_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for segments based on semantic similarity to the query.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_by_type: Optional filter for segment type ("text" or "table")
            
        Returns:
            Search results with matching segments
        """
        # Generate embedding for the query
        query_embedding = self.model.encode(query).tolist()
        
        # Prepare filter if needed
        where_filter = None
        if filter_by_type:
            where_filter = {"type": filter_by_type}
        
        # Query the vector store
        results = self.vector_store.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )
        
        return results 