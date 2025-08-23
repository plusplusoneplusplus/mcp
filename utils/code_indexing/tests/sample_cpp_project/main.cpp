#include "geometry/Shape.h"
#include "utils/MathUtils.h"
#include <iostream>
#include <vector>
#include <memory>

using namespace geometry;
using namespace utils;

/**
 * Demo application showing inheritance and polymorphism.
 */
class ShapeManager
{
public:
    ShapeManager() = default;
    ~ShapeManager() = default;

    void addShape(std::unique_ptr<Shape> shape)
    {
        shapes_.push_back(std::move(shape));
    }

    void drawAll() const
    {
        for (const auto &shape : shapes_)
        {
            shape->draw();
        }
    }

    double calculateTotalArea() const
    {
        double total = 0.0;
        for (const auto &shape : shapes_)
        {
            total += shape->area();
        }
        return total;
    }

    size_t getShapeCount() const { return shapes_.size(); }

private:
    std::vector<std::unique_ptr<Shape>> shapes_;
};

// Global utility functions
double calculateDistance(const Vec2d &point1, const Vec2d &point2)
{
    Vec2d diff = point2 - point1;
    return diff.magnitude();
}

void demonstrateVectorOperations()
{
    std::cout << "\n=== Vector Operations Demo ===\n";

    Vec2d v1(3.0, 4.0);
    Vec2d v2(1.0, 2.0);

    std::cout << "Vector 1: (" << v1.x << ", " << v1.y << ")\n";
    std::cout << "Vector 2: (" << v2.x << ", " << v2.y << ")\n";
    std::cout << "Magnitude of v1: " << v1.magnitude() << "\n";
    std::cout << "Distance between vectors: " << calculateDistance(v1, v2) << "\n";

    Vec2d sum = v1 + v2;
    std::cout << "Sum: (" << sum.x << ", " << sum.y << ")\n";

    double dot_product = v1.dot(v2);
    std::cout << "Dot product: " << dot_product << "\n";
}

void demonstrateStatistics()
{
    std::cout << "\n=== Statistics Demo ===\n";

    StatisticsCalculator calc;
    std::vector<double> data = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0};

    calc.addValues(data);

    Statistics stats = calc.calculate();
    std::cout << "Data count: " << stats.count << "\n";
    std::cout << "Mean: " << stats.mean << "\n";
    std::cout << "Median: " << stats.median << "\n";
    std::cout << "Standard deviation: " << stats.standardDeviation << "\n";
    std::cout << "Range: [" << stats.minimum << ", " << stats.maximum << "]\n";

    double percentile_75 = calc.getPercentile(75.0);
    std::cout << "75th percentile: " << percentile_75 << "\n";
}

int main()
{
    std::cout << "=== Shape Geometry Demo ===\n";

    ShapeManager manager;

    // Create various shapes
    auto rect = std::make_unique<Rectangle>(0, 0, 5, 3);
    auto circle = std::make_unique<Circle>(10, 10, 2.5);
    auto square = std::make_unique<Rectangle>(20, 20, 4, 4);

    std::cout << "Created shapes:\n";
    std::cout << "Rectangle area: " << rect->area() << "\n";
    std::cout << "Circle area: " << circle->area() << "\n";
    std::cout << "Square area: " << square->area() << "\n";

    // Add to manager
    manager.addShape(std::move(rect));
    manager.addShape(std::move(circle));
    manager.addShape(std::move(square));

    std::cout << "\nTotal shapes: " << manager.getShapeCount() << "\n";
    std::cout << "Total area: " << manager.calculateTotalArea() << "\n";

    std::cout << "\nDrawing all shapes:\n";
    manager.drawAll();

    // Demonstrate math utilities
    std::cout << "\n=== Math Utilities Demo ===\n";
    double value = 15.7;
    double clamped = MathUtils::clamp(value, 0.0, 10.0);
    std::cout << "Clamping " << value << " to [0, 10]: " << clamped << "\n";

    double lerped = MathUtils::lerp(0.0, 100.0, 0.25);
    std::cout << "Linear interpolation between 0 and 100 at t=0.25: " << lerped << "\n";

    bool near_zero = MathUtils::isNearZero(0.0000001);
    std::cout << "Is 0.0000001 near zero? " << (near_zero ? "Yes" : "No") << "\n";

    // Demonstrate vector operations
    demonstrateVectorOperations();

    // Demonstrate statistics
    demonstrateStatistics();

    return 0;
}
