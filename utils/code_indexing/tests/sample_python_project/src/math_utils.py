"""
Mathematical utilities and data structures.

This module demonstrates:
- Data classes
- Type hints and generics
- Properties and methods
- Static and class methods
- Custom exceptions
"""

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import TypeVar, Generic, List, Optional, Union, Callable, Iterator
from functools import wraps, lru_cache
from enum import Enum, auto


T = TypeVar("T", bound=Union[int, float])
Number = Union[int, float]


@dataclass(frozen=True)
class Vector2D:
    """Immutable 2D vector with mathematical operations."""

    x: float
    y: float

    @property
    def magnitude(self) -> float:
        """Calculate the magnitude of the vector."""
        return math.sqrt(self.x**2 + self.y**2)

    @property
    def magnitude_squared(self) -> float:
        """Calculate the squared magnitude (faster than magnitude)."""
        return self.x**2 + self.y**2

    @property
    def normalized(self) -> "Vector2D":
        """Get a normalized copy of the vector."""
        mag = self.magnitude
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)

    @property
    def angle(self) -> float:
        """Get the angle of the vector in radians."""
        return math.atan2(self.y, self.x)

    def __add__(self, other: "Vector2D") -> "Vector2D":
        """Add two vectors."""
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2D") -> "Vector2D":
        """Subtract two vectors."""
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: Number) -> "Vector2D":
        """Multiply vector by scalar."""
        return Vector2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: Number) -> "Vector2D":
        """Right multiply vector by scalar."""
        return self.__mul__(scalar)

    def __truediv__(self, scalar: Number) -> "Vector2D":
        """Divide vector by scalar."""
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide vector by zero")
        return Vector2D(self.x / scalar, self.y / scalar)

    def dot(self, other: "Vector2D") -> float:
        """Calculate dot product with another vector."""
        return self.x * other.x + self.y * other.y

    def cross(self, other: "Vector2D") -> float:
        """Calculate 2D cross product (returns scalar)."""
        return self.x * other.y - self.y * other.x

    def distance_to(self, other: "Vector2D") -> float:
        """Calculate distance to another vector."""
        return (self - other).magnitude

    def rotate(self, angle: float) -> "Vector2D":
        """Rotate vector by given angle in radians."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vector2D(
            self.x * cos_a - self.y * sin_a, self.x * sin_a + self.y * cos_a
        )

    @classmethod
    def from_angle(cls, angle: float, magnitude: float = 1.0) -> "Vector2D":
        """Create vector from angle and magnitude."""
        return cls(magnitude * math.cos(angle), magnitude * math.sin(angle))

    @classmethod
    def zero(cls) -> "Vector2D":
        """Create zero vector."""
        return cls(0, 0)

    @classmethod
    def up(cls) -> "Vector2D":
        """Create up vector."""
        return cls(0, 1)

    @classmethod
    def right(cls) -> "Vector2D":
        """Create right vector."""
        return cls(1, 0)


class StatisticsCalculator(Generic[T]):
    """Generic statistics calculator for numeric types."""

    def __init__(self) -> None:
        self._values: List[T] = []
        self._sorted_cache: Optional[List[T]] = None
        self._stats_cache: dict = {}

    def add_value(self, value: T) -> None:
        """Add a single value."""
        self._values.append(value)
        self._invalidate_cache()

    def add_values(self, values: List[T]) -> None:
        """Add multiple values."""
        self._values.extend(values)
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate cached calculations."""
        self._sorted_cache = None
        self._stats_cache.clear()

    @property
    def count(self) -> int:
        """Get the number of values."""
        return len(self._values)

    @property
    def is_empty(self) -> bool:
        """Check if calculator is empty."""
        return len(self._values) == 0

    def clear(self) -> None:
        """Clear all values."""
        self._values.clear()
        self._invalidate_cache()

    def get_values(self) -> List[T]:
        """Get a copy of all values."""
        return self._values.copy()

    def _get_sorted(self) -> List[T]:
        """Get sorted values (cached)."""
        if self._sorted_cache is None:
            self._sorted_cache = sorted(self._values)
        return self._sorted_cache

    def min(self) -> Optional[T]:
        """Get minimum value."""
        return min(self._values) if self._values else None

    def max(self) -> Optional[T]:
        """Get maximum value."""
        return max(self._values) if self._values else None

    def sum(self) -> T:
        """Get sum of values."""
        if not self._values:
            raise ValueError("Cannot calculate sum of empty dataset")
        return sum(self._values)

    def mean(self) -> float:
        """Calculate arithmetic mean."""
        if not self._values:
            raise ValueError("Cannot calculate mean of empty dataset")
        return statistics.mean(self._values)

    def median(self) -> float:
        """Calculate median."""
        if not self._values:
            raise ValueError("Cannot calculate median of empty dataset")
        return statistics.median(self._values)

    def mode(self) -> T:
        """Calculate mode."""
        if not self._values:
            raise ValueError("Cannot calculate mode of empty dataset")
        return statistics.mode(self._values)

    def variance(self) -> float:
        """Calculate variance."""
        if len(self._values) < 2:
            raise ValueError("Cannot calculate variance with less than 2 values")
        return statistics.variance(self._values)

    def std_dev(self) -> float:
        """Calculate standard deviation."""
        return math.sqrt(self.variance())

    def percentile(self, p: float) -> float:
        """Calculate percentile (0-100)."""
        if not self._values:
            raise ValueError("Cannot calculate percentile of empty dataset")
        if not 0 <= p <= 100:
            raise ValueError("Percentile must be between 0 and 100")

        sorted_values = self._get_sorted()
        k = (len(sorted_values) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return float(sorted_values[int(k)])

        d0 = sorted_values[int(f)] * (c - k)
        d1 = sorted_values[int(c)] * (k - f)
        return float(d0 + d1)

    def quartiles(self) -> tuple[float, float, float]:
        """Calculate Q1, Q2 (median), Q3."""
        return (self.percentile(25), self.percentile(50), self.percentile(75))


class OperationType(Enum):
    """Enumeration of mathematical operations."""

    ADDITION = auto()
    SUBTRACTION = auto()
    MULTIPLICATION = auto()
    DIVISION = auto()
    POWER = auto()
    ROOT = auto()
    LOGARITHM = auto()


@dataclass
class MathOperation:
    """Represents a mathematical operation with operands."""

    operation: OperationType
    operand1: Number
    operand2: Optional[Number] = None
    result: Optional[Number] = field(default=None, init=False)

    def execute(self) -> Number:
        """Execute the mathematical operation."""
        if self.operation == OperationType.ADDITION:
            self.result = self.operand1 + (self.operand2 or 0)
        elif self.operation == OperationType.SUBTRACTION:
            self.result = self.operand1 - (self.operand2 or 0)
        elif self.operation == OperationType.MULTIPLICATION:
            self.result = self.operand1 * (self.operand2 or 1)
        elif self.operation == OperationType.DIVISION:
            if self.operand2 == 0:
                raise ZeroDivisionError("Division by zero")
            self.result = self.operand1 / (self.operand2 or 1)
        elif self.operation == OperationType.POWER:
            self.result = self.operand1 ** (self.operand2 or 2)
        elif self.operation == OperationType.ROOT:
            if self.operand2 is None:
                self.result = math.sqrt(self.operand1)
            else:
                self.result = self.operand1 ** (1 / self.operand2)
        elif self.operation == OperationType.LOGARITHM:
            if self.operand2 is None:
                self.result = math.log(self.operand1)
            else:
                self.result = math.log(self.operand1, self.operand2)

        return self.result


class MathUtils:
    """Collection of mathematical utility functions."""

    def __init__(self):
        self._operation_history: List[MathOperation] = []
        self._random = random.Random()

    @property
    def operation_count(self) -> int:
        """Get number of operations performed."""
        return len(self._operation_history)

    def set_seed(self, seed: int) -> None:
        """Set random seed for reproducible results."""
        self._random.seed(seed)

    def add_vectors(self, v1: Vector2D, v2: Vector2D) -> Vector2D:
        """Add two vectors."""
        return v1 + v2

    def subtract_vectors(self, v1: Vector2D, v2: Vector2D) -> Vector2D:
        """Subtract two vectors."""
        return v1 - v2

    def calculate_distance(self, point1: Vector2D, point2: Vector2D) -> float:
        """Calculate distance between two points."""
        return point1.distance_to(point2)

    def calculate_angle_between(self, v1: Vector2D, v2: Vector2D) -> float:
        """Calculate angle between two vectors in radians."""
        dot_product = v1.dot(v2)
        magnitude_product = v1.magnitude * v2.magnitude

        if magnitude_product == 0:
            return 0.0

        cos_angle = dot_product / magnitude_product
        # Clamp to [-1, 1] to handle floating point errors
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.acos(cos_angle)

    @lru_cache(maxsize=128)
    def factorial(self, n: int) -> int:
        """Calculate factorial with caching."""
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers")
        if n <= 1:
            return 1
        return n * self.factorial(n - 1)

    @lru_cache(maxsize=128)
    def fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number with caching."""
        if n < 0:
            raise ValueError("Fibonacci is not defined for negative numbers")
        if n <= 1:
            return n
        return self.fibonacci(n - 1) + self.fibonacci(n - 2)

    def is_prime(self, number: int) -> bool:
        """Check if a number is prime."""
        if number <= 1:
            return False
        if number <= 3:
            return True
        if number % 2 == 0 or number % 3 == 0:
            return False

        i = 5
        while i * i <= number:
            if number % i == 0 or number % (i + 2) == 0:
                return False
            i += 6
        return True

    def generate_primes(self, limit: int) -> List[int]:
        """Generate all prime numbers up to limit using Sieve of Eratosthenes."""
        if limit < 2:
            return []

        sieve = [True] * (limit + 1)
        sieve[0] = sieve[1] = False

        for i in range(2, int(math.sqrt(limit)) + 1):
            if sieve[i]:
                for j in range(i * i, limit + 1, i):
                    sieve[j] = False

        return [i for i in range(2, limit + 1) if sieve[i]]

    def gcd(self, a: int, b: int) -> int:
        """Calculate greatest common divisor."""
        while b:
            a, b = b, a % b
        return abs(a)

    def lcm(self, a: int, b: int) -> int:
        """Calculate least common multiple."""
        return abs(a * b) // self.gcd(a, b) if a and b else 0

    def degrees_to_radians(self, degrees: float) -> float:
        """Convert degrees to radians."""
        return math.radians(degrees)

    def radians_to_degrees(self, radians: float) -> float:
        """Convert radians to degrees."""
        return math.degrees(radians)

    def clamp(self, value: Number, min_val: Number, max_val: Number) -> Number:
        """Clamp value between min and max."""
        return max(min_val, min(max_val, value))

    def lerp(self, start: Number, end: Number, t: float) -> Number:
        """Linear interpolation between start and end."""
        return start + t * (end - start)

    def generate_random_float(
        self, min_val: float = 0.0, max_val: float = 1.0
    ) -> float:
        """Generate random float in range."""
        return self._random.uniform(min_val, max_val)

    def generate_random_int(self, min_val: int, max_val: int) -> int:
        """Generate random integer in range."""
        return self._random.randint(min_val, max_val)

    def generate_random_vector(self, max_magnitude: float = 1.0) -> Vector2D:
        """Generate random 2D vector."""
        angle = self._random.uniform(0, 2 * math.pi)
        magnitude = self._random.uniform(0, max_magnitude)
        return Vector2D.from_angle(angle, magnitude)

    def clear_history(self) -> None:
        """Clear operation history."""
        self._operation_history.clear()

    def get_history(self) -> List[MathOperation]:
        """Get copy of operation history."""
        return self._operation_history.copy()


# Decorator functions
def validate_positive(func: Callable) -> Callable:
    """Decorator to validate that numeric arguments are positive."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        for arg in args[1:]:  # Skip 'self' argument
            if isinstance(arg, (int, float)) and arg <= 0:
                raise ValueError(f"Argument {arg} must be positive")
        return func(*args, **kwargs)

    return wrapper


def cache_result(func: Callable) -> Callable:
    """Simple caching decorator."""
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


# Module-level constants
PI = math.pi
E = math.e
GOLDEN_RATIO = (1 + math.sqrt(5)) / 2
EULER_GAMMA = 0.5772156649015329


# Module-level functions
def calculate_circle_area(radius: float) -> float:
    """Calculate area of a circle."""
    return PI * radius**2


def calculate_sphere_volume(radius: float) -> float:
    """Calculate volume of a sphere."""
    return (4 / 3) * PI * radius**3


def solve_quadratic(
    a: float, b: float, c: float
) -> tuple[Optional[float], Optional[float]]:
    """Solve quadratic equation ax² + bx + c = 0."""
    if a == 0:
        if b == 0:
            return (None, None)
        return (-c / b, None)

    discriminant = b**2 - 4 * a * c

    if discriminant < 0:
        return (None, None)  # No real solutions
    elif discriminant == 0:
        root = -b / (2 * a)
        return (root, None)  # One solution
    else:
        sqrt_discriminant = math.sqrt(discriminant)
        root1 = (-b + sqrt_discriminant) / (2 * a)
        root2 = (-b - sqrt_discriminant) / (2 * a)
        return (root1, root2)


class MathError(Exception):
    """Custom exception for mathematical operations."""

    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message)
        self.operation = operation


class DivisionByZeroError(MathError):
    """Exception for division by zero."""

    def __init__(self, dividend: Number):
        super().__init__(f"Cannot divide {dividend} by zero", "division")
        self.dividend = dividend


class InvalidInputError(MathError):
    """Exception for invalid mathematical input."""

    def __init__(self, value: Number, operation: str):
        super().__init__(f"Invalid input {value} for operation {operation}", operation)
        self.value = value
