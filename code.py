from machine import Pin, I2C, PWM, ADC 
from time import sleep, ticks_ms, ticks_diff
import network
import urequests
import mpu6050

# ==============================
# KONFIGURACE
# ==============================
SSID = "TvojeWiFi"  # lokální wifi, ke které se připojuje zařízení
PASSWORD = "TvojeHeslo"
NTFY_TOPIC = "fall_alert_12345"  # téma odesílaného oznámení
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"  # adresa/cloud, kam je oznámení odesíláno

# Práhy a časování
FALL_ACCEL_THRESHOLD = 5    # g síla pro detekci pádu-dle rešerše to bude klidně třeba 5g
FALL_GYRO_THRESHOLD = 250     # deg/s (výrazná rotace)
COUNTDOWN_MS = 10000           # čas na stisk tlačítka Cancel v milisekundách
BATTERY_THRESHOLD = 85        # hranice pro „nabitá baterie“

# ==============================
# HARDWARE upravit piny dle reálného zapojení!!!
# ==============================
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
mpu = mpu6050.accel(i2c)    # vytvoření instance MPU6050 pro komunikaci přes I2C

rled = Pin(15, Pin.OUT)  # červená,
gled = Pin(2, Pin.OUT)   # zelená
bled = Pin(4, Pin.OUT)   # modrá
buzzer = PWM(Pin(5))    # PWM-pulse width modulation-umožňuje neposílat stálé napětí, ale jen pulzy->buď pulzace bzučáku, nebo jen snížení spotřeby za cenu nižší intenzity (záleží na frekvenci)
buzzer.duty(0)  # bzučák začíná na nule-tzn je vypnutý

sos_btn = Pin(12, Pin.IN, Pin.PULL_UP)  # tlačítko nestisknuté->pin HIGH (=log 0), stisk-spojení s GND->pin LOW
cancel_btn = Pin(13, Pin.IN, Pin.PULL_UP)

# simulace baterie a nabíjení (v praxi: ADC na pinu např. 34)
BATTERY_LEVEL = 90
CHARGING_PIN = ADC(Pin(34))  # můžeš použít pro reálné zjištění napětí z nabíječky
CHARGING = False  # defaultně

# ==============================
# FUNKCE PRO SÍTĚ A NOTIFIKACE
# ==============================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)  # vytvoření objektu pro správu wifi. STA_IF station interface=režim stanice=zařízení je klientem domácí wifi
    wlan.active(True)   # aktivace wifi
    if not wlan.isconnected():
        print("📡 Připojuji se k Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            sleep(0.5)  # hodnota času sleep [s] bude nastavena dle možností procesoru- aby se nepřetížil
    print("✅ Wi-Fi připojena:", wlan.ifconfig())  # vypsání informací o síti

def send_ntfy(title, message):
    """Odešle notifikaci na ntfy.cloud"""
    try:
        headers = {"Title": title}
        response = urequests.post(NTFY_URL, data=message, headers=headers)  # odeslání požadavku na adresu url cloudové služby
        response.close()    # zavře http spojení
        print("📨 Notifikace odeslána na ntfy")
    except Exception as e:
        print("⚠️ Chyba při odesílání ntfy:", e)

# ==============================
# FUNKCE PRO LED A ZVUK (neblokující verze)
# ==============================
def nonblocking_blink(pin, freq_hz, last_toggle):
    """Přepíná LED neblokujícím způsobem"""
    period = 1 / freq_hz
    if ticks_diff(ticks_ms(), last_toggle) >= period * 1000 / 2:
        pin.value(1 - pin.value())
        return ticks_ms()
    return last_toggle

def nonblocking_buzz(freq_hz, last_toggle):
    """Pípání bzučáku neblokujícím způsobem"""
    period = 1 / freq_hz
    if ticks_diff(ticks_ms(), last_toggle) >= period * 1000 / 2:
        if buzzer.duty() == 0:
            buzzer.duty(512)
        else:
            buzzer.duty(0)
        return ticks_ms()
    return last_toggle

def stop_alerts():
    buzzer.duty(0)
    bled.off()

def send_sos():
    print("📡 SOS signal odeslán!")
    send_ntfy("🚨 SOS Alert", "Detekován pád nebo nouzová situace!")

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
# HLAVNÍ PROGRAM
# ==============================
def main():
    global BATTERY_LEVEL, CHARGING

    connect_wifi()
    gled_last_toggle = ticks_ms()
    bled_last_toggle = 0
    buzz_last_toggle = 0
    alarm_active = False
    alarm_start_time = 0

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
        if not alarm_active and (detect_fall() or sos_btn.value() == 0):
            print("🆘 Pád nebo SOS detekován, spouštím alarm")
            alarm_active = True
            alarm_start_time = ticks_ms()

        if alarm_active:
            # Během alarmu blikání a pípání neblokujícím způsobem
            bled_last_toggle = nonblocking_blink(bled, 1, bled_last_toggle)
            buzz_last_toggle = nonblocking_buzz(1, buzz_last_toggle)

            # Kontrola, jestli už neuplynul čas pro zrušení alarmu
            if ticks_diff(ticks_ms(), alarm_start_time) > COUNTDOWN_MS:
                send_sos()
                stop_alerts()
                alarm_active = False

            # Pokud uživatel stiskne cancel, zruší alarm
            if cancel_btn.value() == 0:
                print("❌ Alarm zrušen uživatelem")
                stop_alerts()
                alarm_active = False

        else:
            # Když není alarm, LED modrá vypnutá
            bled.off()
            buzzer.duty(0)

        sleep(0.1)

# ==============================
# SPUŠTĚNÍ
# ==============================
try:
    main()
except KeyboardInterrupt:
    stop_alerts()
    print("Program ukončen.")
