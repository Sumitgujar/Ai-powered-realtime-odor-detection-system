#include <cassert>
#include <cmath>
#include <iostream>

#include "calibration.h"

int main() {
  assert(std::fabs(applyCalibration(100.0f, 1.1f, -10.0f, 0.0f, 1023.0f) -
                   100.0f) < 0.001f);
  assert(applyCalibration(5000.0f, 1.0f, 0.0f, 0.0f, 1023.0f) == 1023.0f);
  assert(applyCalibration(-20.0f, 1.0f, 0.0f, 0.0f, 1023.0f) == 0.0f);
  assert(applyCalibration(NAN, 1.0f, 0.0f, 0.0f, 1023.0f) == 0.0f);
  std::cout << "Calibration tests passed\n";
  return 0;
}
