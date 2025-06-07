"""Log compression utilities for parsing and compressing log files."""

from utils.logcomp.compressor import compress_logs, LogCompressor
from utils.logcomp.parsers import AVAILABLE_ALGORITHMS, is_logparser_available
from utils.logcomp.types import LogEntry, StructuredLog, CompressionResult

__all__ = [
    "compress_logs",
    "LogCompressor",
    "AVAILABLE_ALGORITHMS",
    "is_logparser_available",
    "LogEntry",
    "StructuredLog",
    "CompressionResult"
]
