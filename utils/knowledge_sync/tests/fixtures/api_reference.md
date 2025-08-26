# API Reference

Complete API documentation for the knowledge sync service.

## KnowledgeSyncService

Main service class for syncing knowledge folders.

### Methods

#### `is_enabled() -> bool`
Check if knowledge sync is enabled in configuration.

#### `get_folder_collections() -> List[Tuple[str, str]]`
Parse configured folders and collections.

#### `resolve_folder_path(folder_path: str) -> Optional[Path]`
Resolve folder path to absolute path.

#### `collect_markdown_files(folder_path: Path) -> List[Dict[str, Any]]`
Collect all markdown files from a folder recursively.

#### `async run_manual_sync(resync: bool = False) -> Dict[str, Any]`
Run manual knowledge sync for all configured folders.

## Configuration

Environment variables:
- `KNOWLEDGE_SYNC_ENABLED`: Enable/disable sync
- `KNOWLEDGE_SYNC_FOLDERS`: Comma-separated folder paths
- `KNOWLEDGE_SYNC_COLLECTIONS`: Corresponding collection names
