#include "utils/MathUtils.h"
#include <algorithm>
#include <cmath>
#include <numeric>

namespace utils
{

    // MathUtils implementation
    double MathUtils::clamp(double value, double min, double max)
    {
        return std::max(min, std::min(value, max));
    }

    double MathUtils::lerp(double a, double b, double t)
    {
        return a + t * (b - a);
    }

    bool MathUtils::isNearZero(double value, double epsilon)
    {
        return std::abs(value) < epsilon;
    }

    // Vector2D template implementations
    template <typename T>
    Vector2D<T> Vector2D<T>::operator+(const Vector2D &other) const
    {
        return Vector2D(x + other.x, y + other.y);
    }

    template <typename T>
    Vector2D<T> Vector2D<T>::operator-(const Vector2D &other) const
    {
        return Vector2D(x - other.x, y - other.y);
    }

    template <typename T>
    Vector2D<T> Vector2D<T>::operator*(T scalar) const
    {
        return Vector2D(x * scalar, y * scalar);
    }

    template <typename T>
    Vector2D<T> &Vector2D<T>::operator+=(const Vector2D &other)
    {
        x += other.x;
        y += other.y;
        return *this;
    }

    template <typename T>
    Vector2D<T> &Vector2D<T>::operator-=(const Vector2D &other)
    {
        x -= other.x;
        y -= other.y;
        return *this;
    }

    template <typename T>
    Vector2D<T> &Vector2D<T>::operator*=(T scalar)
    {
        x *= scalar;
        y *= scalar;
        return *this;
    }

    template <typename T>
    bool Vector2D<T>::operator==(const Vector2D &other) const
    {
        return std::abs(x - other.x) < EPSILON_VAL &&
               std::abs(y - other.y) < EPSILON_VAL;
    }

    template <typename T>
    bool Vector2D<T>::operator!=(const Vector2D &other) const
    {
        return !(*this == other);
    }

    template <typename T>
    T Vector2D<T>::magnitude() const
    {
        return std::sqrt(x * x + y * y);
    }

    template <typename T>
    T Vector2D<T>::magnitudeSquared() const
    {
        return x * x + y * y;
    }

    template <typename T>
    Vector2D<T> Vector2D<T>::normalized() const
    {
        T mag = magnitude();
        if (mag < EPSILON_VAL)
        {
            return Vector2D(T{}, T{});
        }
        return Vector2D(x / mag, y / mag);
    }

    template <typename T>
    T Vector2D<T>::dot(const Vector2D &other) const
    {
        return x * other.x + y * other.y;
    }

    // Explicit template instantiations
    template class Vector2D<float>;
    template class Vector2D<double>;
    template class Vector2D<int>;

    // StatisticsCalculator implementation
    StatisticsCalculator::StatisticsCalculator() : is_sorted_(true)
    {
    }

    StatisticsCalculator::~StatisticsCalculator() = default;

    void StatisticsCalculator::addValue(double value)
    {
        data_.push_back(value);
        is_sorted_ = false;
    }

    void StatisticsCalculator::addValues(const std::vector<double> &values)
    {
        data_.insert(data_.end(), values.begin(), values.end());
        is_sorted_ = false;
    }

    void StatisticsCalculator::clear()
    {
        data_.clear();
        is_sorted_ = true;
    }

    Statistics StatisticsCalculator::calculate() const
    {
        if (data_.empty())
        {
            return Statistics{};
        }

        Statistics stats;
        stats.count = data_.size();
        stats.mean = calculateMean();
        stats.median = calculateMedian();
        stats.standardDeviation = calculateStandardDeviation(stats.mean);

        auto minmax = std::minmax_element(data_.begin(), data_.end());
        stats.minimum = *minmax.first;
        stats.maximum = *minmax.second;

        return stats;
    }

    double StatisticsCalculator::getPercentile(double percentile) const
    {
        if (data_.empty())
        {
            return 0.0;
        }

        sortDataIfNeeded();

        double index = percentile * (data_.size() - 1) / 100.0;
        size_t lower = static_cast<size_t>(std::floor(index));
        size_t upper = static_cast<size_t>(std::ceil(index));

        if (lower == upper)
        {
            return data_[lower];
        }

        double weight = index - lower;
        return data_[lower] * (1.0 - weight) + data_[upper] * weight;
    }

    std::vector<double> StatisticsCalculator::getHistogram(size_t bins) const
    {
        std::vector<double> histogram(bins, 0.0);

        if (data_.empty() || bins == 0)
        {
            return histogram;
        }

        auto minmax = std::minmax_element(data_.begin(), data_.end());
        double min_val = *minmax.first;
        double max_val = *minmax.second;
        double range = max_val - min_val;

        if (range == 0.0)
        {
            histogram[0] = static_cast<double>(data_.size());
            return histogram;
        }

        for (double value : data_)
        {
            size_t bin = static_cast<size_t>((value - min_val) / range * bins);
            if (bin >= bins)
                bin = bins - 1;
            histogram[bin] += 1.0;
        }

        return histogram;
    }

    void StatisticsCalculator::sortDataIfNeeded() const
    {
        if (!is_sorted_)
        {
            std::sort(data_.begin(), data_.end());
            is_sorted_ = true;
        }
    }

    double StatisticsCalculator::calculateMean() const
    {
        return std::accumulate(data_.begin(), data_.end(), 0.0) / data_.size();
    }

    double StatisticsCalculator::calculateMedian() const
    {
        sortDataIfNeeded();

        size_t size = data_.size();
        if (size % 2 == 0)
        {
            return (data_[size / 2 - 1] + data_[size / 2]) / 2.0;
        }
        else
        {
            return data_[size / 2];
        }
    }

    double StatisticsCalculator::calculateStandardDeviation(double mean) const
    {
        if (data_.size() <= 1)
        {
            return 0.0;
        }

        double sum_squared_diff = 0.0;
        for (double value : data_)
        {
            double diff = value - mean;
            sum_squared_diff += diff * diff;
        }

        return std::sqrt(sum_squared_diff / (data_.size() - 1));
    }

} // namespace utils
