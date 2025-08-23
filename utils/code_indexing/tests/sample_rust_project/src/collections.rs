/*!
 * Custom collection types and data structures.
 */

use crate::{LibError, LibResult};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::fmt::Debug;
use std::hash::Hash;

/// Generic stack implementation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Stack<T> {
    items: Vec<T>,
    max_size: Option<usize>,
}

impl<T> Stack<T> {
    pub fn new() -> Self {
        Self {
            items: Vec::new(),
            max_size: None,
        }
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            items: Vec::with_capacity(capacity),
            max_size: Some(capacity),
        }
    }

    pub fn push(&mut self, item: T) -> LibResult<()> {
        if let Some(max) = self.max_size {
            if self.items.len() >= max {
                return Err(LibError::InvalidInput("Stack overflow".to_string()));
            }
        }
        self.items.push(item);
        Ok(())
    }

    pub fn pop(&mut self) -> Option<T> {
        self.items.pop()
    }

    pub fn peek(&self) -> Option<&T> {
        self.items.last()
    }

    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    pub fn len(&self) -> usize {
        self.items.len()
    }

    pub fn clear(&mut self) {
        self.items.clear();
    }

    pub fn capacity(&self) -> Option<usize> {
        self.max_size
    }
}

impl<T> Default for Stack<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// Generic queue implementation
#[derive(Debug, Clone)]
pub struct Queue<T> {
    items: VecDeque<T>,
    max_size: Option<usize>,
}

impl<T> Queue<T> {
    pub fn new() -> Self {
        Self {
            items: VecDeque::new(),
            max_size: None,
        }
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            items: VecDeque::with_capacity(capacity),
            max_size: Some(capacity),
        }
    }

    pub fn enqueue(&mut self, item: T) -> LibResult<()> {
        if let Some(max) = self.max_size {
            if self.items.len() >= max {
                return Err(LibError::InvalidInput("Queue is full".to_string()));
            }
        }
        self.items.push_back(item);
        Ok(())
    }

    pub fn dequeue(&mut self) -> Option<T> {
        self.items.pop_front()
    }

    pub fn front(&self) -> Option<&T> {
        self.items.front()
    }

    pub fn back(&self) -> Option<&T> {
        self.items.back()
    }

    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    pub fn len(&self) -> usize {
        self.items.len()
    }

    pub fn clear(&mut self) {
        self.items.clear();
    }

    pub fn iter(&self) -> std::collections::vec_deque::Iter<T> {
        self.items.iter()
    }
}

impl<T> Default for Queue<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// Binary tree node
#[derive(Debug, Clone, PartialEq)]
pub struct TreeNode<T> {
    pub value: T,
    pub left: Option<Box<TreeNode<T>>>,
    pub right: Option<Box<TreeNode<T>>>,
}

impl<T> TreeNode<T> {
    pub fn new(value: T) -> Self {
        Self {
            value,
            left: None,
            right: None,
        }
    }

    pub fn with_children(value: T, left: Option<Box<TreeNode<T>>>, right: Option<Box<TreeNode<T>>>) -> Self {
        Self { value, left, right }
    }

    pub fn is_leaf(&self) -> bool {
        self.left.is_none() && self.right.is_none()
    }

    pub fn has_left_child(&self) -> bool {
        self.left.is_some()
    }

    pub fn has_right_child(&self) -> bool {
        self.right.is_some()
    }
}

/// Binary search tree implementation
#[derive(Debug, Clone)]
pub struct BinarySearchTree<T>
where
    T: Ord + Clone,
{
    root: Option<Box<TreeNode<T>>>,
    size: usize,
}

impl<T> BinarySearchTree<T>
where
    T: Ord + Clone,
{
    pub fn new() -> Self {
        Self {
            root: None,
            size: 0,
        }
    }

    pub fn insert(&mut self, value: T) {
        if self.root.is_none() {
            self.root = Some(Box::new(TreeNode::new(value)));
            self.size = 1;
        } else {
            if Self::insert_recursive(&mut self.root, value) {
                self.size += 1;
            }
        }
    }

    fn insert_recursive(node: &mut Option<Box<TreeNode<T>>>, value: T) -> bool {
        if let Some(ref mut n) = node {
            match value.cmp(&n.value) {
                std::cmp::Ordering::Less => Self::insert_recursive(&mut n.left, value),
                std::cmp::Ordering::Greater => Self::insert_recursive(&mut n.right, value),
                std::cmp::Ordering::Equal => false, // Value already exists
            }
        } else {
            *node = Some(Box::new(TreeNode::new(value)));
            true
        }
    }

    pub fn contains(&self, value: &T) -> bool {
        Self::contains_recursive(&self.root, value)
    }

    fn contains_recursive(node: &Option<Box<TreeNode<T>>>, value: &T) -> bool {
        if let Some(ref n) = node {
            match value.cmp(&n.value) {
                std::cmp::Ordering::Less => Self::contains_recursive(&n.left, value),
                std::cmp::Ordering::Greater => Self::contains_recursive(&n.right, value),
                std::cmp::Ordering::Equal => true,
            }
        } else {
            false
        }
    }

    pub fn remove(&mut self, value: &T) -> bool {
        let (new_root, removed) = Self::remove_recursive(self.root.take(), value);
        self.root = new_root;
        if removed {
            self.size -= 1;
        }
        removed
    }

    fn remove_recursive(node: Option<Box<TreeNode<T>>>, value: &T) -> (Option<Box<TreeNode<T>>>, bool) {
        if let Some(mut n) = node {
            match value.cmp(&n.value) {
                std::cmp::Ordering::Less => {
                    let (new_left, removed) = Self::remove_recursive(n.left.take(), value);
                    n.left = new_left;
                    (Some(n), removed)
                }
                std::cmp::Ordering::Greater => {
                    let (new_right, removed) = Self::remove_recursive(n.right.take(), value);
                    n.right = new_right;
                    (Some(n), removed)
                }
                std::cmp::Ordering::Equal => {
                    // Node to remove found
                    match (n.left.take(), n.right.take()) {
                        (None, None) => (None, true),
                        (Some(left), None) => (Some(left), true),
                        (None, Some(right)) => (Some(right), true),
                        (Some(left), Some(right)) => {
                            // Find inorder successor (minimum in right subtree)
                            let (min_value, new_right) = Self::extract_min(Some(right));
                            let mut new_node = Box::new(TreeNode::new(min_value));
                            new_node.left = Some(left);
                            new_node.right = new_right;
                            (Some(new_node), true)
                        }
                    }
                }
            }
        } else {
            (None, false)
        }
    }

    fn extract_min(node: Option<Box<TreeNode<T>>>) -> (T, Option<Box<TreeNode<T>>>) {
        if let Some(mut n) = node {
            if n.left.is_none() {
                (n.value, n.right.take())
            } else {
                let (min_value, new_left) = Self::extract_min(n.left.take());
                n.left = new_left;
                (min_value, Some(n))
            }
        } else {
            panic!("Cannot extract minimum from empty tree")
        }
    }

    pub fn inorder_traversal(&self) -> Vec<T> {
        let mut result = Vec::new();
        Self::inorder_recursive(&self.root, &mut result);
        result
    }

    fn inorder_recursive(node: &Option<Box<TreeNode<T>>>, result: &mut Vec<T>) {
        if let Some(ref n) = node {
            Self::inorder_recursive(&n.left, result);
            result.push(n.value.clone());
            Self::inorder_recursive(&n.right, result);
        }
    }

    pub fn preorder_traversal(&self) -> Vec<T> {
        let mut result = Vec::new();
        Self::preorder_recursive(&self.root, &mut result);
        result
    }

    fn preorder_recursive(node: &Option<Box<TreeNode<T>>>, result: &mut Vec<T>) {
        if let Some(ref n) = node {
            result.push(n.value.clone());
            Self::preorder_recursive(&n.left, result);
            Self::preorder_recursive(&n.right, result);
        }
    }

    pub fn postorder_traversal(&self) -> Vec<T> {
        let mut result = Vec::new();
        Self::postorder_recursive(&self.root, &mut result);
        result
    }

    fn postorder_recursive(node: &Option<Box<TreeNode<T>>>, result: &mut Vec<T>) {
        if let Some(ref n) = node {
            Self::postorder_recursive(&n.left, result);
            Self::postorder_recursive(&n.right, result);
            result.push(n.value.clone());
        }
    }

    pub fn height(&self) -> usize {
        Self::height_recursive(&self.root)
    }

    fn height_recursive(node: &Option<Box<TreeNode<T>>>) -> usize {
        if let Some(ref n) = node {
            1 + std::cmp::max(
                Self::height_recursive(&n.left),
                Self::height_recursive(&n.right)
            )
        } else {
            0
        }
    }

    pub fn size(&self) -> usize {
        self.size
    }

    pub fn is_empty(&self) -> bool {
        self.root.is_none()
    }

    pub fn clear(&mut self) {
        self.root = None;
        self.size = 0;
    }
}

impl<T> Default for BinarySearchTree<T>
where
    T: Ord + Clone,
{
    fn default() -> Self {
        Self::new()
    }
}

/// Hash table with custom collision resolution
#[derive(Debug, Clone)]
pub struct HashTable<K, V>
where
    K: Hash + Eq + Clone,
    V: Clone,
{
    buckets: Vec<Vec<(K, V)>>,
    size: usize,
    capacity: usize,
    load_factor_threshold: f64,
}

impl<K, V> HashTable<K, V>
where
    K: Hash + Eq + Clone,
    V: Clone,
{
    pub fn new() -> Self {
        Self::with_capacity(16)
    }

    pub fn with_capacity(capacity: usize) -> Self {
        let mut buckets = Vec::with_capacity(capacity);
        for _ in 0..capacity {
            buckets.push(Vec::new());
        }

        Self {
            buckets,
            size: 0,
            capacity,
            load_factor_threshold: 0.75,
        }
    }

    fn hash(&self, key: &K) -> usize {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::Hasher;

        let mut hasher = DefaultHasher::new();
        key.hash(&mut hasher);
        (hasher.finish() as usize) % self.capacity
    }

    pub fn insert(&mut self, key: K, value: V) -> Option<V> {
        if self.load_factor() > self.load_factor_threshold {
            self.resize();
        }

        let index = self.hash(&key);
        let bucket = &mut self.buckets[index];

        for (ref mut k, ref mut v) in bucket.iter_mut() {
            if *k == key {
                let old_value = v.clone();
                *v = value;
                return Some(old_value);
            }
        }

        bucket.push((key, value));
        self.size += 1;
        None
    }

    pub fn get(&self, key: &K) -> Option<&V> {
        let index = self.hash(key);
        let bucket = &self.buckets[index];

        for (k, v) in bucket.iter() {
            if k == key {
                return Some(v);
            }
        }

        None
    }

    pub fn remove(&mut self, key: &K) -> Option<V> {
        let index = self.hash(key);
        let bucket = &mut self.buckets[index];

        for (i, (k, _)) in bucket.iter().enumerate() {
            if k == key {
                let (_, value) = bucket.remove(i);
                self.size -= 1;
                return Some(value);
            }
        }

        None
    }

    pub fn contains_key(&self, key: &K) -> bool {
        self.get(key).is_some()
    }

    pub fn keys(&self) -> Vec<K> {
        let mut keys = Vec::new();
        for bucket in &self.buckets {
            for (k, _) in bucket {
                keys.push(k.clone());
            }
        }
        keys
    }

    pub fn values(&self) -> Vec<V> {
        let mut values = Vec::new();
        for bucket in &self.buckets {
            for (_, v) in bucket {
                values.push(v.clone());
            }
        }
        values
    }

    pub fn size(&self) -> usize {
        self.size
    }

    pub fn is_empty(&self) -> bool {
        self.size == 0
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn load_factor(&self) -> f64 {
        self.size as f64 / self.capacity as f64
    }

    pub fn clear(&mut self) {
        for bucket in &mut self.buckets {
            bucket.clear();
        }
        self.size = 0;
    }

    fn resize(&mut self) {
        let old_buckets = std::mem::replace(&mut self.buckets, Vec::new());
        self.capacity *= 2;
        self.size = 0;

        self.buckets = Vec::with_capacity(self.capacity);
        for _ in 0..self.capacity {
            self.buckets.push(Vec::new());
        }

        for bucket in old_buckets {
            for (key, value) in bucket {
                self.insert(key, value);
            }
        }
    }
}

impl<K, V> Default for HashTable<K, V>
where
    K: Hash + Eq + Clone,
    V: Clone,
{
    fn default() -> Self {
        Self::new()
    }
}

/// Circular buffer implementation
#[derive(Debug, Clone)]
pub struct CircularBuffer<T> {
    buffer: Vec<Option<T>>,
    head: usize,
    tail: usize,
    size: usize,
    capacity: usize,
}

impl<T> CircularBuffer<T>
where
    T: Clone,
{
    pub fn new(capacity: usize) -> Self {
        if capacity == 0 {
            panic!("Capacity must be greater than 0");
        }

        let mut buffer = Vec::with_capacity(capacity);
        for _ in 0..capacity {
            buffer.push(None);
        }

        Self {
            buffer,
            head: 0,
            tail: 0,
            size: 0,
            capacity,
        }
    }

    pub fn push(&mut self, item: T) -> Option<T> {
        let old_value = self.buffer[self.tail].clone();
        self.buffer[self.tail] = Some(item);

        self.tail = (self.tail + 1) % self.capacity;

        if self.size < self.capacity {
            self.size += 1;
            None
        } else {
            self.head = (self.head + 1) % self.capacity;
            old_value
        }
    }

    pub fn pop(&mut self) -> Option<T> {
        if self.is_empty() {
            return None;
        }

        self.tail = if self.tail == 0 { self.capacity - 1 } else { self.tail - 1 };
        let value = self.buffer[self.tail].take();
        self.size -= 1;
        value
    }

    pub fn peek(&self) -> Option<&T> {
        if self.is_empty() {
            None
        } else {
            let peek_index = if self.tail == 0 { self.capacity - 1 } else { self.tail - 1 };
            self.buffer[peek_index].as_ref()
        }
    }

    pub fn get(&self, index: usize) -> Option<&T> {
        if index >= self.size {
            return None;
        }

        let actual_index = (self.head + index) % self.capacity;
        self.buffer[actual_index].as_ref()
    }

    pub fn is_empty(&self) -> bool {
        self.size == 0
    }

    pub fn is_full(&self) -> bool {
        self.size == self.capacity
    }

    pub fn size(&self) -> usize {
        self.size
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn clear(&mut self) {
        for item in &mut self.buffer {
            *item = None;
        }
        self.head = 0;
        self.tail = 0;
        self.size = 0;
    }

    pub fn to_vec(&self) -> Vec<T> {
        let mut result = Vec::with_capacity(self.size);
        for i in 0..self.size {
            if let Some(ref item) = self.get(i) {
                result.push((*item).clone());
            }
        }
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stack_operations() {
        let mut stack = Stack::new();

        assert!(stack.is_empty());
        assert_eq!(stack.len(), 0);

        stack.push(1).unwrap();
        stack.push(2).unwrap();
        stack.push(3).unwrap();

        assert_eq!(stack.len(), 3);
        assert_eq!(stack.peek(), Some(&3));
        assert_eq!(stack.pop(), Some(3));
        assert_eq!(stack.pop(), Some(2));
        assert_eq!(stack.len(), 1);
    }

    #[test]
    fn test_queue_operations() {
        let mut queue = Queue::new();

        assert!(queue.is_empty());

        queue.enqueue(1).unwrap();
        queue.enqueue(2).unwrap();
        queue.enqueue(3).unwrap();

        assert_eq!(queue.len(), 3);
        assert_eq!(queue.front(), Some(&1));
        assert_eq!(queue.back(), Some(&3));
        assert_eq!(queue.dequeue(), Some(1));
        assert_eq!(queue.dequeue(), Some(2));
        assert_eq!(queue.len(), 1);
    }

    #[test]
    fn test_binary_search_tree() {
        let mut bst = BinarySearchTree::new();

        bst.insert(5);
        bst.insert(3);
        bst.insert(7);
        bst.insert(1);
        bst.insert(9);

        assert_eq!(bst.size(), 5);
        assert!(bst.contains(&5));
        assert!(bst.contains(&3));
        assert!(!bst.contains(&10));

        let inorder = bst.inorder_traversal();
        assert_eq!(inorder, vec![1, 3, 5, 7, 9]);

        assert!(bst.remove(&3));
        assert!(!bst.contains(&3));
        assert_eq!(bst.size(), 4);
    }

    #[test]
    fn test_hash_table() {
        let mut ht = HashTable::new();

        assert!(ht.is_empty());

        ht.insert("key1", "value1");
        ht.insert("key2", "value2");
        ht.insert("key3", "value3");

        assert_eq!(ht.size(), 3);
        assert_eq!(ht.get(&"key1"), Some(&"value1"));
        assert_eq!(ht.get(&"key2"), Some(&"value2"));
        assert_eq!(ht.get(&"nonexistent"), None);

        assert_eq!(ht.remove(&"key1"), Some("value1"));
        assert_eq!(ht.size(), 2);
        assert!(!ht.contains_key(&"key1"));
    }

    #[test]
    fn test_circular_buffer() {
        let mut cb = CircularBuffer::new(3);

        assert!(cb.is_empty());
        assert!(!cb.is_full());

        assert_eq!(cb.push(1), None);
        assert_eq!(cb.push(2), None);
        assert_eq!(cb.push(3), None);

        assert!(cb.is_full());
        assert_eq!(cb.size(), 3);

        // Buffer is full, pushing should return the overwritten value
        assert_eq!(cb.push(4), Some(1));
        assert_eq!(cb.get(0), Some(&2));
        assert_eq!(cb.get(1), Some(&3));
        assert_eq!(cb.get(2), Some(&4));
    }
}
