/*!
 * Main application demonstrating the sample Rust library functionality.
 */

use sample_rust_project::{
    Config, OutputFormat, Container, Processor, ProcessorState,
    LibResult, LibError, Processable, Serializable,
    constants,
};
use sample_rust_project::geometry::{Point2D, Rectangle, Circle, Triangle, Shape, Drawable};
use sample_rust_project::utils::{math, string, StatisticsCalculator, Cache};
use sample_rust_project::collections::{Stack, Queue, BinarySearchTree, HashTable, CircularBuffer};

use std::fmt::Display;

/// Example struct that implements the Processable trait
#[derive(Debug, Clone)]
struct DataPoint {
    id: u32,
    value: f64,
    label: String,
    processed: bool,
}

impl DataPoint {
    fn new(id: u32, value: f64, label: String) -> Self {
        Self {
            id,
            value,
            label,
            processed: false,
        }
    }
}

impl Processable for DataPoint {
    type Output = f64;
    type Error = LibError;

    fn process(&self) -> Result<Self::Output, Self::Error> {
        if self.value < 0.0 {
            Err(LibError::CalculationError {
                message: format!("Negative value in data point {}", self.id),
                code: 2001,
            })
        } else {
            Ok(self.value * 2.0) // Simple processing: double the value
        }
    }

    fn validate(&self) -> bool {
        !self.label.is_empty() && self.value.is_finite()
    }

    fn reset(&mut self) {
        self.processed = false;
        self.value = 0.0;
    }
}

impl Serializable for DataPoint {
    fn serialize(&self) -> LibResult<String> {
        serde_json::to_string(self)
            .map_err(|e| LibError::ParseError)
    }

    fn deserialize(data: &str) -> LibResult<Self> {
        serde_json::from_str(data)
            .map_err(|e| LibError::ParseError)
    }
}

impl serde::Serialize for DataPoint {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeStruct;
        let mut state = serializer.serialize_struct("DataPoint", 4)?;
        state.serialize_field("id", &self.id)?;
        state.serialize_field("value", &self.value)?;
        state.serialize_field("label", &self.label)?;
        state.serialize_field("processed", &self.processed)?;
        state.end()
    }
}

impl<'de> serde::Deserialize<'de> for DataPoint {
    fn deserialize<D>(deserializer: D) -> Result<DataPoint, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        use serde::de::{self, MapAccess, SeqAccess, Visitor};
        use std::fmt;

        #[derive(serde::Deserialize)]
        #[serde(field_identifier, rename_all = "lowercase")]
        enum Field { Id, Value, Label, Processed }

        struct DataPointVisitor;

        impl<'de> Visitor<'de> for DataPointVisitor {
            type Value = DataPoint;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("struct DataPoint")
            }

            fn visit_map<V>(self, mut map: V) -> Result<DataPoint, V::Error>
            where
                V: MapAccess<'de>,
            {
                let mut id = None;
                let mut value = None;
                let mut label = None;
                let mut processed = None;

                while let Some(key) = map.next_key()? {
                    match key {
                        Field::Id => {
                            if id.is_some() {
                                return Err(de::Error::duplicate_field("id"));
                            }
                            id = Some(map.next_value()?);
                        }
                        Field::Value => {
                            if value.is_some() {
                                return Err(de::Error::duplicate_field("value"));
                            }
                            value = Some(map.next_value()?);
                        }
                        Field::Label => {
                            if label.is_some() {
                                return Err(de::Error::duplicate_field("label"));
                            }
                            label = Some(map.next_value()?);
                        }
                        Field::Processed => {
                            if processed.is_some() {
                                return Err(de::Error::duplicate_field("processed"));
                            }
                            processed = Some(map.next_value()?);
                        }
                    }
                }

                let id = id.ok_or_else(|| de::Error::missing_field("id"))?;
                let value = value.ok_or_else(|| de::Error::missing_field("value"))?;
                let label = label.ok_or_else(|| de::Error::missing_field("label"))?;
                let processed = processed.ok_or_else(|| de::Error::missing_field("processed"))?;

                Ok(DataPoint { id, value, label, processed })
            }
        }

        const FIELDS: &'static [&'static str] = &["id", "value", "label", "processed"];
        deserializer.deserialize_struct("DataPoint", FIELDS, DataPointVisitor)
    }
}

/// Demonstrates geometry functionality
fn demonstrate_geometry() {
    println!("\n=== Geometry Demonstration ===");

    // Create various shapes
    let mut rect = Rectangle::new(0.0, 0.0, 5.0, 3.0);
    let mut circle = Circle::new(10.0, 10.0, 4.0);
    let triangle = Triangle::new(
        Point2D::new(0.0, 0.0),
        Point2D::new(3.0, 0.0),
        Point2D::new(1.5, 2.6),
    );

    println!("Rectangle: {}", rect.draw());
    println!("  Area: {:.2}", rect.area());
    println!("  Perimeter: {:.2}", rect.perimeter());
    println!("  Center: ({:.2}, {:.2})", rect.center().x, rect.center().y);

    println!("Circle: {}", circle.draw());
    println!("  Area: {:.2}", circle.area());
    println!("  Circumference: {:.2}", circle.perimeter());

    println!("Triangle area: {:.2}", triangle.area());
    println!("Triangle perimeter: {:.2}", triangle.perimeter());

    // Test point containment
    let test_point = Point2D::new(2.0, 1.0);
    println!("Point ({}, {}) is in rectangle: {}",
             test_point.x, test_point.y, rect.contains_point(&test_point));
    println!("Point ({}, {}) is in circle: {}",
             test_point.x, test_point.y, circle.contains_point(&test_point));

    // Move shapes
    rect.translate(5.0, 5.0);
    circle.translate(-5.0, -5.0);
    println!("After moving:");
    println!("  Rectangle center: ({:.2}, {:.2})", rect.center().x, rect.center().y);
    println!("  Circle center: ({:.2}, {:.2})", circle.center().x, circle.center().y);
}

/// Demonstrates utility functions
fn demonstrate_utilities() {
    println!("\n=== Utilities Demonstration ===");

    // Math utilities
    println!("Math utilities:");
    println!("  Clamp 15 to [0, 10]: {}", math::clamp(15, 0, 10));
    println!("  Linear interpolation 0->100 at t=0.3: {:.2}", math::lerp(0.0, 100.0, 0.3));
    println!("  Factorial of 6: {}", math::factorial(6));
    println!("  10th Fibonacci number: {}", math::fibonacci(10));
    println!("  GCD of 48 and 18: {}", math::gcd(48, 18));
    println!("  90 degrees to radians: {:.4}", math::degrees_to_radians(90.0));

    // String utilities
    println!("\nString utilities:");
    let text = "hello world";
    println!("  Original: '{}'", text);
    println!("  Reversed: '{}'", string::reverse_string(text));
    println!("  Capitalized: '{}'", string::capitalize_words(text));
    println!("  Word count: {}", string::word_count(text));

    let palindrome = "racecar";
    println!("  '{}' is palindrome: {}", palindrome, string::is_palindrome(palindrome));

    let numbers_text = "abc 123 def 456 ghi 789";
    println!("  Numbers in '{}': {:?}", numbers_text, string::extract_numbers(numbers_text));

    // Statistics
    println!("\nStatistics:");
    let mut calc = StatisticsCalculator::new();
    let data = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0];
    calc.add_values(&data);

    match calc.calculate() {
        Ok(stats) => {
            println!("  Count: {}", stats.count);
            println!("  Mean: {:.2}", stats.mean);
            println!("  Median: {:.2}", stats.median);
            println!("  Std Dev: {:.2}", stats.std_deviation);
            println!("  Range: [{:.2}, {:.2}]", stats.min, stats.max);
        }
        Err(e) => println!("  Statistics error: {}", e),
    }

    // Cache demonstration
    println!("\nCache demonstration:");
    let mut cache: Cache<String, i32> = Cache::new(3);
    cache.put("one".to_string(), 1);
    cache.put("two".to_string(), 2);
    cache.put("three".to_string(), 3);

    println!("  Cache size: {}", cache.size());
    println!("  Get 'two': {:?}", cache.get(&"two".to_string()));

    // Adding fourth item should evict least recently used
    cache.put("four".to_string(), 4);
    println!("  After adding 'four', cache size: {}", cache.size());
}

/// Demonstrates collection types
fn demonstrate_collections() {
    println!("\n=== Collections Demonstration ===");

    // Stack
    println!("Stack operations:");
    let mut stack = Stack::new();
    stack.push(1).unwrap();
    stack.push(2).unwrap();
    stack.push(3).unwrap();

    println!("  Stack size: {}", stack.len());
    println!("  Peek: {:?}", stack.peek());
    println!("  Pop: {:?}", stack.pop());
    println!("  Pop: {:?}", stack.pop());

    // Queue
    println!("\nQueue operations:");
    let mut queue = Queue::new();
    queue.enqueue("first").unwrap();
    queue.enqueue("second").unwrap();
    queue.enqueue("third").unwrap();

    println!("  Queue size: {}", queue.len());
    println!("  Front: {:?}", queue.front());
    println!("  Dequeue: {:?}", queue.dequeue());
    println!("  Dequeue: {:?}", queue.dequeue());

    // Binary Search Tree
    println!("\nBinary Search Tree:");
    let mut bst = BinarySearchTree::new();
    let values = vec![5, 3, 7, 2, 4, 6, 8];
    for val in values {
        bst.insert(val);
    }

    println!("  Tree size: {}", bst.size());
    println!("  Contains 4: {}", bst.contains(&4));
    println!("  Contains 9: {}", bst.contains(&9));
    println!("  Inorder traversal: {:?}", bst.inorder_traversal());
    println!("  Tree height: {}", bst.height());

    // Hash Table
    println!("\nHash Table:");
    let mut ht = HashTable::new();
    ht.insert("apple", 5);
    ht.insert("banana", 3);
    ht.insert("cherry", 8);
    ht.insert("date", 2);

    println!("  Hash table size: {}", ht.size());
    println!("  Load factor: {:.2}", ht.load_factor());
    println!("  Get 'banana': {:?}", ht.get(&"banana"));
    println!("  Keys: {:?}", ht.keys());

    // Circular Buffer
    println!("\nCircular Buffer:");
    let mut cb = CircularBuffer::new(4);
    println!("  Push 1: {:?}", cb.push(1));
    println!("  Push 2: {:?}", cb.push(2));
    println!("  Push 3: {:?}", cb.push(3));
    println!("  Push 4: {:?}", cb.push(4));
    println!("  Buffer is full: {}", cb.is_full());

    // This should overwrite the first element
    println!("  Push 5 (should overwrite): {:?}", cb.push(5));
    println!("  Buffer contents: {:?}", cb.to_vec());
}

/// Demonstrates data processing
fn demonstrate_processing() {
    println!("\n=== Data Processing Demonstration ===");

    let config = Config {
        debug_mode: true,
        max_iterations: 100,
        tolerance: 1e-6,
        output_format: OutputFormat::Json,
    };

    let mut processor = Processor::new(config);

    // Create test data
    let data_points = vec![
        DataPoint::new(1, 10.5, "Point A".to_string()),
        DataPoint::new(2, 15.2, "Point B".to_string()),
        DataPoint::new(3, 8.7, "Point C".to_string()),
        DataPoint::new(4, 22.1, "Point D".to_string()),
    ];

    // Add data to processor
    for point in data_points {
        processor.add_item(point);
    }

    println!("Processor state: {:?}", processor.get_state());

    // Process all data
    match processor.process_all() {
        Ok(results) => {
            println!("Processing completed successfully!");
            println!("Results: {:?}", results);
            println!("Final state: {:?}", processor.get_state());
        }
        Err(e) => {
            println!("Processing failed: {}", e);
        }
    }

    // Demonstrate container
    println!("\nContainer operations:");
    let mut container: Container<String> = Container::new();
    container.push("Item 1".to_string());
    container.push("Item 2".to_string());
    container.push("Item 3".to_string());

    println!("  Container size: {}", container.len());
    println!("  Get item 1: {:?}", container.get(1));

    println!("  Container contents:");
    for (i, item) in container.iter().enumerate() {
        println!("    [{}]: {}", i, item);
    }
}

/// Demonstrates serialization
fn demonstrate_serialization() {
    println!("\n=== Serialization Demonstration ===");

    let data_point = DataPoint::new(42, 3.14159, "Pi Point".to_string());

    match data_point.serialize() {
        Ok(json_str) => {
            println!("Serialized data point:");
            println!("  {}", json_str);

            match DataPoint::deserialize(&json_str) {
                Ok(deserialized) => {
                    println!("Deserialization successful!");
                    println!("  ID: {}, Value: {:.5}, Label: '{}'",
                             deserialized.id, deserialized.value, deserialized.label);
                }
                Err(e) => println!("Deserialization failed: {}", e),
            }
        }
        Err(e) => println!("Serialization failed: {}", e),
    }

    // Demonstrate various data structures serialization
    let rect = Rectangle::new(5.0, 10.0, 20.0, 15.0);
    match serde_json::to_string(&rect) {
        Ok(json) => println!("Rectangle JSON: {}", json),
        Err(e) => println!("Rectangle serialization failed: {}", e),
    }

    let circle = Circle::new(0.0, 0.0, 5.0);
    match serde_json::to_string(&circle) {
        Ok(json) => println!("Circle JSON: {}", json),
        Err(e) => println!("Circle serialization failed: {}", e),
    }
}

/// Main application entry point
fn main() -> LibResult<()> {
    println!("Sample Rust Project - Version {}", constants::VERSION);
    println!("Max buffer size: {}", constants::MAX_BUFFER_SIZE);
    println!("Supported formats: {:?}", constants::SUPPORTED_FORMATS);

    // Initialize the library
    sample_rust_project::initialize_library()?;

    // Run demonstrations
    demonstrate_geometry();
    demonstrate_utilities();
    demonstrate_collections();
    demonstrate_processing();
    demonstrate_serialization();

    // Performance and error demonstration
    println!("\n=== Error Handling Demonstration ===");

    // Try to create invalid data
    let mut invalid_processor = Processor::new(Config::default());
    let invalid_point = DataPoint::new(99, -5.0, "Invalid".to_string()); // Negative value
    invalid_processor.add_item(invalid_point);

    match invalid_processor.process_all() {
        Ok(_) => println!("Unexpected success with invalid data"),
        Err(e) => println!("Expected error caught: {}", e),
    }

    // Demonstrate different error types
    let errors = vec![
        LibError::InvalidInput("Test invalid input".to_string()),
        LibError::CalculationError {
            message: "Test calculation error".to_string(),
            code: 500
        },
        LibError::IoError("Test IO error".to_string()),
        LibError::ParseError,
    ];

    println!("\nError types demonstration:");
    for (i, error) in errors.iter().enumerate() {
        println!("  Error {}: {}", i + 1, error);
    }

    // Cleanup
    sample_rust_project::cleanup_library();
    println!("\n=== Demonstration Complete ===");

    Ok(())
}
