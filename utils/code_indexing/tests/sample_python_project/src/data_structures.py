"""
Custom data structures and algorithms.

This module demonstrates:
- Generic classes
- Node-based data structures
- Iterator protocols
- Magic methods
- Type hints with complex generics
"""

from typing import TypeVar, Generic, Optional, Iterator, List, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod


T = TypeVar("T")


@dataclass
class TreeNode(Generic[T]):
    """Generic tree node with value and children."""

    value: T
    left: Optional["TreeNode[T]"] = None
    right: Optional["TreeNode[T]"] = None
    parent: Optional["TreeNode[T]"] = None

    def is_leaf(self) -> bool:
        """Check if node is a leaf."""
        return self.left is None and self.right is None

    def is_root(self) -> bool:
        """Check if node is root."""
        return self.parent is None

    def height(self) -> int:
        """Calculate height of subtree rooted at this node."""
        if self.is_leaf():
            return 0

        left_height = self.left.height() if self.left else -1
        right_height = self.right.height() if self.right else -1
        return 1 + max(left_height, right_height)

    def size(self) -> int:
        """Calculate number of nodes in subtree."""
        count = 1
        if self.left:
            count += self.left.size()
        if self.right:
            count += self.right.size()
        return count


class BinaryTree(Generic[T]):
    """Generic binary tree implementation."""

    def __init__(self):
        self._root: Optional[TreeNode[T]] = None
        self._size = 0

    @property
    def root(self) -> Optional[TreeNode[T]]:
        """Get the root node."""
        return self._root

    @property
    def size(self) -> int:
        """Get the number of nodes."""
        return self._size

    @property
    def is_empty(self) -> bool:
        """Check if tree is empty."""
        return self._root is None

    @property
    def height(self) -> int:
        """Get the height of the tree."""
        return self._root.height() if self._root else -1

    def insert(self, value: T) -> TreeNode[T]:
        """Insert a value into the tree (as BST)."""
        if self._root is None:
            self._root = TreeNode(value)
            self._size = 1
            return self._root

        return self._insert_recursive(self._root, value)

    def _insert_recursive(self, node: TreeNode[T], value: T) -> TreeNode[T]:
        """Recursively insert value into BST."""
        if value < node.value:
            if node.left is None:
                node.left = TreeNode(value, parent=node)
                self._size += 1
                return node.left
            else:
                return self._insert_recursive(node.left, value)
        else:
            if node.right is None:
                node.right = TreeNode(value, parent=node)
                self._size += 1
                return node.right
            else:
                return self._insert_recursive(node.right, value)

    def search(self, value: T) -> Optional[TreeNode[T]]:
        """Search for a value in the tree."""
        return self._search_recursive(self._root, value)

    def _search_recursive(
        self, node: Optional[TreeNode[T]], value: T
    ) -> Optional[TreeNode[T]]:
        """Recursively search for value."""
        if node is None or node.value == value:
            return node

        if value < node.value:
            return self._search_recursive(node.left, value)
        else:
            return self._search_recursive(node.right, value)

    def inorder_traversal(self) -> Iterator[T]:
        """Inorder traversal iterator."""
        yield from self._inorder_recursive(self._root)

    def _inorder_recursive(self, node: Optional[TreeNode[T]]) -> Iterator[T]:
        """Recursive inorder traversal."""
        if node:
            yield from self._inorder_recursive(node.left)
            yield node.value
            yield from self._inorder_recursive(node.right)

    def preorder_traversal(self) -> Iterator[T]:
        """Preorder traversal iterator."""
        yield from self._preorder_recursive(self._root)

    def _preorder_recursive(self, node: Optional[TreeNode[T]]) -> Iterator[T]:
        """Recursive preorder traversal."""
        if node:
            yield node.value
            yield from self._preorder_recursive(node.left)
            yield from self._preorder_recursive(node.right)

    def postorder_traversal(self) -> Iterator[T]:
        """Postorder traversal iterator."""
        yield from self._postorder_recursive(self._root)

    def _postorder_recursive(self, node: Optional[TreeNode[T]]) -> Iterator[T]:
        """Recursive postorder traversal."""
        if node:
            yield from self._postorder_recursive(node.left)
            yield from self._postorder_recursive(node.right)
            yield node.value

    def to_list(self) -> List[T]:
        """Convert tree to sorted list."""
        return list(self.inorder_traversal())

    def __iter__(self) -> Iterator[T]:
        """Make tree iterable (inorder)."""
        return self.inorder_traversal()

    def __len__(self) -> int:
        """Get tree size."""
        return self._size

    def __contains__(self, value: T) -> bool:
        """Check if value is in tree."""
        return self.search(value) is not None


@dataclass
class ListNode(Generic[T]):
    """Node for linked list."""

    value: T
    next: Optional["ListNode[T]"] = None

    def __repr__(self) -> str:
        return f"ListNode({self.value})"


class LinkedList(Generic[T]):
    """Generic singly linked list."""

    def __init__(self):
        self._head: Optional[ListNode[T]] = None
        self._tail: Optional[ListNode[T]] = None
        self._size = 0

    @property
    def size(self) -> int:
        """Get list size."""
        return self._size

    @property
    def is_empty(self) -> bool:
        """Check if list is empty."""
        return self._head is None

    @property
    def head(self) -> Optional[T]:
        """Get head value."""
        return self._head.value if self._head else None

    @property
    def tail(self) -> Optional[T]:
        """Get tail value."""
        return self._tail.value if self._tail else None

    def append(self, value: T) -> None:
        """Append value to end of list."""
        new_node = ListNode(value)

        if self._head is None:
            self._head = self._tail = new_node
        else:
            self._tail.next = new_node
            self._tail = new_node

        self._size += 1

    def prepend(self, value: T) -> None:
        """Prepend value to beginning of list."""
        new_node = ListNode(value)

        if self._head is None:
            self._head = self._tail = new_node
        else:
            new_node.next = self._head
            self._head = new_node

        self._size += 1

    def insert_at(self, index: int, value: T) -> None:
        """Insert value at specific index."""
        if index < 0 or index > self._size:
            raise IndexError("Index out of range")

        if index == 0:
            self.prepend(value)
        elif index == self._size:
            self.append(value)
        else:
            new_node = ListNode(value)
            prev = self._get_node_at(index - 1)
            new_node.next = prev.next
            prev.next = new_node
            self._size += 1

    def remove_first(self) -> Optional[T]:
        """Remove and return first element."""
        if self._head is None:
            return None

        value = self._head.value
        self._head = self._head.next

        if self._head is None:
            self._tail = None

        self._size -= 1
        return value

    def remove_last(self) -> Optional[T]:
        """Remove and return last element."""
        if self._head is None:
            return None

        if self._head == self._tail:
            value = self._head.value
            self._head = self._tail = None
            self._size -= 1
            return value

        # Find second-to-last node
        current = self._head
        while current.next != self._tail:
            current = current.next

        value = self._tail.value
        self._tail = current
        self._tail.next = None
        self._size -= 1
        return value

    def remove_at(self, index: int) -> T:
        """Remove and return element at index."""
        if index < 0 or index >= self._size:
            raise IndexError("Index out of range")

        if index == 0:
            return self.remove_first()
        elif index == self._size - 1:
            return self.remove_last()
        else:
            prev = self._get_node_at(index - 1)
            node_to_remove = prev.next
            prev.next = node_to_remove.next
            self._size -= 1
            return node_to_remove.value

    def _get_node_at(self, index: int) -> ListNode[T]:
        """Get node at specific index."""
        if index < 0 or index >= self._size:
            raise IndexError("Index out of range")

        current = self._head
        for _ in range(index):
            current = current.next
        return current

    def get(self, index: int) -> T:
        """Get value at index."""
        return self._get_node_at(index).value

    def set(self, index: int, value: T) -> None:
        """Set value at index."""
        self._get_node_at(index).value = value

    def find(self, value: T) -> int:
        """Find index of first occurrence of value."""
        current = self._head
        index = 0

        while current:
            if current.value == value:
                return index
            current = current.next
            index += 1

        return -1

    def reverse(self) -> None:
        """Reverse the list in place."""
        if self._size <= 1:
            return

        prev = None
        current = self._head
        self._tail = self._head

        while current:
            next_node = current.next
            current.next = prev
            prev = current
            current = next_node

        self._head = prev

    def to_list(self) -> List[T]:
        """Convert to Python list."""
        return list(self)

    def __iter__(self) -> Iterator[T]:
        """Make list iterable."""
        current = self._head
        while current:
            yield current.value
            current = current.next

    def __len__(self) -> int:
        """Get list length."""
        return self._size

    def __getitem__(self, index: int) -> T:
        """Get item by index."""
        return self.get(index)

    def __setitem__(self, index: int, value: T) -> None:
        """Set item by index."""
        self.set(index, value)

    def __str__(self) -> str:
        """String representation."""
        return "[" + " -> ".join(str(x) for x in self) + "]"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"LinkedList({list(self)})"


class Stack(Generic[T]):
    """Generic stack implementation using list."""

    def __init__(self):
        self._items: List[T] = []

    @property
    def size(self) -> int:
        """Get stack size."""
        return len(self._items)

    @property
    def is_empty(self) -> bool:
        """Check if stack is empty."""
        return len(self._items) == 0

    def push(self, item: T) -> None:
        """Push item onto stack."""
        self._items.append(item)

    def pop(self) -> T:
        """Pop item from stack."""
        if self.is_empty:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self) -> T:
        """Peek at top item without removing."""
        if self.is_empty:
            raise IndexError("peek from empty stack")
        return self._items[-1]

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()

    def to_list(self) -> List[T]:
        """Convert to list (top to bottom)."""
        return self._items[::-1]

    def __len__(self) -> int:
        """Get stack size."""
        return len(self._items)

    def __bool__(self) -> bool:
        """Check if stack is non-empty."""
        return not self.is_empty

    def __str__(self) -> str:
        """String representation."""
        return f"Stack({self.to_list()})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"Stack(size={self.size}, top={self.peek() if not self.is_empty else None})"
        )


class Queue(Generic[T]):
    """Generic queue implementation using list."""

    def __init__(self):
        self._items: List[T] = []

    @property
    def size(self) -> int:
        """Get queue size."""
        return len(self._items)

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._items) == 0

    def enqueue(self, item: T) -> None:
        """Add item to rear of queue."""
        self._items.append(item)

    def dequeue(self) -> T:
        """Remove item from front of queue."""
        if self.is_empty:
            raise IndexError("dequeue from empty queue")
        return self._items.pop(0)

    def front(self) -> T:
        """Peek at front item without removing."""
        if self.is_empty:
            raise IndexError("front from empty queue")
        return self._items[0]

    def rear(self) -> T:
        """Peek at rear item without removing."""
        if self.is_empty:
            raise IndexError("rear from empty queue")
        return self._items[-1]

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()

    def to_list(self) -> List[T]:
        """Convert to list (front to rear)."""
        return self._items.copy()

    def __len__(self) -> int:
        """Get queue size."""
        return len(self._items)

    def __bool__(self) -> bool:
        """Check if queue is non-empty."""
        return not self.is_empty

    def __str__(self) -> str:
        """String representation."""
        return f"Queue({self._items})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Queue(size={self.size}, front={self.front() if not self.is_empty else None})"


class PriorityQueue(Generic[T]):
    """Simple priority queue implementation."""

    def __init__(self):
        self._items: List[tuple[int, T]] = []  # (priority, item)

    @property
    def size(self) -> int:
        """Get queue size."""
        return len(self._items)

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._items) == 0

    def enqueue(self, item: T, priority: int = 0) -> None:
        """Add item with priority (higher number = higher priority)."""
        self._items.append((priority, item))
        self._items.sort(key=lambda x: x[0], reverse=True)

    def dequeue(self) -> T:
        """Remove highest priority item."""
        if self.is_empty:
            raise IndexError("dequeue from empty priority queue")
        return self._items.pop(0)[1]

    def peek(self) -> T:
        """Peek at highest priority item."""
        if self.is_empty:
            raise IndexError("peek from empty priority queue")
        return self._items[0][1]

    def peek_priority(self) -> int:
        """Peek at highest priority value."""
        if self.is_empty:
            raise IndexError("peek from empty priority queue")
        return self._items[0][0]

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()

    def __len__(self) -> int:
        """Get queue size."""
        return len(self._items)

    def __bool__(self) -> bool:
        """Check if queue is non-empty."""
        return not self.is_empty

    def __str__(self) -> str:
        """String representation."""
        return f"PriorityQueue({[(p, i) for p, i in self._items]})"


# Abstract base classes for data structures
class DataStructure(ABC, Generic[T]):
    """Abstract base class for data structures."""

    @abstractmethod
    def size(self) -> int:
        """Get size of data structure."""
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        """Check if data structure is empty."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all elements."""
        pass


class Collection(DataStructure[T]):
    """Abstract collection with common operations."""

    @abstractmethod
    def add(self, item: T) -> None:
        """Add item to collection."""
        pass

    @abstractmethod
    def remove(self, item: T) -> bool:
        """Remove item from collection."""
        pass

    @abstractmethod
    def contains(self, item: T) -> bool:
        """Check if item is in collection."""
        pass


# Utility functions for data structures
def merge_sorted_lists(list1: List[T], list2: List[T]) -> List[T]:
    """Merge two sorted lists into one sorted list."""
    result = []
    i = j = 0

    while i < len(list1) and j < len(list2):
        if list1[i] <= list2[j]:
            result.append(list1[i])
            i += 1
        else:
            result.append(list2[j])
            j += 1

    result.extend(list1[i:])
    result.extend(list2[j:])
    return result


def binary_search(sorted_list: List[T], target: T) -> int:
    """Binary search in sorted list. Returns index or -1 if not found."""
    left, right = 0, len(sorted_list) - 1

    while left <= right:
        mid = (left + right) // 2
        if sorted_list[mid] == target:
            return mid
        elif sorted_list[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


def quicksort(items: List[T]) -> List[T]:
    """Quicksort implementation."""
    if len(items) <= 1:
        return items

    pivot = items[len(items) // 2]
    left = [x for x in items if x < pivot]
    middle = [x for x in items if x == pivot]
    right = [x for x in items if x > pivot]

    return quicksort(left) + middle + quicksort(right)
