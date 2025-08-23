/*!
 * Utility functions and helper structures.
 */

use crate::{LibError, LibResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::hash::Hash;

/// Mathematical utility functions
pub mod math {
    use std::f64::consts::PI;

    pub fn clamp<T: PartialOrd>(value: T, min: T, max: T) -> T {
        if value < min {
            min
        } else if value > max {
            max
        } else {
            value
        }
    }

    pub fn lerp(a: f64, b: f64, t: f64) -> f64 {
        a + t * (b - a)
    }

    pub fn degrees_to_radians(degrees: f64) -> f64 {
        degrees * PI / 180.0
    }

    pub fn radians_to_degrees(radians: f64) -> f64 {
        radians * 180.0 / PI
    }

    pub fn is_approximately_equal(a: f64, b: f64, epsilon: f64) -> bool {
        (a - b).abs() < epsilon
    }

    pub fn factorial(n: u64) -> u64 {
        match n {
            0 | 1 => 1,
            _ => n * factorial(n - 1),
        }
    }

    pub fn fibonacci(n: u32) -> u64 {
        match n {
            0 => 0,
            1 => 1,
            _ => fibonacci(n - 1) + fibonacci(n - 2),
        }
    }

    pub fn gcd(a: u64, b: u64) -> u64 {
        if b == 0 {
            a
        } else {
            gcd(b, a % b)
        }
    }

    pub fn lcm(a: u64, b: u64) -> u64 {
        if a == 0 || b == 0 {
            0
        } else {
            (a * b) / gcd(a, b)
        }
    }
}

/// String utility functions
pub mod string {
    use super::LibResult;
    use super::LibError;

    pub fn reverse_string(input: &str) -> String {
        input.chars().rev().collect()
    }

    pub fn is_palindrome(input: &str) -> bool {
        let cleaned: String = input.chars()
            .filter(|c| c.is_alphanumeric())
            .map(|c| c.to_lowercase().next().unwrap())
            .collect();

        cleaned == reverse_string(&cleaned)
    }

    pub fn word_count(input: &str) -> usize {
        input.split_whitespace().count()
    }

    pub fn capitalize_words(input: &str) -> String {
        input.split_whitespace()
            .map(|word| {
                let mut chars = word.chars();
                match chars.next() {
                    None => String::new(),
                    Some(first) => first.to_uppercase().collect::<String>() + &chars.as_str().to_lowercase(),
                }
            })
            .collect::<Vec<_>>()
            .join(" ")
    }

    pub fn extract_numbers(input: &str) -> Vec<i32> {
        input.split_whitespace()
            .filter_map(|s| s.parse().ok())
            .collect()
    }

    pub fn validate_email(email: &str) -> LibResult<bool> {
        if email.is_empty() {
            return Err(LibError::InvalidInput("Email cannot be empty".to_string()));
        }

        let parts: Vec<&str> = email.split('@').collect();
        if parts.len() != 2 {
            return Ok(false);
        }

        let local = parts[0];
        let domain = parts[1];

        if local.is_empty() || domain.is_empty() {
            return Ok(false);
        }

        if !domain.contains('.') {
            return Ok(false);
        }

        Ok(true)
    }
}

/// File and I/O utilities
pub mod io {
    use super::{LibError, LibResult};
    use std::fs;
    use std::path::Path;

    pub fn read_file_to_string<P: AsRef<Path>>(path: P) -> LibResult<String> {
        fs::read_to_string(path)
            .map_err(|e| LibError::IoError(format!("Failed to read file: {}", e)))
    }

    pub fn write_string_to_file<P: AsRef<Path>>(path: P, content: &str) -> LibResult<()> {
        fs::write(path, content)
            .map_err(|e| LibError::IoError(format!("Failed to write file: {}", e)))
    }

    pub fn file_exists<P: AsRef<Path>>(path: P) -> bool {
        path.as_ref().exists()
    }

    pub fn get_file_size<P: AsRef<Path>>(path: P) -> LibResult<u64> {
        let metadata = fs::metadata(path)
            .map_err(|e| LibError::IoError(format!("Failed to get file metadata: {}", e)))?;
        Ok(metadata.len())
    }

    pub fn create_directory<P: AsRef<Path>>(path: P) -> LibResult<()> {
        fs::create_dir_all(path)
            .map_err(|e| LibError::IoError(format!("Failed to create directory: {}", e)))
    }

    pub fn list_directory<P: AsRef<Path>>(path: P) -> LibResult<Vec<String>> {
        let entries = fs::read_dir(path)
            .map_err(|e| LibError::IoError(format!("Failed to read directory: {}", e)))?;

        let mut result = Vec::new();
        for entry in entries {
            let entry = entry
                .map_err(|e| LibError::IoError(format!("Failed to read directory entry: {}", e)))?;

            if let Some(file_name) = entry.file_name().to_str() {
                result.push(file_name.to_string());
            }
        }

        result.sort();
        Ok(result)
    }
}

/// Statistics and data analysis utilities
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Statistics {
    pub count: usize,
    pub sum: f64,
    pub mean: f64,
    pub median: f64,
    pub mode: Option<f64>,
    pub std_deviation: f64,
    pub variance: f64,
    pub min: f64,
    pub max: f64,
    pub range: f64,
}

impl Statistics {
    pub fn new() -> Self {
        Self {
            count: 0,
            sum: 0.0,
            mean: 0.0,
            median: 0.0,
            mode: None,
            std_deviation: 0.0,
            variance: 0.0,
            min: 0.0,
            max: 0.0,
            range: 0.0,
        }
    }
}

impl Default for Statistics {
    fn default() -> Self {
        Self::new()
    }
}

pub struct StatisticsCalculator {
    data: Vec<f64>,
    dirty: bool,
    cached_stats: Option<Statistics>,
}

impl StatisticsCalculator {
    pub fn new() -> Self {
        Self {
            data: Vec::new(),
            dirty: true,
            cached_stats: None,
        }
    }

    pub fn add_value(&mut self, value: f64) {
        self.data.push(value);
        self.dirty = true;
        self.cached_stats = None;
    }

    pub fn add_values(&mut self, values: &[f64]) {
        self.data.extend_from_slice(values);
        self.dirty = true;
        self.cached_stats = None;
    }

    pub fn clear(&mut self) {
        self.data.clear();
        self.dirty = true;
        self.cached_stats = None;
    }

    pub fn calculate(&mut self) -> LibResult<Statistics> {
        if !self.dirty && self.cached_stats.is_some() {
            return Ok(self.cached_stats.clone().unwrap());
        }

        if self.data.is_empty() {
            return Err(LibError::InvalidInput("No data to calculate statistics".to_string()));
        }

        let count = self.data.len();
        let sum: f64 = self.data.iter().sum();
        let mean = sum / count as f64;

        // Sort data for median calculation
        let mut sorted_data = self.data.clone();
        sorted_data.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let median = if count % 2 == 0 {
            (sorted_data[count / 2 - 1] + sorted_data[count / 2]) / 2.0
        } else {
            sorted_data[count / 2]
        };

        let min = *sorted_data.first().unwrap();
        let max = *sorted_data.last().unwrap();
        let range = max - min;

        // Calculate variance and standard deviation
        let variance = self.data.iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>() / count as f64;
        let std_deviation = variance.sqrt();

        // Calculate mode (most frequent value)
        let mode = self.calculate_mode();

        let stats = Statistics {
            count,
            sum,
            mean,
            median,
            mode,
            std_deviation,
            variance,
            min,
            max,
            range,
        };

        self.cached_stats = Some(stats.clone());
        self.dirty = false;

        Ok(stats)
    }

    fn calculate_mode(&self) -> Option<f64> {
        let mut frequency_map = HashMap::new();

        for &value in &self.data {
            *frequency_map.entry(value as i64) += 1;
        }

        frequency_map.into_iter()
            .max_by_key(|(_, count)| *count)
            .map(|(value, _)| value as f64)
    }

    pub fn percentile(&self, p: f64) -> LibResult<f64> {
        if self.data.is_empty() {
            return Err(LibError::InvalidInput("No data available".to_string()));
        }

        if !(0.0..=100.0).contains(&p) {
            return Err(LibError::InvalidInput("Percentile must be between 0 and 100".to_string()));
        }

        let mut sorted_data = self.data.clone();
        sorted_data.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let index = (p / 100.0) * (sorted_data.len() - 1) as f64;
        let lower = index.floor() as usize;
        let upper = index.ceil() as usize;

        if lower == upper {
            Ok(sorted_data[lower])
        } else {
            let weight = index - lower as f64;
            Ok(sorted_data[lower] * (1.0 - weight) + sorted_data[upper] * weight)
        }
    }

    pub fn outliers(&self, method: OutlierMethod) -> Vec<f64> {
        match method {
            OutlierMethod::Iqr => self.iqr_outliers(),
            OutlierMethod::ZScore(threshold) => self.zscore_outliers(threshold),
        }
    }

    fn iqr_outliers(&self) -> Vec<f64> {
        if self.data.len() < 4 {
            return Vec::new();
        }

        let q1 = self.percentile(25.0).unwrap_or(0.0);
        let q3 = self.percentile(75.0).unwrap_or(0.0);
        let iqr = q3 - q1;
        let lower_bound = q1 - 1.5 * iqr;
        let upper_bound = q3 + 1.5 * iqr;

        self.data.iter()
            .filter(|&&x| x < lower_bound || x > upper_bound)
            .copied()
            .collect()
    }

    fn zscore_outliers(&self, threshold: f64) -> Vec<f64> {
        if self.data.is_empty() {
            return Vec::new();
        }

        let mean: f64 = self.data.iter().sum::<f64>() / self.data.len() as f64;
        let variance = self.data.iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>() / self.data.len() as f64;
        let std_dev = variance.sqrt();

        if std_dev == 0.0 {
            return Vec::new();
        }

        self.data.iter()
            .filter(|&&x| ((x - mean) / std_dev).abs() > threshold)
            .copied()
            .collect()
    }
}

impl Default for StatisticsCalculator {
    fn default() -> Self {
        Self::new()
    }
}

/// Outlier detection methods
#[derive(Debug, Clone)]
pub enum OutlierMethod {
    Iqr,
    ZScore(f64),
}

/// Generic cache implementation
pub struct Cache<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    store: HashMap<K, CacheEntry<V>>,
    max_size: usize,
    access_count: u64,
}

#[derive(Debug, Clone)]
struct CacheEntry<V> {
    value: V,
    access_count: u64,
    created_at: std::time::Instant,
}

impl<K, V> Cache<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    pub fn new(max_size: usize) -> Self {
        Self {
            store: HashMap::new(),
            max_size,
            access_count: 0,
        }
    }

    pub fn get(&mut self, key: &K) -> Option<V> {
        self.access_count += 1;

        if let Some(entry) = self.store.get_mut(key) {
            entry.access_count = self.access_count;
            Some(entry.value.clone())
        } else {
            None
        }
    }

    pub fn put(&mut self, key: K, value: V) {
        self.access_count += 1;

        if self.store.len() >= self.max_size && !self.store.contains_key(&key) {
            self.evict_lru();
        }

        let entry = CacheEntry {
            value,
            access_count: self.access_count,
            created_at: std::time::Instant::now(),
        };

        self.store.insert(key, entry);
    }

    pub fn remove(&mut self, key: &K) -> Option<V> {
        self.store.remove(key).map(|entry| entry.value)
    }

    pub fn clear(&mut self) {
        self.store.clear();
    }

    pub fn size(&self) -> usize {
        self.store.len()
    }

    pub fn is_empty(&self) -> bool {
        self.store.is_empty()
    }

    fn evict_lru(&mut self) {
        if let Some(lru_key) = self.store.iter()
            .min_by_key(|(_, entry)| entry.access_count)
            .map(|(k, _)| k.clone())
        {
            self.store.remove(&lru_key);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_math_functions() {
        assert_eq!(math::clamp(5, 0, 10), 5);
        assert_eq!(math::clamp(-5, 0, 10), 0);
        assert_eq!(math::clamp(15, 0, 10), 10);

        assert!((math::lerp(0.0, 10.0, 0.5) - 5.0).abs() < f64::EPSILON);

        assert_eq!(math::factorial(5), 120);
        assert_eq!(math::fibonacci(10), 55);
        assert_eq!(math::gcd(48, 18), 6);
        assert_eq!(math::lcm(12, 18), 36);
    }

    #[test]
    fn test_string_functions() {
        assert_eq!(string::reverse_string("hello"), "olleh");
        assert!(string::is_palindrome("racecar"));
        assert!(!string::is_palindrome("hello"));
        assert_eq!(string::word_count("hello world test"), 3);
        assert_eq!(string::capitalize_words("hello world"), "Hello World");
        assert_eq!(string::extract_numbers("test 123 hello 456"), vec![123, 456]);
    }

    #[test]
    fn test_statistics_calculator() {
        let mut calc = StatisticsCalculator::new();
        calc.add_values(&[1.0, 2.0, 3.0, 4.0, 5.0]);

        let stats = calc.calculate().unwrap();
        assert_eq!(stats.count, 5);
        assert_eq!(stats.mean, 3.0);
        assert_eq!(stats.median, 3.0);
        assert_eq!(stats.min, 1.0);
        assert_eq!(stats.max, 5.0);

        let p50 = calc.percentile(50.0).unwrap();
        assert_eq!(p50, 3.0);
    }

    #[test]
    fn test_cache() {
        let mut cache = Cache::new(2);

        cache.put("key1", "value1");
        cache.put("key2", "value2");

        assert_eq!(cache.get(&"key1"), Some("value1"));
        assert_eq!(cache.get(&"key2"), Some("value2"));

        // Adding third item should evict least recently used
        cache.put("key3", "value3");
        assert_eq!(cache.size(), 2);
    }
}
