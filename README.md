# Preprototype of fall detection device

In this project I focused on getting familiar with basic
functions I will later use in my bachelors project.

I constructed basic electronic hardware that reads data
and has simple user-device interface and runned basic
code on it.

---

## Used Hardware

| Component |Function | Connected via |
|-----------|--------|-----------|
| ESP32 | microcontroler | USB to laptop |
| MPU6050 | accelerometer+gyroscope | I2C: SDA → GPIO21, SCL → GPIO22 |
| Red LED | alarm signalization | GPIO27 |
| Green LED | normal state | GPIO26 |
| Buzzer | alarm signalization | GPIO25 |
| Button | alarm cancelation | GPIO33 (pull-up) |

---

## Instalation

1. The micropython must be instaled to ESP32 in order for
   the code to run.
3. Then the following files need to be uploaded to ESP32:
   - `main.py` (the main code)
   - `MPU6050.py` (the sensor controler)
4. Restart the ESP32 – code should start automatically.

---

## Running the code

After the start:

- Green LED should shine
- The data of acceleration and rotation should be written
  into terminal
- If the acceleration exceeds threshold (1.2g, can be changed in code)=alarm:
  - the green led turns off
  - the red led turns on
  - buzzer turns on
- If the button is pressed the alarm turns off.

Measurements are taken at intervals of 0.1 seconds..

---

## Testing done

| Test | result |
|------|-------------------|
| lays still | g-force ≈ 1.08 g, no alarm |
| shake | alarms turn on |
| button pressed when alarm off| nothing |
| button pressed when alarm on| alarm turns off |


For more details abou testing see: **[hardware_tests_report.md](testing/hardware_tests_report.md)**.



---

## Future of the project

- threshold adjusted for real fall
- battery powered and wearable
- more user<->device interface (another button, more LED signals)
- emergency messages will be sent via wifi to remote device


Chceš, abych ti upravil kód pro lepší detekci a přidal např. **sekvenční rozpoznání pádu (reálnější algoritmus)**?  
Napiš *„chci vylepšenou detekci“* a pošlu hotovou verzi. 🚀
