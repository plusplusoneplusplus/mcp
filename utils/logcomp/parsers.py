"""Log parser implementations with graceful dependency handling."""

import time
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from utils.logcomp.types import TIMESTAMP_PATTERN, LogEntry


# Handle optional logparser dependencies
try:
    import logparser
    from logparser.utils import evaluator
    from logparser import Drain, Spell, IPLoM
    LOGPARSER_AVAILABLE = True

    # Map algorithm names to their implementations
    ALGORITHMS = {
        "drain": Drain.LogParser,
        "spell": Spell.LogParser,
        "iplom": IPLoM.LogParser,
    }
except ImportError:
    LOGPARSER_AVAILABLE = False
    ALGORITHMS = {}


def get_available_algorithms() -> List[str]:
    """Get list of available parsing algorithms."""
    if not LOGPARSER_AVAILABLE:
        return []
    return list(ALGORITHMS.keys())


def is_logparser_available() -> bool:
    """Check if logparser dependencies are available."""
    return LOGPARSER_AVAILABLE


def get_parser_class(algorithm: str) -> Optional[Any]:
    """Get parser class for the specified algorithm."""
    if not LOGPARSER_AVAILABLE:
        raise ImportError(
            "logparser is not available. Please install it with: pip install logparser"
        )

    parser_cls = ALGORITHMS.get(algorithm.lower())
    if not parser_cls:
        available = ", ".join(ALGORITHMS.keys())
        raise ValueError(
            f"Unknown algorithm: {algorithm}. Available algorithms: {available}"
        )

    return parser_cls


def parse_timestamp(line: str) -> Tuple[float, str]:
    """
    Extract timestamp from log line if available, otherwise use current time.
    Returns (epoch_time, remaining_line)
    """
    match = TIMESTAMP_PATTERN.match(line)
    if match:
        timestamp_str = match.group(1)
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            return timestamp.timestamp(), line[len(timestamp_str):].strip()
        except ValueError:
            pass

    return time.time(), line


def read_log_entries(input_file: str) -> List[LogEntry]:
    """Read log entries from file, extracting timestamps and content."""
    log_entries = []

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            timestamp, content = parse_timestamp(line)
            log_entries.append(LogEntry(timestamp=timestamp, content=content))

    return log_entries


def extract_parameters_from_result(df_row: Any) -> Dict[str, Any]:
    """Extract parameters from a parser result row."""
    params = {}

    if hasattr(df_row, 'get') and "ParameterList" in df_row:
        # Some parsers return a string representation of a list
        param_list_str = df_row["ParameterList"]
        if isinstance(param_list_str, str):
            # Try to convert string representation to actual list
            try:
                import ast
                param_list = ast.literal_eval(param_list_str)
                for j, param in enumerate(param_list):
                    params[f"p{j}"] = param
            except (SyntaxError, ValueError):
                # Fallback if parsing fails
                params["p0"] = param_list_str
        else:
            # Handle case where it's not a string (might be a list or scalar)
            params["p0"] = str(param_list_str)

    return params


# Export available algorithms for external use
AVAILABLE_ALGORITHMS = get_available_algorithms()
