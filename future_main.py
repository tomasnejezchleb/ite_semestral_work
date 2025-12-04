from machine import Pin, I2C, PWM, ADC
from time import sleep, ticks_ms, ticks_diff
import network
import urequests
from MPU6050 import MPU6050


# ========================
# WiFi + odesílání zpráv
# ========================

SSID = "localwifiname"
PASSWORD = "localwifipassword"
NTFY_URL = "https://....."   # doplň skutečný link ntfy.sh/topic

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Připojuji...")
    while not wlan.isconnected():
        sleep(0.5)
    print("WiFi OK:", wlan.ifconfig())


# ========================
# Nastavení prahů
# ========================

FALL_ACCEL_THRESHOLD = 5        # [g]
FALL_GYRO_THRESHOLD = 250       # [deg/s]
COUNTDOWN_MS = 10000            # čas na Cancel
BATTERY_THRESHOLD_LOW = 25
BATTERY_THRESHOLD_HIGH = 85


# ========================
# Piny
# ========================

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
mpu = MPU6050(i2c)

rled = Pin(27, Pin.OUT)      # červená
gled = Pin(26, Pin.OUT)      # zelená
bled = Pin(14, Pin.OUT)      # modrá
buzzer = PWM(Pin(25))
buzzer.duty(0)

btn_sos  = Pin(33, Pin.IN, Pin.PULL_UP)
btn_cncl = Pin(32, Pin.IN, Pin.PULL_UP)   # TODO: doplň správný pin

battery_lvl = ADC(Pin(35))               # TODO: doplň správný pin
battery_lvl.atten(ADC.ATTN_11DB)         # měří až 3.3V → vhodné pro baterii


# ========================
# Funkce
# ========================

def send_ntfy(title="FALL", message="Detekován pád!"):
    try:
        headers = {"Title": title}
        response = urequests.post(NTFY_URL, data=message, headers=headers)
        response.close()
        print("Notifikace odeslána ✓")
    except Exception as e:
        print("Chyba odesílání:", e)


def nonblocking_blink(pin, freq_hz, last_toggle):
    period = 1000 / freq_hz / 2
    if ticks_diff(ticks_ms(), last_toggle) >= period:
        pin.value(1 - pin.value())
        return ticks_ms()
    return last_toggle


def nonblocking_buzz(freq_hz, last_toggle):
    period = 1000 / freq_hz / 2
    if ticks_diff(ticks_ms(), last_toggle) >= period:
        buzzer.duty(512 if buzzer.duty()==0 else 0)
        return ticks_ms()
    return last_toggle


def stop_alerts():
    buzzer.duty(0)
    bled.off()


def detect_fall():
    data = mpu.get_values()

    ax = data["AcX"]/16384
    ay = data["AcY"]/16384
    az = data["AcZ"]/16384
    g_force = (ax*ax + ay*ay + az*az) ** 0.5

    gx = abs(data["GyX"])/131
    gy = abs(data["GyY"])/131
    gz = abs(data["GyZ"])/131
    rotation = max(gx,gy,gz)

    if g_force > FALL_ACCEL_THRESHOLD and rotation > FALL_GYRO_THRESHOLD:
        print(f"‼ Pád detekován  g={g_force:.2f} rot={rotation:.1f}")
        return True
    return False


# ========================
# Hlavní smyčka
# ========================

def main():
    connect_wifi()

    gled_toggle = bled_toggle = buzz_toggle = 0
    alarm = False
    alarm_start = 0

    while True:
        # Čtení baterie (0–4095 → procenta orientačně)
        adc = battery_lvl.read()
        level = int(adc/4095*100)

        # Monitoring baterie
        if level < BATTERY_THRESHOLD_LOW:
            rled.on(); gled.off()
        elif level > BATTERY_THRESHOLD_HIGH:
            rled.off(); gled.on()
        else:
            gled_toggle = nonblocking_blink(gled, 1, gled_toggle)

        # Trigger pád / SOS
        if not alarm and (detect_fall() or btn_sos.value()==0):
            print("🆘 Alarm aktivní")
            alarm = True
            alarm_start = ticks_ms()

        # Pokud probíhá alarm
        if alarm:
            bled_toggle = nonblocking_blink(bled, 1, bled_toggle)
            buzz_toggle = nonblocking_buzz(2, buzz_toggle)

            # Timeout – odeslat SOS
            if ticks_diff(ticks_ms(), alarm_start) > COUNTDOWN_MS:
                send_ntfy("FALL ALERT")
                stop_alerts()
                alarm = False

            # Uživatel zrušil
            if btn_cncl.value()==0:
                print("❌ Zrušeno uživatelem")
                stop_alerts()
                alarm=False


try:
    main()
except KeyboardInterrupt:
    stop_alerts()
    print("KONEC")
