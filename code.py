from machine import Pin, I2C, PWM, ADC
from time import sleep, ticks_ms, ticks_diff
import network
import urequests
import mpu6050

# ==============================
# KONFIGURACE
# ==============================
SSID = "TvojeWiFi"
PASSWORD = "TvojeHeslo"
NTFY_TOPIC = "fall_alert_12345"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# Práhy a časování
FALL_ACCEL_THRESHOLD = 2.5    # g síla pro detekci pádu
FALL_GYRO_THRESHOLD = 250     # deg/s (výrazná rotace)
COUNTDOWN_MS = 5000           # čas na stisk tlačítka Cancel
BATTERY_THRESHOLD = 85        # hranice pro „nabitá baterie“

# ==============================
# HARDWARE
# ==============================
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
mpu = mpu6050.accel(i2c)

rled = Pin(15, Pin.OUT)  # červená
gled = Pin(2, Pin.OUT)   # zelená
bled = Pin(4, Pin.OUT)   # modrá
buzzer = PWM(Pin(5))
buzzer.duty(0)

sos_btn = Pin(12, Pin.IN, Pin.PULL_UP)
cancel_btn = Pin(13, Pin.IN, Pin.PULL_UP)

# simulace baterie a nabíjení (v praxi: ADC na pinu např. 34)
BATTERY_LEVEL = 90
CHARGING_PIN = ADC(Pin(34))  # můžeš použít pro reálné zjištění napětí z nabíječky
CHARGING = False  # defaultně

# ==============================
# FUNKCE PRO SÍTĚ A NOTIFIKACE
# ==============================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("📡 Připojuji se k Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            sleep(0.5)
    print("✅ Wi-Fi připojena:", wlan.ifconfig())

def send_ntfy(title, message):
    """Odešle notifikaci na ntfy.cloud"""
    try:
        headers = {"Title": title}
        response = urequests.post(NTFY_URL, data=message, headers=headers)
        response.close()
        print("📨 Notifikace odeslána na ntfy")
    except Exception as e:
        print("⚠️ Chyba při odesílání ntfy:", e)

# ==============================
# FUNKCE PRO LED A ZVUK
# ==============================
def blink(pin, freq_hz, duration_s):
    """Blikání LED nebo bzučáku (blokující)"""
    period = 1 / freq_hz
    end_time = ticks_ms() + int(duration_s * 1000)
    while ticks_diff(end_time, ticks_ms()) > 0:
        pin.value(1)
        sleep(period / 2)
        pin.value(0)
        sleep(period / 2)

def buzz(freq_hz, duration_s):
    """Bzučák s danou frekvencí blikání"""
    period = 1 / freq_hz
    end_time = ticks_ms() + int(duration_s * 1000)
    while ticks_diff(end_time, ticks_ms()) > 0:
        buzzer.duty(512)
        sleep(period / 2)
        buzzer.duty(0)
        sleep(period / 2)

def stop_alerts():
    buzzer.duty(0)
    bled.off()

def send_sos():
    print("📡 SOS signal odeslán!")
    send_ntfy("🚨 SOS Alert", "Detekován pád nebo nouzová situace!")
    blink(bled, 2, 5)
    buzz(2, 5)

# ==============================
# DETEKCE PÁDU (akcelerometr + gyroskop)
# ==============================
def detect_fall():
    data = mpu.get_values()
    # Akcelerometr
    ax = data["AcX"] / 16384
    ay = data["AcY"] / 16384
    az = data["AcZ"] / 16384
    g_force = (ax**2 + ay**2 + az**2) ** 0.5

    # Gyroskop (v deg/s)
    gx = abs(data["GyX"]) / 131
    gy = abs(data["GyY"]) / 131
    gz = abs(data["GyZ"]) / 131
    rotation = max(gx, gy, gz)

    # Detekce pádu = vysoké zrychlení + velká rotace
    if g_force > FALL_ACCEL_THRESHOLD and rotation > FALL_GYRO_THRESHOLD:
        print(f"🆘 Detekován pád! g={g_force:.2f}, rot={rotation:.1f}")
        return True
    return False

# ==============================
# NEBLOKUJÍCÍ BLINK FUNKCE
# ==============================
def nonblocking_blink(pin, freq_hz, last_toggle):
    """Přepíná LED neblokujícím způsobem"""
    period = 1 / freq_hz
    if ticks_diff(ticks_ms(), last_toggle) >= period * 1000 / 2:
        pin.value(1 - pin.value())
        return ticks_ms()
    return last_toggle

# ==============================
# HLAVNÍ PROGRAM
# ==============================
def main():
    global BATTERY_LEVEL, CHARGING

    connect_wifi()
    gled_last_toggle = ticks_ms()

    print("Systém spuštěn.")

    while True:
        # --- Automatická detekce nabíjení ---
        adc_val = CHARGING_PIN.read()
        CHARGING = adc_val > 1000  # přibližný práh, uprav dle zapojení

        # --- Signalizace nabíjení / stavu baterie ---
        if BATTERY_LEVEL < BATTERY_THRESHOLD:
            rled.on()
            gled.off()
        else:
            rled.off()
            if CHARGING:
                gled.on()  # stále nabíjeno
            else:
                gled_last_toggle = nonblocking_blink(gled, 0.5, gled_last_toggle)

        # --- Detekce pádu nebo SOS ---
        if detect_fall() or sos_btn.value() == 0:
            print("🆘 Pád nebo SOS detekován")
            start_time = ticks_ms()
            while ticks_diff(ticks_ms(), start_time) < COUNTDOWN_MS:
                blink(bled, 1, 1)
                buzz(1, 1)
                if cancel_btn.value() == 0:
                    print("❌ Alarm zrušen")
                    stop_alerts()
                    break
            else:
                send_sos()
                stop_alerts()

        sleep(0.1)

# ==============================
# SPUŠTĚNÍ
# ==============================
try:
    main()
except KeyboardInterrupt:
    stop_alerts()
    print("Program ukončen.")
