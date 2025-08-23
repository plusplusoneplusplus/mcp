using System;
using System.Collections.Generic;

namespace Utils.Math
{
    /// <summary>
    /// 2D Vector structure with mathematical operations
    /// </summary>
    public struct Vector2D
    {
        public double X { get; }
        public double Y { get; }

        public Vector2D(double x, double y)
        {
            X = x;
            Y = y;
        }

        public double Magnitude => Math.Sqrt(X * X + Y * Y);
        public double MagnitudeSquared => X * X + Y * Y;

        public Vector2D Normalized
        {
            get
            {
                double mag = Magnitude;
                return mag > 0 ? new Vector2D(X / mag, Y / mag) : new Vector2D(0, 0);
            }
        }

        public static Vector2D operator +(Vector2D a, Vector2D b)
        {
            return new Vector2D(a.X + b.X, a.Y + b.Y);
        }

        public static Vector2D operator -(Vector2D a, Vector2D b)
        {
            return new Vector2D(a.X - b.X, a.Y - b.Y);
        }

        public static Vector2D operator *(Vector2D v, double scalar)
        {
            return new Vector2D(v.X * scalar, v.Y * scalar);
        }

        public static double Dot(Vector2D a, Vector2D b)
        {
            return a.X * b.X + a.Y * b.Y;
        }

        public override string ToString()
        {
            return $"({X:F2}, {Y:F2})";
        }
    }

    /// <summary>
    /// Generic mathematical statistics calculator
    /// </summary>
    public class StatisticsCalculator<T> where T : IComparable<T>
    {
        private readonly List<T> _values;

        public StatisticsCalculator()
        {
            _values = new List<T>();
        }

        public void AddValue(T value)
        {
            _values.Add(value);
        }

        public void AddValues(IEnumerable<T> values)
        {
            _values.AddRange(values);
        }

        public int Count => _values.Count;

        public T Min => _values.Count > 0 ? _values.Min() : default(T);
        public T Max => _values.Count > 0 ? _values.Max() : default(T);

        public void Clear()
        {
            _values.Clear();
        }

        public T[] ToArray()
        {
            return _values.ToArray();
        }
    }

    /// <summary>
    /// Mathematical utility functions and constants
    /// </summary>
    public static class MathConstants
    {
        public const double PI = Math.PI;
        public const double E = Math.E;
        public const double GOLDEN_RATIO = 1.618033988749895;
        public const double SQRT_2 = 1.4142135623730951;
        public const double SQRT_3 = 1.7320508075688772;

        public static double DegreesToRadians(double degrees)
        {
            return degrees * PI / 180.0;
        }

        public static double RadiansToDegrees(double radians)
        {
            return radians * 180.0 / PI;
        }
    }

    /// <summary>
    /// Collection of mathematical utility methods
    /// </summary>
    public class MathUtils
    {
        private static readonly Random _random = new Random();

        public Vector2D AddVectors(Vector2D a, Vector2D b)
        {
            return a + b;
        }

        public Vector2D SubtractVectors(Vector2D a, Vector2D b)
        {
            return a - b;
        }

        public double CalculateDistance(Vector2D point1, Vector2D point2)
        {
            Vector2D diff = point2 - point1;
            return diff.Magnitude;
        }

        public double CalculateAngle(Vector2D vector)
        {
            return Math.Atan2(vector.Y, vector.X);
        }

        public int Factorial(int n)
        {
            if (n < 0) throw new ArgumentException("Factorial is not defined for negative numbers");
            if (n <= 1) return 1;

            int result = 1;
            for (int i = 2; i <= n; i++)
            {
                result *= i;
            }
            return result;
        }

        public long Fibonacci(int n)
        {
            if (n < 0) throw new ArgumentException("Fibonacci is not defined for negative numbers");
            if (n <= 1) return n;

            long a = 0, b = 1;
            for (int i = 2; i <= n; i++)
            {
                long temp = a + b;
                a = b;
                b = temp;
            }
            return b;
        }

        public bool IsPrime(int number)
        {
            if (number <= 1) return false;
            if (number <= 3) return true;
            if (number % 2 == 0 || number % 3 == 0) return false;

            for (int i = 5; i * i <= number; i += 6)
            {
                if (number % i == 0 || number % (i + 2) == 0)
                    return false;
            }
            return true;
        }

        public double GenerateRandomDouble(double min = 0.0, double max = 1.0)
        {
            return _random.NextDouble() * (max - min) + min;
        }

        public int GenerateRandomInt(int min, int max)
        {
            return _random.Next(min, max + 1);
        }
    }

    /// <summary>
    /// Exception for mathematical operation errors
    /// </summary>
    public class MathOperationException : Exception
    {
        public MathOperationException() : base() { }

        public MathOperationException(string message) : base(message) { }

        public MathOperationException(string message, Exception innerException) : base(message, innerException) { }
    }
}
