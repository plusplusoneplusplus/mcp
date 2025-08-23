/*!
 * Sample Rust library demonstrating various language constructs for ctags testing.
 *
 * This library includes:
 * - Structs with various field types
 * - Enums with different variants
 * - Traits and implementations
 * - Generic types and functions
 * - Modules and visibility modifiers
 */

pub mod collections;
pub mod geometry;
pub mod utils;

use serde::{Deserialize, Serialize};

/// Result type alias for this library
pub type LibResult<T> = Result<T, LibError>;

/// Error types for the library
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LibError {
    InvalidInput(String),
    CalculationError { message: String, code: i32 },
    IoError(String),
    ParseError,
}

impl std::fmt::Display for LibError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LibError::InvalidInput(msg) => write!(f, "Invalid input: {}", msg),
            LibError::CalculationError { message, code } => {
                write!(f, "Calculation error [{}]: {}", code, message)
            }
            LibError::IoError(msg) => write!(f, "IO error: {}", msg),
            LibError::ParseError => write!(f, "Parse error"),
        }
    }
}

impl std::error::Error for LibError {}

/// Configuration structure for the library
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub debug_mode: bool,
    pub max_iterations: usize,
    pub tolerance: f64,
    pub output_format: OutputFormat,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            debug_mode: false,
            max_iterations: 1000,
            tolerance: 1e-6,
            output_format: OutputFormat::Json,
        }
    }
}

/// Output format enumeration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OutputFormat {
    Json,
    Yaml,
    Csv,
    Binary { compression: bool },
}

/// Generic container for data processing
#[derive(Debug, Clone)]
pub struct Container<T> {
    data: Vec<T>,
    metadata: ContainerMetadata,
}

impl<T> Container<T> {
    pub fn new() -> Self {
        Self {
            data: Vec::new(),
            metadata: ContainerMetadata::default(),
        }
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            data: Vec::with_capacity(capacity),
            metadata: ContainerMetadata::default(),
        }
    }

    pub fn push(&mut self, item: T) {
        self.data.push(item);
        self.metadata.count += 1;
    }

    pub fn len(&self) -> usize {
        self.data.len()
    }

    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    pub fn get(&self, index: usize) -> Option<&T> {
        self.data.get(index)
    }

    pub fn iter(&self) -> std::slice::Iter<'_, T> {
        self.data.iter()
    }
}

impl<T> Default for Container<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// Metadata for containers
#[derive(Debug, Clone, Default)]
struct ContainerMetadata {
    count: usize,
    created_at: Option<std::time::SystemTime>,
    last_modified: Option<std::time::SystemTime>,
}

/// Trait for processable items
pub trait Processable {
    type Output;
    type Error;

    fn process(&self) -> Result<Self::Output, Self::Error>;
    fn validate(&self) -> bool;
    fn reset(&mut self);
}

/// Trait for serializable items
pub trait Serializable {
    fn serialize(&self) -> LibResult<String>;
    fn deserialize(data: &str) -> LibResult<Self>
    where
        Self: Sized;
}

/// Generic processor for different data types
pub struct Processor<T> {
    items: Vec<T>,
    config: Config,
    state: ProcessorState,
}

impl<T> Processor<T>
where
    T: Processable + Clone,
{
    pub fn new(config: Config) -> Self {
        Self {
            items: Vec::new(),
            config,
            state: ProcessorState::Idle,
        }
    }

    pub fn add_item(&mut self, item: T) {
        self.items.push(item);
    }

    pub fn process_all(&mut self) -> LibResult<Vec<T::Output>> {
        self.state = ProcessorState::Processing;

        let mut results = Vec::new();
        for item in &self.items {
            match item.process() {
                Ok(output) => results.push(output),
                Err(_) => {
                    self.state = ProcessorState::Error;
                    return Err(LibError::CalculationError {
                        message: "Processing failed".to_string(),
                        code: 1001,
                    });
                }
            }
        }

        self.state = ProcessorState::Completed;
        Ok(results)
    }

    pub fn get_state(&self) -> &ProcessorState {
        &self.state
    }

    pub fn reset(&mut self) {
        self.items.clear();
        self.state = ProcessorState::Idle;
    }
}

/// Processor state enumeration
#[derive(Debug, Clone, PartialEq)]
pub enum ProcessorState {
    Idle,
    Processing,
    Completed,
    Error,
}

/// Constants and static values
pub mod constants {
    pub const VERSION: &str = "0.1.0";
    pub const MAX_BUFFER_SIZE: usize = 8192;
    pub const DEFAULT_TIMEOUT_MS: u64 = 5000;

    pub static SUPPORTED_FORMATS: &[&str] = &["json", "yaml", "csv", "binary"];
}

/// Utility functions
pub fn initialize_library() -> LibResult<()> {
    // Library initialization logic
    Ok(())
}

pub fn cleanup_library() {
    // Cleanup logic
}

/// Generic function for type conversion
pub fn convert_type<T, U>(input: T) -> LibResult<U>
where
    T: Into<U>,
{
    Ok(input.into())
}

/// Function with lifetime parameters
pub fn find_longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() {
        x
    } else {
        y
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_default() {
        let config = Config::default();
        assert!(!config.debug_mode);
        assert_eq!(config.max_iterations, 1000);
    }

    #[test]
    fn test_container_operations() {
        let mut container = Container::<i32>::new();
        assert!(container.is_empty());

        container.push(42);
        assert_eq!(container.len(), 1);
        assert_eq!(container.get(0), Some(&42));
    }
}
