from machine import Pin, PWM
from time import sleep, ticks_ms, ticks_diff
from MPU6050 import MPU6050
import network
import urequests


# =======================
# KONFIGURACE
# =======================

SSID = "cuky"
PASSWORD = "tomas_335"
NTFY_URL = "https://ntfy.sh/fall_detection_9fk3a8DQ"

WIFI_TIMEOUT_S = 10
ALARM_THRESHOLD_G = 1.2
REARM_DELAY_MS = 5000


# =======================
# WIFI – JEDEN OBJEKT
# =======================

wlan = network.WLAN(network.STA_IF)


def connect_wifi(timeout_s=WIFI_TIMEOUT_S):
    """
    Bezpečné připojení k WiFi.
    Nepoužívá nový WLAN objekt.
    """
    wlan.active(True)

    if wlan.isconnected():
        return True

    print("📡 Připojuji se k WiFi...")
    try:
        wlan.disconnect()
        sleep(0.2)
        wlan.connect(SSID, PASSWORD)

        t0 = ticks_ms()
        while not wlan.isconnected():
            if ticks_diff(ticks_ms(), t0) > timeout_s * 1000:
                print("❌ WiFi timeout")
                return False
            sleep(0.5)

        print("✅ WiFi OK:", wlan.ifconfig())
        return True

    except OSError as e:
        print("❌ WiFi error:", e)
        return False


def ensure_wifi():
    """
    Zajistí, že WiFi je připojena.
    """
    if not wlan.isconnected():
        print("⚠️ WiFi spadla – reconnect")
        return connect_wifi()
    return True


# =======================
# NOTIFIKACE (NTFY)
# =======================

def send_ntfy(title="FALL", message="Detekován pád!"):
    try:
        headers = {
            "Title": title,
            "Priority": "urgent"
        }
        r = urequests.post(NTFY_URL, data=message, headers=headers)
        r.close()
        print("📨 Notifikace odeslána")
    except Exception as e:
        print("❌ Chyba ntfy:", e)


# =======================
# HW INIT
# =======================

mpu = MPU6050()

rled = Pin(27, Pin.OUT)
gled = Pin(26, Pin.OUT)
buzzer = PWM(Pin(25))
buzzer.duty(0)

btn_cancel = Pin(33, Pin.IN, Pin.PULL_UP)

gled.on()


# =======================
# STAVY
# =======================

alarm_active = False
alarm_cancelled = False
last_alarm_time = 0


# =======================
# IRQ – ZRUŠENÍ ALARMU
# =======================

def btn_cancel_handler(pin):
    global alarm_active, alarm_cancelled

    if alarm_active:
        alarm_active = False
        alarm_cancelled = True

        rled.off()
        buzzer.duty(0)
        gled.on()

        print("✅ Alarm zrušen tlačítkem (IRQ)")


btn_cancel.irq(trigger=Pin.IRQ_FALLING, handler=btn_cancel_handler)


# =======================
# START WIFI
# =======================

connect_wifi()


# =======================
# HLAVNÍ SMYČKA
# =======================

try:
    while True:
        accel = mpu.read_accel_data(g=True)
        gyro = mpu.read_gyro_data()

        g_force = (accel['x']**2 + accel['y']**2 + accel['z']**2) ** 0.5
        rotation = max(abs(gyro['x']), abs(gyro['y']), abs(gyro['z']))

        print(f"g_force={g_force:.2f} g | rotation={rotation:.1f} dps")

        now = ticks_ms()

        # ===== DETEKCE PÁDU =====
        if not alarm_active:
            if ticks_diff(now, last_alarm_time) > REARM_DELAY_MS:
                if g_force > ALARM_THRESHOLD_G:
                    alarm_active = True
                    last_alarm_time = now

                    print("⚠️ ALARM AKTIVOVÁN")
                    rled.on()
                    gled.off()
                    buzzer.duty(512)

                    if ensure_wifi():
                        send_ntfy(
                            title="⚠️ Detekován pád",
                            message=f"g_force={g_force:.2f} g"
                        )
        else:
            rled.on()
            buzzer.duty(512)
            gled.off()

        # ===== ZRUŠENÍ ALARMU =====
        if alarm_cancelled:
            alarm_cancelled = False
            if ensure_wifi():
                send_ntfy(
                    title="✅ Alarm zrušen",
                    message="Uživatel potvrdil, že je v pořádku"
                )

        sleep(0.1)

except KeyboardInterrupt:
    print("⏹ Program ukončen uživatelem")
    rled.off()
    gled.off()
    buzzer.duty(0)
