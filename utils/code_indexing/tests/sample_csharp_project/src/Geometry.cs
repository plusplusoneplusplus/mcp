using System;

namespace Geometry.Shapes
{
    /// <summary>
    /// Base interface for all geometric shapes
    /// </summary>
    public interface IShape
    {
        double Area { get; }
        double Perimeter { get; }
        string Name { get; }
        void Draw();
    }

    /// <summary>
    /// Abstract base class for shapes with common properties
    /// </summary>
    public abstract class Shape : IShape
    {
        protected string _name;

        protected Shape(string name)
        {
            _name = name;
        }

        public abstract double Area { get; }
        public abstract double Perimeter { get; }
        public virtual string Name => _name;

        public virtual void Draw()
        {
            Console.WriteLine($"Drawing {Name}");
        }

        public override string ToString()
        {
            return $"{Name}: Area={Area:F2}, Perimeter={Perimeter:F2}";
        }
    }

    /// <summary>
    /// Rectangle implementation with width and height
    /// </summary>
    public class Rectangle : Shape
    {
        public double Width { get; private set; }
        public double Height { get; private set; }

        public Rectangle(double width, double height) : base("Rectangle")
        {
            Width = width;
            Height = height;
        }

        public override double Area => Width * Height;
        public override double Perimeter => 2 * (Width + Height);

        public bool IsSquare => Math.Abs(Width - Height) < 1e-10;

        public void Resize(double newWidth, double newHeight)
        {
            Width = newWidth;
            Height = newHeight;
        }
    }

    /// <summary>
    /// Circle implementation with radius
    /// </summary>
    public class Circle : Shape
    {
        public double Radius { get; private set; }

        public Circle(double radius) : base("Circle")
        {
            Radius = radius;
        }

        public override double Area => Math.PI * Radius * Radius;
        public override double Perimeter => 2 * Math.PI * Radius;

        public double Diameter => 2 * Radius;

        public void SetRadius(double newRadius)
        {
            if (newRadius <= 0)
                throw new ArgumentException("Radius must be positive");
            Radius = newRadius;
        }
    }

    /// <summary>
    /// Triangle implementation with three sides
    /// </summary>
    public class Triangle : Shape
    {
        public double SideA { get; private set; }
        public double SideB { get; private set; }
        public double SideC { get; private set; }

        public Triangle(double sideA, double sideB, double sideC) : base("Triangle")
        {
            if (!IsValidTriangle(sideA, sideB, sideC))
                throw new ArgumentException("Invalid triangle sides");

            SideA = sideA;
            SideB = sideB;
            SideC = sideC;
        }

        public override double Area
        {
            get
            {
                // Using Heron's formula
                double s = Perimeter / 2;
                return Math.Sqrt(s * (s - SideA) * (s - SideB) * (s - SideC));
            }
        }

        public override double Perimeter => SideA + SideB + SideC;

        public bool IsEquilateral => Math.Abs(SideA - SideB) < 1e-10 && Math.Abs(SideB - SideC) < 1e-10;
        public bool IsIsosceles => Math.Abs(SideA - SideB) < 1e-10 || Math.Abs(SideB - SideC) < 1e-10 || Math.Abs(SideA - SideC) < 1e-10;

        private static bool IsValidTriangle(double a, double b, double c)
        {
            return a + b > c && b + c > a && a + c > b;
        }
    }

    /// <summary>
    /// Utility class for calculating areas of different shapes
    /// </summary>
    public class AreaCalculator
    {
        public double CalculateArea(IShape shape)
        {
            return shape.Area;
        }

        public double CalculateTotalArea(params IShape[] shapes)
        {
            return shapes.Sum(s => s.Area);
        }

        public IShape FindLargestShape(IEnumerable<IShape> shapes)
        {
            return shapes.OrderByDescending(s => s.Area).FirstOrDefault();
        }
    }
}
