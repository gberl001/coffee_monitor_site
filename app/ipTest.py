import subprocess
import time
from lib.lcddriver import lcd as lcddriver

lcd = lcddriver()


while True:
    cmd = "hostname -I | cut -d\' \' -f1"
    ip = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    lcd.lcd_clear()
    lcd.lcd_display_string("IP: " + ip, 4)

    print("IP: " + ip)

    time.sleep(1.0)
