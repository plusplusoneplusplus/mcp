"""
Geometry module with shapes and area calculations.

This module demonstrates:
- Abstract base classes
- Protocol definitions
- Property decorators
- Class inheritance
- Type hints
"""

import math
from abc import ABC, abstractmethod
from typing import Protocol, List, Union, Optional
from dataclasses import dataclass


class Drawable(Protocol):
    """Protocol for objects that can be drawn."""

    def draw(self) -> str:
        """Draw the object and return its string representation."""
        ...

    def get_color(self) -> str:
        """Get the color of the object."""
        ...


class Shape(ABC):
    """Abstract base class for all geometric shapes."""

    def __init__(self, name: str, color: str = "black"):
        self._name = name
        self._color = color
        self._id = id(self)

    @property
    def name(self) -> str:
        """Get the shape name."""
        return self._name

    @property
    def color(self) -> str:
        """Get the shape color."""
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        """Set the shape color."""
        self._color = value

    @property
    def id(self) -> int:
        """Get the unique shape ID."""
        return self._id

    @abstractmethod
    def area(self) -> float:
        """Calculate the area of the shape."""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        """Calculate the perimeter of the shape."""
        pass

    def draw(self) -> str:
        """Draw the shape."""
        return f"Drawing {self._color} {self._name}"

    def get_color(self) -> str:
        """Get the color for Drawable protocol."""
        return self._color

    def __str__(self) -> str:
        return f"{self._name}(area={self.area():.2f}, perimeter={self.perimeter():.2f})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._name}', color='{self._color}')"


class Rectangle(Shape):
    """Rectangle implementation with width and height."""

    def __init__(self, width: float, height: float, color: str = "black"):
        super().__init__("Rectangle", color)
        self._width = width
        self._height = height

    @property
    def width(self) -> float:
        """Get the rectangle width."""
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        """Set the rectangle width."""
        if value <= 0:
            raise ValueError("Width must be positive")
        self._width = value

    @property
    def height(self) -> float:
        """Get the rectangle height."""
        return self._height

    @height.setter
    def height(self, value: float) -> None:
        """Set the rectangle height."""
        if value <= 0:
            raise ValueError("Height must be positive")
        self._height = value

    @property
    def is_square(self) -> bool:
        """Check if the rectangle is a square."""
        return abs(self._width - self._height) < 1e-10

    def area(self) -> float:
        """Calculate the rectangle area."""
        return self._width * self._height

    def perimeter(self) -> float:
        """Calculate the rectangle perimeter."""
        return 2 * (self._width + self._height)

    def resize(self, width: float, height: float) -> None:
        """Resize the rectangle."""
        self.width = width
        self.height = height

    def scale(self, factor: float) -> "Rectangle":
        """Create a scaled copy of the rectangle."""
        return Rectangle(self._width * factor, self._height * factor, self._color)


class Circle(Shape):
    """Circle implementation with radius."""

    def __init__(self, radius: float, color: str = "black"):
        super().__init__("Circle", color)
        self._radius = radius

    @property
    def radius(self) -> float:
        """Get the circle radius."""
        return self._radius

    @radius.setter
    def radius(self, value: float) -> None:
        """Set the circle radius."""
        if value <= 0:
            raise ValueError("Radius must be positive")
        self._radius = value

    @property
    def diameter(self) -> float:
        """Get the circle diameter."""
        return 2 * self._radius

    def area(self) -> float:
        """Calculate the circle area."""
        return math.pi * self._radius**2

    def perimeter(self) -> float:
        """Calculate the circle perimeter (circumference)."""
        return 2 * math.pi * self._radius

    def scale(self, factor: float) -> "Circle":
        """Create a scaled copy of the circle."""
        return Circle(self._radius * factor, self._color)


class Triangle(Shape):
    """Triangle implementation with three sides."""

    def __init__(
        self, side_a: float, side_b: float, side_c: float, color: str = "black"
    ):
        if not self._is_valid_triangle(side_a, side_b, side_c):
            raise ValueError("Invalid triangle sides")

        super().__init__("Triangle", color)
        self._side_a = side_a
        self._side_b = side_b
        self._side_c = side_c

    @property
    def side_a(self) -> float:
        """Get side A length."""
        return self._side_a

    @property
    def side_b(self) -> float:
        """Get side B length."""
        return self._side_b

    @property
    def side_c(self) -> float:
        """Get side C length."""
        return self._side_c

    @property
    def is_equilateral(self) -> bool:
        """Check if the triangle is equilateral."""
        return (
            abs(self._side_a - self._side_b) < 1e-10
            and abs(self._side_b - self._side_c) < 1e-10
        )

    @property
    def is_isosceles(self) -> bool:
        """Check if the triangle is isosceles."""
        return (
            abs(self._side_a - self._side_b) < 1e-10
            or abs(self._side_b - self._side_c) < 1e-10
            or abs(self._side_a - self._side_c) < 1e-10
        )

    def area(self) -> float:
        """Calculate the triangle area using Heron's formula."""
        s = self.perimeter() / 2
        return math.sqrt(
            s * (s - self._side_a) * (s - self._side_b) * (s - self._side_c)
        )

    def perimeter(self) -> float:
        """Calculate the triangle perimeter."""
        return self._side_a + self._side_b + self._side_c

    @staticmethod
    def _is_valid_triangle(a: float, b: float, c: float) -> bool:
        """Check if three sides can form a valid triangle."""
        return a + b > c and b + c > a and a + c > b


@dataclass
class Point:
    """2D point with x and y coordinates."""

    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        """Calculate distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def translate(self, dx: float, dy: float) -> "Point":
        """Create a translated copy of the point."""
        return Point(self.x + dx, self.y + dy)


class AreaCalculator:
    """Utility class for calculating areas of different shapes."""

    def __init__(self):
        self._calculation_count = 0

    @property
    def calculation_count(self) -> int:
        """Get the number of calculations performed."""
        return self._calculation_count

    def calculate_area(self, shape: Shape) -> float:
        """Calculate the area of a single shape."""
        self._calculation_count += 1
        return shape.area()

    def calculate_total_area(self, shapes: List[Shape]) -> float:
        """Calculate the total area of multiple shapes."""
        return sum(self.calculate_area(shape) for shape in shapes)

    def find_largest_shape(self, shapes: List[Shape]) -> Optional[Shape]:
        """Find the shape with the largest area."""
        if not shapes:
            return None
        return max(shapes, key=lambda s: s.area())

    def find_smallest_shape(self, shapes: List[Shape]) -> Optional[Shape]:
        """Find the shape with the smallest area."""
        if not shapes:
            return None
        return min(shapes, key=lambda s: s.area())

    def group_by_type(self, shapes: List[Shape]) -> dict[str, List[Shape]]:
        """Group shapes by their type."""
        groups: dict[str, List[Shape]] = {}
        for shape in shapes:
            shape_type = type(shape).__name__
            if shape_type not in groups:
                groups[shape_type] = []
            groups[shape_type].append(shape)
        return groups

    def reset_counter(self) -> None:
        """Reset the calculation counter."""
        self._calculation_count = 0


class ShapeFactory:
    """Factory class for creating shapes."""

    @staticmethod
    def create_rectangle(
        width: float, height: float, color: str = "black"
    ) -> Rectangle:
        """Create a rectangle."""
        return Rectangle(width, height, color)

    @staticmethod
    def create_square(side: float, color: str = "black") -> Rectangle:
        """Create a square (special case of rectangle)."""
        return Rectangle(side, side, color)

    @staticmethod
    def create_circle(radius: float, color: str = "black") -> Circle:
        """Create a circle."""
        return Circle(radius, color)

    @staticmethod
    def create_triangle(
        side_a: float, side_b: float, side_c: float, color: str = "black"
    ) -> Triangle:
        """Create a triangle."""
        return Triangle(side_a, side_b, side_c, color)

    @staticmethod
    def create_equilateral_triangle(side: float, color: str = "black") -> Triangle:
        """Create an equilateral triangle."""
        return Triangle(side, side, side, color)

    @classmethod
    def create_random_shape(cls, shape_type: str = "random") -> Shape:
        """Create a random shape."""
        import random

        if shape_type == "random":
            shape_type = random.choice(["rectangle", "circle", "triangle"])

        color = random.choice(["red", "blue", "green", "yellow", "purple"])

        if shape_type == "rectangle":
            return cls.create_rectangle(
                random.uniform(1, 10), random.uniform(1, 10), color
            )
        elif shape_type == "circle":
            return cls.create_circle(random.uniform(1, 5), color)
        elif shape_type == "triangle":
            # Generate valid triangle sides
            a = random.uniform(3, 10)
            b = random.uniform(3, 10)
            c = random.uniform(abs(a - b) + 0.1, a + b - 0.1)
            return cls.create_triangle(a, b, c, color)
        else:
            raise ValueError(f"Unknown shape type: {shape_type}")


# Module-level functions
def calculate_total_area(shapes: List[Shape]) -> float:
    """Module-level function to calculate total area."""
    calculator = AreaCalculator()
    return calculator.calculate_total_area(shapes)


def create_shape_from_dict(shape_data: dict) -> Shape:
    """Create a shape from a dictionary specification."""
    factory = ShapeFactory()
    shape_type = shape_data.get("type", "").lower()
    color = shape_data.get("color", "black")

    if shape_type == "rectangle":
        return factory.create_rectangle(
            shape_data["width"], shape_data["height"], color
        )
    elif shape_type == "circle":
        return factory.create_circle(shape_data["radius"], color)
    elif shape_type == "triangle":
        return factory.create_triangle(
            shape_data["side_a"], shape_data["side_b"], shape_data["side_c"], color
        )
    else:
        raise ValueError(f"Unknown shape type: {shape_type}")
