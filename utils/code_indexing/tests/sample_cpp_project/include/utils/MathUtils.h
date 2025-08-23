#pragma once

#include <vector>
#include <memory>

namespace utils
{

    /**
     * Utility class for mathematical operations.
     */
    class MathUtils
    {
    public:
        // Static methods
        static double clamp(double value, double min, double max);
        static double lerp(double a, double b, double t);
        static bool isNearZero(double value, double epsilon = 1e-9);

        // Constants
        static constexpr double EPSILON = 1e-9;
        static constexpr double GOLDEN_RATIO = 1.618033988749895;

    private:
        // Prevent instantiation
        MathUtils() = delete;
        ~MathUtils() = delete;
        MathUtils(const MathUtils &) = delete;
        MathUtils &operator=(const MathUtils &) = delete;
    };

    /**
     * Template class for 2D vectors.
     */
    template <typename T>
    class Vector2D
    {
    public:
        Vector2D() : x(T{}), y(T{}) {}
        Vector2D(T x_val, T y_val) : x(x_val), y(y_val) {}

        // Arithmetic operators
        Vector2D operator+(const Vector2D &other) const;
        Vector2D operator-(const Vector2D &other) const;
        Vector2D operator*(T scalar) const;
        Vector2D &operator+=(const Vector2D &other);
        Vector2D &operator-=(const Vector2D &other);
        Vector2D &operator*=(T scalar);

        // Comparison operators
        bool operator==(const Vector2D &other) const;
        bool operator!=(const Vector2D &other) const;

        // Utility methods
        T magnitude() const;
        T magnitudeSquared() const;
        Vector2D normalized() const;
        T dot(const Vector2D &other) const;

        // Public members
        T x, y;

    private:
        static constexpr T EPSILON_VAL = static_cast<T>(1e-9);
    };

    /**
     * Statistics calculator for numerical data.
     */
    struct Statistics
    {
        double mean;
        double median;
        double standardDeviation;
        double minimum;
        double maximum;
        size_t count;

        Statistics() : mean(0), median(0), standardDeviation(0),
                       minimum(0), maximum(0), count(0) {}
    };

    /**
     * Statistical analysis utility class.
     */
    class StatisticsCalculator
    {
    public:
        StatisticsCalculator();
        ~StatisticsCalculator();

        // Data management
        void addValue(double value);
        void addValues(const std::vector<double> &values);
        void clear();

        // Calculations
        Statistics calculate() const;
        double getPercentile(double percentile) const;
        std::vector<double> getHistogram(size_t bins) const;

        // Accessors
        size_t getCount() const { return data_.size(); }
        bool isEmpty() const { return data_.empty(); }

    protected:
        void sortDataIfNeeded() const;

    private:
        std::vector<double> data_;
        mutable bool is_sorted_;

        // Helper methods
        double calculateMean() const;
        double calculateMedian() const;
        double calculateStandardDeviation(double mean) const;
    };

    // Type aliases
    using Vec2f = Vector2D<float>;
    using Vec2d = Vector2D<double>;
    using Vec2i = Vector2D<int>;

} // namespace utils
