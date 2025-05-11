#!/usr/bin/env python3
"""
Log compression script that parses log files and compresses them into structured templates.
"""
import os
import re
import time
import json
import tempfile
import shutil
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple, TextIO

import click
import msgpack
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
import gzip
import logparser
from logparser.utils import evaluator
from logparser import Drain, Spell, IPLoM


# Timestamp extraction regex
TIMESTAMP_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")

# Define log format (required for logparser)
LOG_FORMAT = '<Content>'  # Simple format treating the whole line as content

# Map algorithm names to their implementations
ALGORITHMS = {
    "drain": Drain.LogParser,
    "spell": Spell.LogParser,
    "iplom": IPLoM.LogParser
}


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


def compress_logs(
    input_file: str,
    output_file: str,
    algorithm: str = "drain",
    compression: Optional[str] = None,
    level: int = 3
) -> None:
    """Parse log lines with the specified algorithm and optionally compress the results."""
    # Check algorithm
    parser_cls = ALGORITHMS.get(algorithm.lower())
    if not parser_cls:
        raise ValueError(f"Unknown algorithm: {algorithm}. Available algorithms: {', '.join(ALGORITHMS.keys())}")
    
    # First, read all the logs with their timestamps
    logs_with_ts = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            timestamp, content = parse_timestamp(line)
            logs_with_ts.append((timestamp, content))
    
    click.echo(f"Read {len(logs_with_ts)} log lines")
    
    if not logs_with_ts:
        click.echo("No log lines found")
        return
    
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
        with open(temp_content_only_file, 'w', encoding='utf-8') as f:
            for _, content in logs_with_ts:
                f.write(content + '\n')
        
        # Initialize and run the parser
        parser = parser_cls(
            log_format=LOG_FORMAT,
            indir=temp_input_dir,
            outdir=temp_output_dir,
            depth=4,  # default
            st=0.4,   # default
            rex=[]    # default
        )
        
        # Process logs using input directory and log name
        parser.parse(log_filename)
        
        # Read the structured results
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
            csv_files = [f for f in os.listdir(temp_output_dir) if f.endswith('.csv')]
            if csv_files:
                result_file = os.path.join(temp_output_dir, csv_files[0])
        
        if not os.path.exists(result_file):
            raise FileNotFoundError(f"Parser did not generate any result files in {temp_output_dir}")
        
        # Load results from the structured CSV
        df_structured = pd.read_csv(result_file)
        
        if len(df_structured) != len(logs_with_ts):
            click.echo(f"Warning: Number of parsed logs ({len(df_structured)}) does not match input ({len(logs_with_ts)})")
        
        # Create structured output with templates
        structured_logs = []
        template_registry = {}  # Map templates to IDs
        
        # Match timestamps with parsed results
        for i, (timestamp, _) in enumerate(logs_with_ts):
            if i >= len(df_structured):
                # In case the parser dropped some logs
                continue
                
            template = df_structured.iloc[i]['EventTemplate']
            
            # Assign template IDs
            if template not in template_registry:
                template_registry[template] = len(template_registry)
            template_id = template_registry[template]
            
            # Extract parameters (the format varies by parser)
            params = {}
            if 'ParameterList' in df_structured.columns:
                # Some parsers return a string representation of a list
                param_list_str = df_structured.iloc[i]['ParameterList']
                if isinstance(param_list_str, str):
                    # Try to convert string representation to actual list
                    try:
                        import ast
                        param_list = ast.literal_eval(param_list_str)
                        for j, param in enumerate(param_list):
                            params[f'p{j}'] = param
                    except (SyntaxError, ValueError):
                        # Fallback if parsing fails
                        params['p0'] = param_list_str
                else:
                    # Handle case where it's not a string (might be a list or scalar)
                    params['p0'] = str(param_list_str)
            
            # Create structured output
            result = {
                "t": template_id,
                "ts": timestamp,
                "p": params
            }
            
            structured_logs.append(result)
        
        # Write output (compressed or uncompressed)
        if compression == "zstd" and ZSTD_AVAILABLE:
            with open(output_file, 'wb') as f:
                cctx = zstd.ZstdCompressor(level=level)
                with cctx.stream_writer(f) as compressor:
                    for log in structured_logs:
                        json_line = json.dumps(log) + '\n'
                        compressor.write(json_line.encode('utf-8'))
        elif compression == "gzip" or (compression == "zstd" and not ZSTD_AVAILABLE):
            if compression == "zstd" and not ZSTD_AVAILABLE:
                click.echo("zstandard not available, falling back to gzip")
            
            with gzip.open(output_file, 'wb', compresslevel=level) as f:
                for log in structured_logs:
                    json_line = json.dumps(log) + '\n'
                    f.write(json_line.encode('utf-8'))
        else:
            # Uncompressed, human-readable JSONL output
            with open(output_file, 'w', encoding='utf-8') as f:
                for log in structured_logs:
                    # Optionally make the JSON more readable with indentation
                    # json_line = json.dumps(log, indent=2) + '\n'
                    json_line = json.dumps(log) + '\n'
                    f.write(json_line)
        
        click.echo(f"Completed processing {len(structured_logs)} lines")
        click.echo(f"Discovered {len(template_registry)} unique templates")
        click.echo(f"Output written to {output_file}")
        
        # Write template dictionary to a separate file if output is not compressed
        if not compression:
            template_file = output_file + ".templates.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                templates = {str(idx): template for template, idx in template_registry.items()}
                json.dump(templates, f, indent=2)
            click.echo(f"Template dictionary written to {template_file}")
    
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@click.command()
@click.option('--input', '-i', required=True, help='Path to input log file')
@click.option('--output', '-o', help='Path to output file (default: <input>.jsonl)')
@click.option('--algo', default='drain', help='Log parsing algorithm (drain, spell, iplom)')
@click.option('--compression', '-c', help='Compression algorithm (zstd, gzip), omit for human-readable output')
@click.option('--level', '-l', default=3, help='Compression level (only used if compression is enabled)')
def main(input, output, algo, compression, level):
    """
    Parse log files by converting them to structured templates.
    
    This tool parses log files using log template mining algorithms,
    extracts timestamps, and outputs either human-readable or compressed results.
    By default, outputs human-readable JSONL files.
    """
    # Validate input
    if not os.path.isfile(input):
        click.echo(f"Error: Input file does not exist: {input}")
        return
    
    # Set default output if not provided
    if not output:
        if compression == "zstd" and ZSTD_AVAILABLE:
            ext = ".jsonl.zst"
        elif compression == "gzip":
            ext = ".jsonl.gz"
        else:
            ext = ".jsonl"
        output = f"{input}{ext}"
    
    try:
        compress_logs(
            input_file=input,
            output_file=output,
            algorithm=algo,
            compression=compression,
            level=level
        )
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        import traceback
        click.echo(traceback.format_exc())


if __name__ == "__main__":
    main() 