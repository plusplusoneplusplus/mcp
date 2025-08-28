import time
import threading
from typing import Dict, Any, Optional
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool


class KVStore:
    """Thread-safe in-memory key-value store with TTL support."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set a key-value pair with optional TTL."""
        with self._lock:
            expiry = None
            if ttl_seconds is not None:
                expiry = time.time() + ttl_seconds

            self._store[key] = {
                'value': value,
                'expiry': expiry,
                'created_at': time.time()
            }

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key, returns None if key doesn't exist or has expired."""
        with self._lock:
            if key not in self._store:
                return None

            entry = self._store[key]

            # Check if expired
            if entry['expiry'] is not None and time.time() > entry['expiry']:
                del self._store[key]
                return None

            return entry['value']

    def delete(self, key: str) -> bool:
        """Delete a key, returns True if key existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists and hasn't expired."""
        with self._lock:
            if key not in self._store:
                return False

            entry = self._store[key]

            # Check if expired
            if entry['expiry'] is not None and time.time() > entry['expiry']:
                del self._store[key]
                return False

            return True

    def keys(self) -> list[str]:
        """Get all non-expired keys."""
        with self._lock:
            current_time = time.time()
            valid_keys = []
            expired_keys = []

            for key, entry in self._store.items():
                if entry['expiry'] is not None and current_time > entry['expiry']:
                    expired_keys.append(key)
                else:
                    valid_keys.append(key)

            # Clean up expired keys
            for key in expired_keys:
                del self._store[key]

            return valid_keys

    def list_keys(self, prefix: str = "") -> list[str]:
        """List keys with optional prefix filtering."""
        with self._lock:
            current_time = time.time()
            valid_keys = []
            expired_keys = []

            for key, entry in self._store.items():
                if entry['expiry'] is not None and current_time > entry['expiry']:
                    expired_keys.append(key)
                else:
                    if not prefix:
                        # If no prefix, return full key
                        valid_keys.append(key)
                    elif key.startswith(prefix):
                        # Return the part after the prefix
                        remaining = key[len(prefix):]
                        if remaining.startswith('/'):
                            # For hierarchical keys like a/b/c, when prefix is a/b, return c
                            remaining = remaining[1:]  # Remove leading slash
                            # Only return the first segment after the prefix
                            next_segment = remaining.split('/')[0]
                            if next_segment not in valid_keys:
                                valid_keys.append(next_segment)
                        elif remaining == "":
                            # Exact match with prefix
                            valid_keys.append("")
                        elif prefix and not remaining.startswith('/'):
                            # Handle case where prefix is "a" and key is "a/b/c"
                            # This shouldn't happen if prefix logic is correct
                            pass

            # Clean up expired keys
            for key in expired_keys:
                del self._store[key]

            return sorted(valid_keys)

    def clear(self) -> int:
        """Clear all keys, returns number of keys cleared."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    def ttl(self, key: str) -> Optional[int]:
        """Get TTL for a key in seconds, returns None if key doesn't exist or has no TTL."""
        with self._lock:
            if key not in self._store:
                return None

            entry = self._store[key]

            if entry['expiry'] is None:
                return -1  # No TTL set

            remaining = entry['expiry'] - time.time()
            if remaining <= 0:
                del self._store[key]
                return None

            return int(remaining)


# Global KV store instance
_kv_store = KVStore()


@register_tool()
class KVStoreTool(ToolInterface):
    """In-memory key-value store tool with TTL support."""

    @property
    def name(self) -> str:
        return "kv_store"

    @property
    def description(self) -> str:
        return (
            "In-memory key-value store with TTL support. "
            "Supports operations: set, get, delete, exists, keys, list, clear, ttl. "
            "Default TTL is 1 day (86400 seconds)."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform",
                    "enum": ["set", "get", "delete", "exists", "keys", "list", "clear", "ttl"]
                },
                "key": {
                    "type": "string",
                    "description": "The key for the operation (required for all operations except 'keys', 'list', and 'clear')"
                },
                "prefix": {
                    "type": "string",
                    "description": "The prefix to filter keys by (optional, only used for 'list' operation)",
                    "default": ""
                },
                "value": {
                    "description": "The value to store (required for 'set' operation)"
                },
                "ttl": {
                    "type": "integer",
                    "description": "Time-to-live in seconds (default: 86400 = 1 day). Use -1 for no expiration.",
                    "default": 86400
                }
            },
            "required": ["operation"]
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute KV store operation."""
        operation = arguments.get("operation")
        key = arguments.get("key")
        value = arguments.get("value")
        ttl = arguments.get("ttl", 86400)
        prefix = arguments.get("prefix", "")
        try:
            if operation == "set":
                if key is None:
                    return {"success": False, "error": "Key is required for set operation"}
                if value is None:
                    return {"success": False, "error": "Value is required for set operation"}

                ttl_seconds = None if ttl == -1 else ttl
                _kv_store.set(key, value, ttl_seconds)
                return {
                    "success": True,
                    "message": f"Set key '{key}' with TTL {ttl} seconds" if ttl != -1 else f"Set key '{key}' with no expiration"
                }

            elif operation == "get":
                if key is None:
                    return {"success": False, "error": "Key is required for get operation"}

                result = _kv_store.get(key)
                if result is None:
                    return {"success": False, "message": f"Key '{key}' not found or expired"}

                return {"success": True, "value": result}

            elif operation == "delete":
                if key is None:
                    return {"success": False, "error": "Key is required for delete operation"}

                deleted = _kv_store.delete(key)
                if deleted:
                    return {"success": True, "message": f"Deleted key '{key}'"}
                else:
                    return {"success": False, "message": f"Key '{key}' not found"}

            elif operation == "exists":
                if key is None:
                    return {"success": False, "error": "Key is required for exists operation"}

                exists = _kv_store.exists(key)
                return {"success": True, "exists": exists}

            elif operation == "keys":
                keys = _kv_store.keys()
                return {"success": True, "keys": keys, "count": len(keys)}

            elif operation == "list":
                keys = _kv_store.list_keys(prefix)
                return {"success": True, "keys": keys, "count": len(keys), "prefix": prefix}

            elif operation == "clear":
                count = _kv_store.clear()
                return {"success": True, "message": f"Cleared {count} keys"}

            elif operation == "ttl":
                if key is None:
                    return {"success": False, "error": "Key is required for ttl operation"}

                ttl_remaining = _kv_store.ttl(key)
                if ttl_remaining is None:
                    return {"success": False, "message": f"Key '{key}' not found or expired"}
                elif ttl_remaining == -1:
                    return {"success": True, "ttl": -1, "message": f"Key '{key}' has no expiration"}
                else:
                    return {"success": True, "ttl": ttl_remaining, "message": f"Key '{key}' expires in {ttl_remaining} seconds"}

            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            return {"success": False, "error": f"Operation failed: {str(e)}"}

    def execute(self, operation: str, key: Optional[str] = None, value: Any = None, ttl: int = 86400, prefix: str = "") -> Dict[str, Any]:
        """Synchronous wrapper for execute_tool for backwards compatibility and testing."""
        import asyncio
        arguments = {
            "operation": operation,
            "key": key,
            "value": value,
            "ttl": ttl,
            "prefix": prefix
        }
        return asyncio.run(self.execute_tool(arguments))
