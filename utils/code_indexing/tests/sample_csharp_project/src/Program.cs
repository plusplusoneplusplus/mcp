using System;
using System.Collections.Generic;
using System.Linq;
using Geometry.Shapes;
using Utils.Math;

namespace SampleApp
{
    /// <summary>
    /// Main application entry point demonstrating various C# constructs
    /// </summary>
    public class Program
    {
        private static readonly Logger logger = new Logger();

        public static void Main(string[] args)
        {
            Console.WriteLine("C# Sample Application");

            // Test geometry shapes
            var shapes = new List<IShape>
            {
                new Rectangle(5.0, 3.0),
                new Circle(2.5),
                new Triangle(3.0, 4.0, 5.0)
            };

            var calculator = new AreaCalculator();
            foreach (var shape in shapes)
            {
                double area = calculator.CalculateArea(shape);
                logger.Log($"Shape: {shape.GetType().Name}, Area: {area:F2}");
            }

            // Test math utilities
            var mathUtils = new MathUtils();
            var vector1 = new Vector2D(3.0, 4.0);
            var vector2 = new Vector2D(1.0, 2.0);
            var result = mathUtils.AddVectors(vector1, vector2);

            Console.WriteLine($"Vector addition result: ({result.X}, {result.Y})");
        }
    }

    /// <summary>
    /// Simple logging utility
    /// </summary>
    public class Logger
    {
        private readonly string _prefix;

        public Logger(string prefix = "LOG")
        {
            _prefix = prefix;
        }

        public void Log(string message)
        {
            Console.WriteLine($"[{_prefix}] {DateTime.Now:HH:mm:ss} - {message}");
        }

        public void LogError(string error)
        {
            Console.WriteLine($"[ERROR] {DateTime.Now:HH:mm:ss} - {error}");
        }
    }
}
