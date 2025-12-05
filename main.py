"""
MPU6050 Fall Detection Alarm

This module implements a simple fall detection system using the MPU6050 accelerometer
and gyroscope sensor on an ESP32 or compatible MicroPython board. The system monitors
acceleration and rotation values to detect a fall event, then activates an alarm
consisting of a red LED and a buzzer. The alarm remains active until manually canceled
by pressing a button.

Hardware connections:
- MPU6050 connected via I2C on default pins (SDA=GPIO21, SCL=GPIO22)
- Red LED (alarm indicator) connected to GPIO27
- Green LED (system status) connected to GPIO26
- Buzzer connected to GPIO25 (PWM)
- Cancel button connected to GPIO33 (active low with pull-up resistor)

Usage:
Run this script on the device. The green LED will be on when the system is idle.
If a fall is detected (acceleration > 1.2 g), the alarm activates with red LED and buzzer.
Pressing the cancel button will deactivate the alarm and restore the green LED.

Press Ctrl+C in the terminal to safely stop the program.
"""

from machine import Pin, PWM
from time import sleep
from MPU6050 import MPU6050

# Initialize MPU6050 sensor
mpu = MPU6050()

# Initialize LEDs and buzzer
rled = Pin(27, Pin.OUT)      # Red LED for alarm status
gled = Pin(26, Pin.OUT)      # Green LED for system OK status
buzzer = PWM(Pin(25))
buzzer.duty(0)               # Buzzer initially off

alarm_active = False  # Current alarm state


def btn_cancel_handler(pin):
    """
    Interrupt handler for the cancel button.
    When the button is pressed (active low), it deactivates the alarm,
    turns off the red LED and buzzer, and turns on the green LED.

    Args:
        pin (Pin): The GPIO pin object that triggered the interrupt.
    """
    global alarm_active
    if alarm_active:
        print("✅ Alarm zrušen tlačítkem (IRQ)")
        alarm_active = False
        rled.off()
        buzzer.duty(0)
        gled.on()


# Setup cancel button with interrupt on falling edge (button press)
btn_cancel = Pin(33, Pin.IN, Pin.PULL_UP)
btn_cancel.irq(trigger=Pin.IRQ_FALLING, handler=btn_cancel_handler)

# Turn on green LED to indicate system is ready
gled.on()

try:
    while True:
        # Read accelerometer and gyroscope data from MPU6050
        accel_data = mpu.read_accel_data(g=True)
        gyro_data = mpu.read_gyro_data()

        # Calculate absolute gyroscope rotation values
        gx = abs(gyro_data['x'])
        gy = abs(gyro_data['y'])
        gz = abs(gyro_data['z'])

        # Calculate total acceleration (g-force)
        g_force = (accel_data['x']**2 + accel_data['y']**2 + accel_data['z']**2)**0.5
        # Determine the maximum rotation rate
        rotation = max(gx, gy, gz)

        print(f"g_force={g_force:.2f} g, rotation={rotation:.1f} deg/s")

        if not alarm_active:
            # Detect fall event if g_force exceeds threshold
            if g_force > 1.2:
                alarm_active = True
                print("⚠️ Alarm aktivován!")
                rled.on()
                buzzer.duty(512)
                gled.off()
        else:
            # Alarm active: keep red LED and buzzer on, green LED off
            rled.on()
            buzzer.duty(512)
            gled.off()

        sleep(0.1)

except KeyboardInterrupt:
    # Cleanup on exit
    print("Smyčka přerušena uživatelem")
    rled.off()
    buzzer.duty(0)
    gled.off()
