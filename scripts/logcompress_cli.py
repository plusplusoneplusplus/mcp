#!/usr/bin/env python3
"""
Log compression CLI script - thin wrapper around utils.logcomp module.
"""
import os
import click

try:
    from utils.logcomp import compress_logs, AVAILABLE_ALGORITHMS, is_logparser_available
    from utils.logcomp.compressor import ZSTD_AVAILABLE
except ImportError as e:
    click.echo(f"Error importing logcomp module: {e}")
    click.echo("Please ensure the utils.logcomp module is properly installed.")
    exit(1)


@click.command()
@click.option("--input", "-i", required=True, help="Path to input log file")
@click.option("--output", "-o", help="Path to output file (default: <input>.jsonl)")
@click.option(
    "--algo", default="drain", help="Log parsing algorithm (drain, spell, iplom)"
)
@click.option(
    "--compression",
    "-c",
    help="Compression algorithm (zstd, gzip), omit for human-readable output",
)
@click.option(
    "--level",
    "-l",
    default=3,
    help="Compression level (only used if compression is enabled)",
)
def main(input, output, algo, compression, level):
    """
    Parse log files by converting them to structured templates.

    This tool parses log files using log template mining algorithms,
    extracts timestamps, and outputs either human-readable or compressed results.
    By default, outputs human-readable JSONL files.
    """
    # Check if logparser is available
    if not is_logparser_available():
        click.echo("Error: logparser is not available.")
        click.echo("Please install it with: pip install logparser")
        return

    # Validate input
    if not os.path.isfile(input):
        click.echo(f"Error: Input file does not exist: {input}")
        return

    # Validate algorithm
    available_algorithms = AVAILABLE_ALGORITHMS
    if algo not in available_algorithms:
        click.echo(f"Error: Unknown algorithm: {algo}")
        click.echo(f"Available algorithms: {', '.join(available_algorithms)}")
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

    # Handle zstd fallback warning
    if compression == "zstd" and not ZSTD_AVAILABLE:
        click.echo("zstandard not available, falling back to gzip")

    def progress_callback(message: str):
        """Callback to display progress messages."""
        click.echo(message)

    try:
        result = compress_logs(
            input_file=input,
            output_file=output,
            algorithm=algo,
            compression=compression,
            level=level,
            progress_callback=progress_callback
        )

        # Write template dictionary to a separate file if output is not compressed
        if not compression:
            template_file = output + ".templates.json"
            click.echo(f"Template dictionary written to {template_file}")

    except Exception as e:
        click.echo(f"Error: {str(e)}")
        import traceback
        click.echo(traceback.format_exc())


if __name__ == "__main__":
    main()
