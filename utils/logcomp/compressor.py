"""Core log compression functionality."""

import os
import json
import tempfile
import shutil
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Callable

from utils.logcomp.types import (
    LogEntry, StructuredLog, CompressionResult,
    LOG_FORMAT, TemplateRegistry
)
from utils.logcomp.parsers import (
    get_parser_class, read_log_entries, extract_parameters_from_result,
    is_logparser_available
)

# Handle optional compression dependencies
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

import gzip


class LogCompressor:
    """Main class for log compression operations."""

    def __init__(self, algorithm: str = "drain", compression: Optional[str] = None, level: int = 3):
        """
        Initialize the log compressor.

        Args:
            algorithm: Log parsing algorithm (drain, spell, iplom)
            compression: Compression method (zstd, gzip, or None)
            level: Compression level (1-22 for zstd, 1-9 for gzip)
        """
        if not is_logparser_available():
            raise ImportError(
                "logparser is not available. Please install it with: pip install logparser"
            )

        self.algorithm = algorithm
        self.compression = compression
        self.level = level
        self.parser_class = get_parser_class(algorithm)

    def compress_logs(
        self,
        input_file: str,
        output_file: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> CompressionResult:
        """
        Parse log lines with the specified algorithm and optionally compress the results.

        Args:
            input_file: Path to input log file
            output_file: Path to output file
            progress_callback: Optional callback for progress updates

        Returns:
            CompressionResult with structured logs and metadata
        """
        def log_progress(message: str) -> None:
            if progress_callback is not None:
                progress_callback(message)

        # Read all the logs with their timestamps
        log_entries = read_log_entries(input_file)
        log_progress(f"Read {len(log_entries)} log lines")

        if not log_entries:
            log_progress("No log lines found")
            return CompressionResult(
                structured_logs=[],
                template_registry={},
                total_lines=0,
                unique_templates=0
            )

        # Create a temporary directory for input and output
        temp_dir = tempfile.mkdtemp()
        temp_input_dir = os.path.join(temp_dir, "input")
        temp_output_dir = os.path.join(temp_dir, "output")
        os.makedirs(temp_input_dir, exist_ok=True)
        os.makedirs(temp_output_dir, exist_ok=True)

        # Define log filename (without path)
        log_filename = "content_only.log"
        temp_content_only_file = os.path.join(temp_input_dir, log_filename)

        try:
            # Write just the content to the content_only file (no timestamps)
            with open(temp_content_only_file, "w", encoding="utf-8") as f:
                for entry in log_entries:
                    f.write(entry.content + "\n")

            # Initialize and run the parser
            parser = self.parser_class(
                log_format=LOG_FORMAT,
                indir=temp_input_dir,
                outdir=temp_output_dir,
                depth=4,  # default
                st=0.4,  # default
                rex=[],  # default
            )

            # Process logs using input directory and log name
            parser.parse(log_filename)

            # Find the result file
            result_file = self._find_result_file(temp_output_dir, log_filename)

            # Load results from the structured CSV
            df_structured = pd.read_csv(result_file)

            if len(df_structured) != len(log_entries):
                log_progress(
                    f"Warning: Number of parsed logs ({len(df_structured)}) does not match input ({len(log_entries)})"
                )

            # Create structured output with templates
            structured_logs, template_registry = self._process_parsed_results(
                log_entries, df_structured
            )

            # Write output
            self._write_output(output_file, structured_logs, template_registry)

            log_progress(f"Completed processing {len(structured_logs)} lines")
            log_progress(f"Discovered {len(template_registry)} unique templates")
            log_progress(f"Output written to {output_file}")

            return CompressionResult(
                structured_logs=structured_logs,
                template_registry=template_registry,
                total_lines=len(structured_logs),
                unique_templates=len(template_registry)
            )

        except Exception as e:
            # Clean up temporary directory before re-raising
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _find_result_file(self, temp_output_dir: str, log_filename: str) -> str:
        """Find the parser result file in the output directory."""
        result_file = os.path.join(temp_output_dir, f"{log_filename}_structured.csv")

        if not os.path.exists(result_file):
            # Try common alternative names the parser might use
            for alt_name in ["content_only_structured.csv", "LogParser_result.csv"]:
                alt_path = os.path.join(temp_output_dir, alt_name)
                if os.path.exists(alt_path):
                    result_file = alt_path
                    break

        # Find any CSV file in the output directory if previous attempts failed
        if not os.path.exists(result_file):
            csv_files = [f for f in os.listdir(temp_output_dir) if f.endswith(".csv")]
            if csv_files:
                result_file = os.path.join(temp_output_dir, csv_files[0])

        if not os.path.exists(result_file):
            raise FileNotFoundError(
                f"Parser did not generate any result files in {temp_output_dir}"
            )

        return result_file

    def _process_parsed_results(
        self,
        log_entries: List[LogEntry],
        df_structured: pd.DataFrame
    ) -> tuple[List[StructuredLog], TemplateRegistry]:
        """Process parsed results into structured logs."""
        structured_logs = []
        template_registry = {}  # Map templates to IDs

        # Match timestamps with parsed results
        for i, entry in enumerate(log_entries):
            if i >= len(df_structured):
                # In case the parser dropped some logs
                continue

            template = df_structured.iloc[i]["EventTemplate"]

            # Assign template IDs
            if template not in template_registry:
                template_registry[template] = len(template_registry)
            template_id = template_registry[template]

            # Extract parameters
            params = extract_parameters_from_result(df_structured.iloc[i])

            # Create structured log entry
            structured_log = StructuredLog(
                template_id=template_id,
                timestamp=entry.timestamp,
                parameters=params
            )
            structured_logs.append(structured_log)

        return structured_logs, template_registry

    def _write_output(
        self,
        output_file: str,
        structured_logs: List[StructuredLog],
        template_registry: TemplateRegistry
    ) -> None:
        """Write structured logs to output file with optional compression."""
        if self.compression == "zstd" and ZSTD_AVAILABLE:
            self._write_zstd_compressed(output_file, structured_logs)
        elif self.compression == "gzip" or (self.compression == "zstd" and not ZSTD_AVAILABLE):
            if self.compression == "zstd" and not ZSTD_AVAILABLE:
                # This warning should be handled by the caller
                pass
            self._write_gzip_compressed(output_file, structured_logs)
        else:
            # Uncompressed, human-readable JSONL output
            self._write_uncompressed(output_file, structured_logs, template_registry)

    def _write_zstd_compressed(self, output_file: str, structured_logs: List[StructuredLog]) -> None:
        """Write logs with zstandard compression."""
        with open(output_file, "wb") as f:
            cctx = zstd.ZstdCompressor(level=self.level)
            with cctx.stream_writer(f) as compressor:
                for log in structured_logs:
                    json_line = json.dumps(log.to_dict()) + "\n"
                    compressor.write(json_line.encode("utf-8"))

    def _write_gzip_compressed(self, output_file: str, structured_logs: List[StructuredLog]) -> None:
        """Write logs with gzip compression."""
        with gzip.open(output_file, "wb", compresslevel=self.level) as f:
            for log in structured_logs:
                json_line = json.dumps(log.to_dict()) + "\n"
                f.write(json_line.encode("utf-8"))

    def _write_uncompressed(
        self,
        output_file: str,
        structured_logs: List[StructuredLog],
        template_registry: TemplateRegistry
    ) -> None:
        """Write logs without compression and include template dictionary."""
        with open(output_file, "w", encoding="utf-8") as f:
            for log in structured_logs:
                json_line = json.dumps(log.to_dict()) + "\n"
                f.write(json_line)

        # Write template dictionary to a separate file
        template_file = output_file + ".templates.json"
        with open(template_file, "w", encoding="utf-8") as f:
            templates = {
                str(idx): template for template, idx in template_registry.items()
            }
            json.dump(templates, f, indent=2)


def compress_logs(
    input_file: str,
    output_file: str,
    algorithm: str = "drain",
    compression: Optional[str] = None,
    level: int = 3,
    progress_callback: Optional[Callable[[str], None]] = None
) -> CompressionResult:
    """
    Convenience function for log compression.

    Args:
        input_file: Path to input log file
        output_file: Path to output file
        algorithm: Log parsing algorithm (drain, spell, iplom)
        compression: Compression method (zstd, gzip, or None)
        level: Compression level
        progress_callback: Optional callback for progress updates

    Returns:
        CompressionResult with structured logs and metadata
    """
    compressor = LogCompressor(algorithm=algorithm, compression=compression, level=level)
    return compressor.compress_logs(input_file, output_file, progress_callback)
