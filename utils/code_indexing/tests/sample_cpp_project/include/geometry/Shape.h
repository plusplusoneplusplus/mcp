#pragma once

namespace geometry
{

    /**
     * Abstract base class for geometric shapes.
     */
    class Shape
    {
    public:
        Shape(double x = 0.0, double y = 0.0);
        virtual ~Shape() = default;

        // Pure virtual methods
        virtual double area() const = 0;
        virtual double perimeter() const = 0;
        virtual void draw() const = 0;

        // Concrete methods
        void move(double dx, double dy);
        double getX() const { return x_; }
        double getY() const { return y_; }

    protected:
        void setPosition(double x, double y);

    private:
        double x_;
        double y_;
    };

    /**
     * Rectangle class inheriting from Shape.
     */
    class Rectangle : public Shape
    {
    public:
        Rectangle(double x, double y, double width, double height);

        // Override virtual methods
        double area() const override;
        double perimeter() const override;
        void draw() const override;

        // Rectangle-specific methods
        double getWidth() const { return width_; }
        double getHeight() const { return height_; }
        void resize(double newWidth, double newHeight);

    protected:
        bool isSquare() const;

    private:
        double width_;
        double height_;

        static constexpr double MIN_SIZE = 0.001;
    };

    /**
     * Circle class inheriting from Shape.
     */
    class Circle : public Shape
    {
    public:
        explicit Circle(double x, double y, double radius);

        // Override virtual methods
        double area() const override;
        double perimeter() const override;
        void draw() const override;

        // Circle-specific methods
        double getRadius() const { return radius_; }
        void setRadius(double newRadius);

    private:
        double radius_;

        static constexpr double PI = 3.14159265359;
    };

} // namespace geometry
