/*!
 * Geometry module with shapes and mathematical operations.
 */

use serde::{Deserialize, Serialize};
use std::f64::consts::PI;

/// 2D Point structure
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Point2D {
    pub x: f64,
    pub y: f64,
}

impl Point2D {
    pub fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }

    pub fn origin() -> Self {
        Self { x: 0.0, y: 0.0 }
    }

    pub fn distance_to(&self, other: &Point2D) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx * dx + dy * dy).sqrt()
    }

    pub fn translate(&mut self, dx: f64, dy: f64) {
        self.x += dx;
        self.y += dy;
    }
}

impl std::ops::Add for Point2D {
    type Output = Point2D;

    fn add(self, rhs: Self) -> Self::Output {
        Point2D::new(self.x + rhs.x, self.y + rhs.y)
    }
}

impl std::ops::Sub for Point2D {
    type Output = Point2D;

    fn sub(self, rhs: Self) -> Self::Output {
        Point2D::new(self.x - rhs.x, self.y - rhs.y)
    }
}

/// Generic vector structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vector2D<T> {
    pub x: T,
    pub y: T,
}

impl<T> Vector2D<T> {
    pub fn new(x: T, y: T) -> Self {
        Self { x, y }
    }
}

impl<T> Vector2D<T>
where
    T: Copy + std::ops::Add<Output = T> + std::ops::Sub<Output = T> + std::ops::Mul<Output = T>,
{
    pub fn dot(&self, other: &Vector2D<T>) -> T {
        self.x * other.x + self.y * other.y
    }

    pub fn add(&self, other: &Vector2D<T>) -> Vector2D<T> {
        Vector2D::new(self.x + other.x, self.y + other.y)
    }
}

/// Shape trait defining common operations
pub trait Shape {
    fn area(&self) -> f64;
    fn perimeter(&self) -> f64;
    fn center(&self) -> Point2D;
    fn translate(&mut self, dx: f64, dy: f64);
    fn contains_point(&self, point: &Point2D) -> bool;
}

/// Drawable trait for rendering shapes
pub trait Drawable {
    fn draw(&self) -> String;
    fn bounding_box(&self) -> BoundingBox;
}

/// Rectangle structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rectangle {
    pub top_left: Point2D,
    pub width: f64,
    pub height: f64,
}

impl Rectangle {
    pub fn new(x: f64, y: f64, width: f64, height: f64) -> Self {
        Self {
            top_left: Point2D::new(x, y),
            width,
            height,
        }
    }

    pub fn square(x: f64, y: f64, size: f64) -> Self {
        Self::new(x, y, size, size)
    }

    pub fn is_square(&self) -> bool {
        (self.width - self.height).abs() < f64::EPSILON
    }

    pub fn resize(&mut self, new_width: f64, new_height: f64) {
        self.width = new_width.max(0.0);
        self.height = new_height.max(0.0);
    }
}

impl Shape for Rectangle {
    fn area(&self) -> f64 {
        self.width * self.height
    }

    fn perimeter(&self) -> f64 {
        2.0 * (self.width + self.height)
    }

    fn center(&self) -> Point2D {
        Point2D::new(
            self.top_left.x + self.width / 2.0,
            self.top_left.y + self.height / 2.0,
        )
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.top_left.translate(dx, dy);
    }

    fn contains_point(&self, point: &Point2D) -> bool {
        point.x >= self.top_left.x
            && point.x <= self.top_left.x + self.width
            && point.y >= self.top_left.y
            && point.y <= self.top_left.y + self.height
    }
}

impl Drawable for Rectangle {
    fn draw(&self) -> String {
        format!(
            "Rectangle at ({}, {}) with width {} and height {}",
            self.top_left.x, self.top_left.y, self.width, self.height
        )
    }

    fn bounding_box(&self) -> BoundingBox {
        BoundingBox {
            min: self.top_left,
            max: Point2D::new(self.top_left.x + self.width, self.top_left.y + self.height),
        }
    }
}

/// Circle structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Circle {
    pub center: Point2D,
    pub radius: f64,
}

impl Circle {
    pub fn new(x: f64, y: f64, radius: f64) -> Self {
        Self {
            center: Point2D::new(x, y),
            radius: radius.max(0.0),
        }
    }

    pub fn from_center(center: Point2D, radius: f64) -> Self {
        Self {
            center,
            radius: radius.max(0.0),
        }
    }

    pub fn diameter(&self) -> f64 {
        2.0 * self.radius
    }

    pub fn circumference(&self) -> f64 {
        2.0 * PI * self.radius
    }

    pub fn set_radius(&mut self, new_radius: f64) {
        self.radius = new_radius.max(0.0);
    }
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        PI * self.radius * self.radius
    }

    fn perimeter(&self) -> f64 {
        self.circumference()
    }

    fn center(&self) -> Point2D {
        self.center
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.center.translate(dx, dy);
    }

    fn contains_point(&self, point: &Point2D) -> bool {
        self.center.distance_to(point) <= self.radius
    }
}

impl Drawable for Circle {
    fn draw(&self) -> String {
        format!(
            "Circle at ({}, {}) with radius {}",
            self.center.x, self.center.y, self.radius
        )
    }

    fn bounding_box(&self) -> BoundingBox {
        BoundingBox {
            min: Point2D::new(self.center.x - self.radius, self.center.y - self.radius),
            max: Point2D::new(self.center.x + self.radius, self.center.y + self.radius),
        }
    }
}

/// Triangle structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Triangle {
    pub vertices: [Point2D; 3],
}

impl Triangle {
    pub fn new(p1: Point2D, p2: Point2D, p3: Point2D) -> Self {
        Self {
            vertices: [p1, p2, p3],
        }
    }

    pub fn is_valid(&self) -> bool {
        // Check if points are not collinear
        let [a, b, c] = self.vertices;
        let area = ((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)).abs();
        area > f64::EPSILON
    }

    pub fn side_lengths(&self) -> [f64; 3] {
        let [a, b, c] = self.vertices;
        [a.distance_to(&b), b.distance_to(&c), c.distance_to(&a)]
    }
}

impl Shape for Triangle {
    fn area(&self) -> f64 {
        let [a, b, c] = self.vertices;
        0.5 * ((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)).abs()
    }

    fn perimeter(&self) -> f64 {
        self.side_lengths().iter().sum()
    }

    fn center(&self) -> Point2D {
        let [a, b, c] = self.vertices;
        Point2D::new((a.x + b.x + c.x) / 3.0, (a.y + b.y + c.y) / 3.0)
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        for vertex in &mut self.vertices {
            vertex.translate(dx, dy);
        }
    }

    fn contains_point(&self, point: &Point2D) -> bool {
        // Barycentric coordinate method
        let [a, b, c] = self.vertices;
        let denominator = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y);

        if denominator.abs() < f64::EPSILON {
            return false;
        }

        let alpha = ((b.y - c.y) * (point.x - c.x) + (c.x - b.x) * (point.y - c.y)) / denominator;
        let beta = ((c.y - a.y) * (point.x - c.x) + (a.x - c.x) * (point.y - c.y)) / denominator;
        let gamma = 1.0 - alpha - beta;

        alpha >= 0.0 && beta >= 0.0 && gamma >= 0.0
    }
}

/// Bounding box structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundingBox {
    pub min: Point2D,
    pub max: Point2D,
}

impl BoundingBox {
    pub fn new(min: Point2D, max: Point2D) -> Self {
        Self { min, max }
    }

    pub fn width(&self) -> f64 {
        self.max.x - self.min.x
    }

    pub fn height(&self) -> f64 {
        self.max.y - self.min.y
    }

    pub fn area(&self) -> f64 {
        self.width() * self.height()
    }

    pub fn contains(&self, point: &Point2D) -> bool {
        point.x >= self.min.x
            && point.x <= self.max.x
            && point.y >= self.min.y
            && point.y <= self.max.y
    }

    pub fn intersects(&self, other: &BoundingBox) -> bool {
        !(self.max.x < other.min.x
            || other.max.x < self.min.x
            || self.max.y < other.min.y
            || other.max.y < self.min.y)
    }
}

/// Shape collection for managing multiple shapes
pub struct ShapeCollection {
    shapes: Vec<Box<dyn Shape>>,
    name: String,
}

impl ShapeCollection {
    pub fn new(name: String) -> Self {
        Self {
            shapes: Vec::new(),
            name,
        }
    }

    pub fn add_shape(&mut self, shape: Box<dyn Shape>) {
        self.shapes.push(shape);
    }

    pub fn total_area(&self) -> f64 {
        self.shapes.iter().map(|s| s.area()).sum()
    }

    pub fn total_perimeter(&self) -> f64 {
        self.shapes.iter().map(|s| s.perimeter()).sum()
    }

    pub fn count(&self) -> usize {
        self.shapes.len()
    }

    pub fn clear(&mut self) {
        self.shapes.clear();
    }

    pub fn name(&self) -> &str {
        &self.name
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_point2d_operations() {
        let p1 = Point2D::new(3.0, 4.0);
        let p2 = Point2D::new(0.0, 0.0);

        assert_eq!(p1.distance_to(&p2), 5.0);

        let p3 = p1 + p2;
        assert_eq!(p3.x, 3.0);
        assert_eq!(p3.y, 4.0);
    }

    #[test]
    fn test_rectangle_shape() {
        let rect = Rectangle::new(0.0, 0.0, 4.0, 3.0);

        assert_eq!(rect.area(), 12.0);
        assert_eq!(rect.perimeter(), 14.0);

        let center = rect.center();
        assert_eq!(center.x, 2.0);
        assert_eq!(center.y, 1.5);

        assert!(rect.contains_point(&Point2D::new(2.0, 1.0)));
        assert!(!rect.contains_point(&Point2D::new(5.0, 1.0)));
    }

    #[test]
    fn test_circle_shape() {
        let circle = Circle::new(0.0, 0.0, 5.0);

        assert!((circle.area() - (PI * 25.0)).abs() < f64::EPSILON);
        assert!((circle.perimeter() - (2.0 * PI * 5.0)).abs() < f64::EPSILON);

        assert!(circle.contains_point(&Point2D::new(3.0, 4.0)));
        assert!(!circle.contains_point(&Point2D::new(6.0, 0.0)));
    }
}
