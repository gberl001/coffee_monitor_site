import math
import sys
import time

import RPi.GPIO as GPIO
from lib.hx711 import HX711
from lib.lcddriver import lcd as lcddriver

# Config
GRAMS_PER_OZ = 28.35
NUM_READINGS = 33   # Should be an odd number
FULL_CUP = 10          # A full cup is about 10 ounces
SPLATTER_POINT = 73          # At this point you'll get splatter, and empty carafe is actually 69.25oz
EMPTY_CARAFE = 69          # An empty carafe is about 69.25oz
FULL_CARAFE = 150         # A full carafe is about 150oz
EMPTY_SCALE_THRESHOLD = 10          # Assume the scale is empty at 10 ounces
MINUTES_IN_HOUR = 60            # 60 Minutes in an hour
MILLIS_IN_MINUTE = 60000         # 60000 ms in a minute
EVENT_PIN = 4             # The pin that will send out an event notification
SERIAL_DEBUG = 1             # Set to 1 to have statements printed to the monitor

# Create objects
hx = HX711(5, 6)
lcd = lcddriver()

# Global variables
lastBrewTime = 0
latestRecordedWeight = 0.0


def setup():
    # LCD Stuff
    lcd.lcd_clear()
    lcd.lcd_display_string("Please Wait...", 1)

    # Scale Stuff
    hx.set_reading_format("MSB", "MSB")
    hx.set_reference_unit(21)
    hx.reset()
    time.sleep(1.0)     # Small delay for settling
    hx.tare()           # Reset the scale to 0

    # Setup the scale
    initScale()


def cleanAndExit():
    print("Cleaning...")
    GPIO.cleanup()

    print("Bye!")
    sys.exit()


def initScale():
    # Ready
    lcd.lcd_clear()
    lcd.lcd_display_string("Ready", 1)
    lcd.lcd_display_string("Add container", 2)

    # Wait for scale to have weight added to it.
    while getScaleReading() < 1.0:
        time.sleep(2.0)


# *******************************************************************************************************
# *******************************************************************************************************
# ************************************ State Functions **************************************************
# *******************************************************************************************************
# *******************************************************************************************************

def getAgeString():
    minutes = (millis() - lastBrewTime) / MILLIS_IN_MINUTE

    # Compute the hours
    strHours = str(int(math.floor(minutes / MINUTES_IN_HOUR))) + "H "

    # Compute the remaining minutes
    strMinutes = str(minutes % MINUTES_IN_HOUR) + "M"

    return str(strHours + strMinutes)


def handleCarafeEmpty():
    lcd.lcd_clear()
    lcd.lcd_display_string("Empty Container", 1)


def handleCarafeNotEmpty(reading):
    # Display the age and cups remaining
    lcd.lcd_clear()
    lcd.lcd_display_string("Age: " + str(getAgeString()), 1)
    lcd.lcd_display_string("Cups Left: " + str(round(getCupsRemaining(reading), 2)), 2)


def handleEmptyScale():
    global latestRecordedWeight

    # Either there is a new brew coming or someone simply lifted the carafe temporarily, record the previous weight
    previousWeight = latestRecordedWeight

    # While the scale is empty, display that we're waiting for more coffee
    lcd.lcd_clear()
    lcd.lcd_display_string("Waiting for", 1)
    lcd.lcd_display_string("next brew", 2)
    # NOTE: By using scaleIsEmpty, technically any weight can be added to leave this state
    #       which may be undesirable but for now I like it this way. In the future I may
    #       change this to while reading is less than empty carafe so it doesn't show
    #       negative cups
    while scaleIsEmpty(getScaleReading()):
        if SERIAL_DEBUG > 0:
            print("Tare")

        # TODO: Need more data to determine whether taring here is a good idea
        hx.tare()
        time.sleep(2.0)

    # Now that the scale isn't empty, determine if more coffee was added
    if latestRecordedWeight > previousWeight + FULL_CUP:
        # If the new wight is at least one more cup of coffee more than the old, assume a new brew
        handleFreshBrew()


def handleFreshBrew():
    global lastBrewTime

    # Update the last brew time
    lastBrewTime = millis()

    # Notify the WiFi module driving the event pin HIGH for half a second
    GPIO.output(EVENT_PIN, True)
    time.sleep(0.5)
    GPIO.output(EVENT_PIN, False)


# *******************************************************************************************************
# *******************************************************************************************************
# *********************************** Utility Functions *************************************************
# *******************************************************************************************************
# *******************************************************************************************************

def millis():
    return int(round(time.time() * 1000))


def scaleIsEmpty(reading):
    return reading < EMPTY_SCALE_THRESHOLD


def carafeIsEmpty(reading):
    # If the reading is between empty and where the coffee splatters...
    return EMPTY_CARAFE <= reading <= SPLATTER_POINT


def getCupsRemaining(reading):
    return (reading - SPLATTER_POINT) / FULL_CUP


def getScaleReading():
    global latestRecordedWeight
    # Keep taking readings one second apart until they are within 1 ounce of each other (indicating stability)
    # This should ensure a reading isn't taken while weight is added or removed from the scale
    firstReading = 0
    secondReading = 10
    while abs(firstReading - secondReading) >= 1:
        firstReading = abs(hx.get_weight(NUM_READINGS)) / GRAMS_PER_OZ
        # I don't think the sleep is needed any longer since it takes a good 2 seconds to read the scale
        # time.sleep(1.0)
        secondReading = abs(hx.get_weight(NUM_READINGS)) / GRAMS_PER_OZ

    if SERIAL_DEBUG > 0:
        print("Reading is " + str(round(secondReading, 2)))

    # If the scale isn't empty, record the last weight
    if not scaleIsEmpty(secondReading):
        latestRecordedWeight = secondReading

    return secondReading


def main():
    try:
        setup()

        while True:
            # Take a reading
            reading = getScaleReading()

            # Determine the state
            if scaleIsEmpty(reading):
                if SERIAL_DEBUG > 0:
                    print("STATE: Scale is Empty")
                handleEmptyScale()
            elif carafeIsEmpty(reading):
                if SERIAL_DEBUG > 0:
                    print("STATE: Carafe is Empty")
                handleCarafeEmpty()
            elif not (carafeIsEmpty(reading)):
                if SERIAL_DEBUG > 0:
                    print("STATE: Carafe is NOT Empty")
                handleCarafeNotEmpty(reading)

            time.sleep(2.0)

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()


if __name__ == "__main__":
    main()
