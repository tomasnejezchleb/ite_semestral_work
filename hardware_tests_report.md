# Hardware Test Report

This document summarizes the results of practical hardware tests performed on the ESP32 alarm device.

---

## Test 1 — Button Press While Alarm is Off
**Observation:**  
Pressing the button while the alarm is inactive results in no action, which
was expected.

---

## Test 2 — Shake Detection Reliability
**Procedure:**  
The device was shaken 10 times.

**Results:**  
- Alarm was successfully triggered every time.  
- Cancelation via *CNCL* button worked reliably.  
- No malfunction occurred even when the cancel button was pressed repeatedly.  


---

## Test 3 — Sensor Accuracy (Accelerometer + Gyroscope)

| Condition | Acceleration (g) | Rotation (°/s) |
|----------|------------------|----------------|
| Device still on table | ~1.08 g | ~2.9 °/s |
| Device shaken | ~1.40 g | ~40 °/s |

**Conclusion:**  
Measured sensor values respond appropriately to motion. Sensitivity appears consistent.

---

### Summary
All basic hardware functionalities (input button, shake detection, cancel mechanism, sensor values) behaved correctly under tested conditions.

Further tests may be- see README.md in main

