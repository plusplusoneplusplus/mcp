#include "geometry/Shape.h"
#include <iostream>
#include <cmath>

namespace geometry
{

    // Shape implementation
    Shape::Shape(double x, double y) : x_(x), y_(y)
    {
    }

    void Shape::move(double dx, double dy)
    {
        x_ += dx;
        y_ += dy;
    }

    void Shape::setPosition(double x, double y)
    {
        x_ = x;
        y_ = y;
    }

    // Rectangle implementation
    Rectangle::Rectangle(double x, double y, double width, double height)
        : Shape(x, y), width_(width), height_(height)
    {
        if (width_ < MIN_SIZE)
            width_ = MIN_SIZE;
        if (height_ < MIN_SIZE)
            height_ = MIN_SIZE;
    }

    double Rectangle::area() const
    {
        return width_ * height_;
    }

    double Rectangle::perimeter() const
    {
        return 2.0 * (width_ + height_);
    }

    void Rectangle::draw() const
    {
        std::cout << "Drawing rectangle at (" << getX() << ", " << getY()
                  << ") with width " << width_ << " and height " << height_ << std::endl;
    }

    void Rectangle::resize(double newWidth, double newHeight)
    {
        width_ = (newWidth > MIN_SIZE) ? newWidth : MIN_SIZE;
        height_ = (newHeight > MIN_SIZE) ? newHeight : MIN_SIZE;
    }

    bool Rectangle::isSquare() const
    {
        return std::abs(width_ - height_) < MIN_SIZE;
    }

    // Circle implementation
    Circle::Circle(double x, double y, double radius)
        : Shape(x, y), radius_(radius)
    {
        if (radius_ < 0.0)
            radius_ = 0.0;
    }

    double Circle::area() const
    {
        return PI * radius_ * radius_;
    }

    double Circle::perimeter() const
    {
        return 2.0 * PI * radius_;
    }

    void Circle::draw() const
    {
        std::cout << "Drawing circle at (" << getX() << ", " << getY()
                  << ") with radius " << radius_ << std::endl;
    }

    void Circle::setRadius(double newRadius)
    {
        radius_ = (newRadius >= 0.0) ? newRadius : 0.0;
    }

} // namespace geometry
