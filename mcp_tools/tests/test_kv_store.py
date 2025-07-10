import time
import threading
import pytest
from mcp_tools.kv_store.tool import KVStoreTool, KVStore


class TestKVStore:
    """Test the KVStore class directly."""

    def setup_method(self):
        """Set up a fresh KVStore for each test."""
        self.kv = KVStore()

    def test_basic_set_get(self):
        """Test basic set and get operations."""
        self.kv.set("test_key", "test_value")
        assert self.kv.get("test_key") == "test_value"

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        assert self.kv.get("nonexistent") is None

    def test_set_with_ttl(self):
        """Test setting a key with TTL."""
        self.kv.set("ttl_key", "ttl_value", ttl_seconds=1)
        assert self.kv.get("ttl_key") == "ttl_value"

        # Wait for expiration
        time.sleep(1.1)
        assert self.kv.get("ttl_key") is None

    def test_delete(self):
        """Test delete operation."""
        self.kv.set("delete_key", "delete_value")
        assert self.kv.delete("delete_key") is True
        assert self.kv.get("delete_key") is None
        assert self.kv.delete("delete_key") is False  # Already deleted

    def test_exists(self):
        """Test exists operation."""
        assert self.kv.exists("nonexistent") is False

        self.kv.set("exists_key", "exists_value")
        assert self.kv.exists("exists_key") is True

        self.kv.set("expired_key", "expired_value", ttl_seconds=1)
        assert self.kv.exists("expired_key") is True
        time.sleep(1.1)
        assert self.kv.exists("expired_key") is False

    def test_keys(self):
        """Test keys operation."""
        assert self.kv.keys() == []

        self.kv.set("key1", "value1")
        self.kv.set("key2", "value2")
        self.kv.set("expired", "expired_value", ttl_seconds=1)

        keys = self.kv.keys()
        assert "key1" in keys
        assert "key2" in keys
        assert "expired" in keys
        assert len(keys) == 3

        # Wait for expiration
        time.sleep(1.1)
        keys = self.kv.keys()
        assert "key1" in keys
        assert "key2" in keys
        assert "expired" not in keys
        assert len(keys) == 2

    def test_list_keys(self):
        """Test list_keys operation with prefix filtering."""
        # Test empty store
        assert self.kv.list_keys() == []
        assert self.kv.list_keys("prefix") == []

        # Add hierarchical keys
        self.kv.set("a/b/c", "value1")
        self.kv.set("a/b/d", "value2")
        self.kv.set("a/x/y", "value3")
        self.kv.set("b/c/d", "value4")
        self.kv.set("simple", "value5")

        # Test listing with no prefix (should return all keys)
        all_keys = self.kv.list_keys()
        assert sorted(all_keys) == ["a/b/c", "a/b/d", "a/x/y", "b/c/d", "simple"]

        # Test listing with prefix "a/b" (should return "c" and "d")
        ab_keys = self.kv.list_keys("a/b")
        assert sorted(ab_keys) == ["c", "d"]

        # Test listing with prefix "a" (should return first segments: "b", "x")
        a_keys = self.kv.list_keys("a")
        assert sorted(a_keys) == ["b", "x"]

        # Test listing with prefix "b" (should return "c")
        b_keys = self.kv.list_keys("b")
        assert sorted(b_keys) == ["c"]

        # Test listing with non-existent prefix
        empty_keys = self.kv.list_keys("nonexistent")
        assert empty_keys == []

        # Test expired keys are filtered out
        self.kv.set("expired/key", "value", ttl_seconds=1)
        expired_keys = self.kv.list_keys("expired")
        assert "key" in expired_keys

        time.sleep(1.1)
        expired_keys = self.kv.list_keys("expired")
        assert expired_keys == []

    def test_clear(self):
        """Test clear operation."""
        self.kv.set("key1", "value1")
        self.kv.set("key2", "value2")

        count = self.kv.clear()
        assert count == 2
        assert self.kv.keys() == []

    def test_ttl(self):
        """Test TTL operation."""
        # Key doesn't exist
        assert self.kv.ttl("nonexistent") is None

        # Key without TTL
        self.kv.set("no_ttl", "value")
        assert self.kv.ttl("no_ttl") == -1

        # Key with TTL
        self.kv.set("with_ttl", "value", ttl_seconds=10)
        ttl = self.kv.ttl("with_ttl")
        assert ttl is not None
        assert 9 <= ttl <= 10  # Should be close to 10

        # Expired key
        self.kv.set("expired", "value", ttl_seconds=1)
        time.sleep(1.1)
        assert self.kv.ttl("expired") is None

    def test_different_value_types(self):
        """Test storing different types of values."""
        # String
        self.kv.set("string_key", "string_value")
        assert self.kv.get("string_key") == "string_value"

        # Integer
        self.kv.set("int_key", 42)
        assert self.kv.get("int_key") == 42

        # Float
        self.kv.set("float_key", 3.14)
        assert self.kv.get("float_key") == 3.14

        # Boolean
        self.kv.set("bool_key", True)
        assert self.kv.get("bool_key") is True

        # List
        self.kv.set("list_key", [1, 2, 3])
        assert self.kv.get("list_key") == [1, 2, 3]

        # Dict
        self.kv.set("dict_key", {"foo": "bar"})
        assert self.kv.get("dict_key") == {"foo": "bar"}

    def test_thread_safety(self):
        """Test thread safety of the KV store."""
        def worker(worker_id):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                self.kv.set(key, value)
                assert self.kv.get(key) == value

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all keys are present
        keys = self.kv.keys()
        assert len(keys) == 500  # 5 workers * 100 keys each


class TestKVStoreTool:
    """Test the KVStoreTool class."""

    def setup_method(self):
        """Set up a fresh KVStoreTool for each test."""
        self.tool = KVStoreTool()
        # Clear the global store before each test
        self.tool.execute("clear")

    def test_tool_properties(self):
        """Test tool properties."""
        assert self.tool.name == "kv_store"
        assert "key-value store" in self.tool.description.lower()
        assert "ttl" in self.tool.description.lower()

        schema = self.tool.input_schema
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert "key" in schema["properties"]
        assert "value" in schema["properties"]
        assert "ttl" in schema["properties"]

    def test_set_operation(self):
        """Test set operation."""
        result = self.tool.execute("set", "test_key", "test_value")
        assert result["success"] is True
        assert "Set key 'test_key'" in result["message"]

        # Test set with custom TTL
        result = self.tool.execute("set", "ttl_key", "ttl_value", ttl=60)
        assert result["success"] is True
        assert "60 seconds" in result["message"]

        # Test set with no TTL
        result = self.tool.execute("set", "no_ttl_key", "no_ttl_value", ttl=-1)
        assert result["success"] is True
        assert "no expiration" in result["message"]

    def test_set_operation_errors(self):
        """Test set operation error cases."""
        # Missing key
        result = self.tool.execute("set", value="test_value")
        assert result["success"] is False
        assert "Key is required" in result["error"]

        # Missing value
        result = self.tool.execute("set", "test_key")
        assert result["success"] is False
        assert "Value is required" in result["error"]

    def test_get_operation(self):
        """Test get operation."""
        # Set a value first
        self.tool.execute("set", "test_key", "test_value")

        result = self.tool.execute("get", "test_key")
        assert result["success"] is True
        assert result["value"] == "test_value"

        # Test getting nonexistent key
        result = self.tool.execute("get", "nonexistent")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_get_operation_errors(self):
        """Test get operation error cases."""
        # Missing key
        result = self.tool.execute("get")
        assert result["success"] is False
        assert "Key is required" in result["error"]

    def test_delete_operation(self):
        """Test delete operation."""
        # Set a value first
        self.tool.execute("set", "test_key", "test_value")

        result = self.tool.execute("delete", "test_key")
        assert result["success"] is True
        assert "Deleted key 'test_key'" in result["message"]

        # Try to delete again
        result = self.tool.execute("delete", "test_key")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_delete_operation_errors(self):
        """Test delete operation error cases."""
        # Missing key
        result = self.tool.execute("delete")
        assert result["success"] is False
        assert "Key is required" in result["error"]

    def test_exists_operation(self):
        """Test exists operation."""
        result = self.tool.execute("exists", "nonexistent")
        assert result["success"] is True
        assert result["exists"] is False

        # Set a value
        self.tool.execute("set", "test_key", "test_value")

        result = self.tool.execute("exists", "test_key")
        assert result["success"] is True
        assert result["exists"] is True

    def test_exists_operation_errors(self):
        """Test exists operation error cases."""
        # Missing key
        result = self.tool.execute("exists")
        assert result["success"] is False
        assert "Key is required" in result["error"]

    def test_keys_operation(self):
        """Test keys operation."""
        result = self.tool.execute("keys")
        assert result["success"] is True
        assert result["keys"] == []
        assert result["count"] == 0

        # Add some keys
        self.tool.execute("set", "key1", "value1")
        self.tool.execute("set", "key2", "value2")

        result = self.tool.execute("keys")
        assert result["success"] is True
        assert "key1" in result["keys"]
        assert "key2" in result["keys"]
        assert result["count"] == 2

    def test_list_operation(self):
        """Test list operation with prefix filtering."""
        # Test empty store
        result = self.tool.execute("list")
        assert result["success"] is True
        assert result["keys"] == []
        assert result["count"] == 0
        assert result["prefix"] == ""

        # Add hierarchical keys
        self.tool.execute("set", "a/b/c", "value1")
        self.tool.execute("set", "a/b/d", "value2")
        self.tool.execute("set", "a/x/y", "value3")
        self.tool.execute("set", "b/c/d", "value4")
        self.tool.execute("set", "simple", "value5")

        # Test listing with no prefix
        result = self.tool.execute("list")
        assert result["success"] is True
        assert sorted(result["keys"]) == ["a/b/c", "a/b/d", "a/x/y", "b/c/d", "simple"]
        assert result["count"] == 5
        assert result["prefix"] == ""

        # Test listing with prefix "a/b"
        result = self.tool.execute("list", prefix="a/b")
        assert result["success"] is True
        assert sorted(result["keys"]) == ["c", "d"]
        assert result["count"] == 2
        assert result["prefix"] == "a/b"

        # Test listing with prefix "a"
        result = self.tool.execute("list", prefix="a")
        assert result["success"] is True
        assert sorted(result["keys"]) == ["b", "x"]
        assert result["count"] == 2
        assert result["prefix"] == "a"

        # Test listing with non-existent prefix
        result = self.tool.execute("list", prefix="nonexistent")
        assert result["success"] is True
        assert result["keys"] == []
        assert result["count"] == 0
        assert result["prefix"] == "nonexistent"

    def test_clear_operation(self):
        """Test clear operation."""
        # Add some keys
        self.tool.execute("set", "key1", "value1")
        self.tool.execute("set", "key2", "value2")

        result = self.tool.execute("clear")
        assert result["success"] is True
        assert "Cleared 2 keys" in result["message"]

        # Verify keys are cleared
        result = self.tool.execute("keys")
        assert result["count"] == 0

    def test_ttl_operation(self):
        """Test TTL operation."""
        # Nonexistent key
        result = self.tool.execute("ttl", "nonexistent")
        assert result["success"] is False
        assert "not found" in result["message"]

        # Key without TTL
        self.tool.execute("set", "no_ttl", "value", ttl=-1)
        result = self.tool.execute("ttl", "no_ttl")
        assert result["success"] is True
        assert result["ttl"] == -1
        assert "no expiration" in result["message"]

        # Key with TTL
        self.tool.execute("set", "with_ttl", "value", ttl=60)
        result = self.tool.execute("ttl", "with_ttl")
        assert result["success"] is True
        assert 55 <= result["ttl"] <= 60  # Should be close to 60
        assert "expires in" in result["message"]

    def test_ttl_operation_errors(self):
        """Test TTL operation error cases."""
        # Missing key
        result = self.tool.execute("ttl")
        assert result["success"] is False
        assert "Key is required" in result["error"]

    def test_unknown_operation(self):
        """Test unknown operation."""
        result = self.tool.execute("unknown_operation")
        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    def test_ttl_expiration(self):
        """Test that TTL expiration works correctly."""
        # Set a key with short TTL
        self.tool.execute("set", "short_ttl", "value", ttl=1)

        # Should exist initially
        result = self.tool.execute("get", "short_ttl")
        assert result["success"] is True

        # Wait for expiration
        time.sleep(1.1)

        # Should not exist after expiration
        result = self.tool.execute("get", "short_ttl")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_default_ttl(self):
        """Test that default TTL is applied."""
        # Set without specifying TTL (should use default 86400)
        self.tool.execute("set", "default_ttl", "value")

        result = self.tool.execute("ttl", "default_ttl")
        assert result["success"] is True
        # Should be close to 86400 (1 day)
        assert 86390 <= result["ttl"] <= 86400
