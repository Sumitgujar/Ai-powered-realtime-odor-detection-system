#pragma once

#include <cmath>

template <typename T>
constexpr T clampValue(T value, T minimum, T maximum) {
  return value < minimum ? minimum : (value > maximum ? maximum : value);
}

inline float applyCalibration(float raw, float scale, float offset,
                              float minimum, float maximum) {
  if (!std::isfinite(raw) || !std::isfinite(scale) || !std::isfinite(offset)) {
    return minimum;
  }
  return clampValue(raw * scale + offset, minimum, maximum);
}
