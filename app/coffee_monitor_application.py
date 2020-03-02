import math
import subprocess
import sys
import time

sys.path.append('/home/pi/repos/python/coffee_monitor_site/app/lib')

import RPi.GPIO as GPIO
import sqlalchemy as db
from lib.ads1232 import ADS1232
from lib.lcddriver import lcd as lcddriver
from models import WeightReading
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Config
GRAMS_PER_OZ = 28.35
NUM_READINGS = 21   # Should be an odd number
FULL_CUP = 10          # A full cup is about 10 ounces
SPLATTER_POINT = 73          # At this point you'll get splatter, and empty carafe is actually 69.25oz
EMPTY_CARAFE = 69          # An empty carafe is about 69.25oz
FULL_CARAFE = 150         # A full carafe is about 150oz
HALF_CARAFE = EMPTY_CARAFE + (FULL_CARAFE - EMPTY_CARAFE)/2  # Rough estimate of where a half brew should be
EMPTY_SCALE_THRESHOLD = 10          # Assume the scale is empty at 10 ounces
MINUTES_IN_HOUR = 60            # 60 Minutes in an hour
MILLIS_IN_MINUTE = 60000         # 60000 ms in a minute
EVENT_PIN = 4             # The pin that will send out an event notification
SERIAL_DEBUG = 1             # Set to 1 to have statements printed to the monitor
PERSIST_TO_DB = True         # Set to True to persist readings to database

# Create objects
scale = ADS1232(5, 6, 21)
lcd = lcddriver()
dbSession = None

# Global variables
lastBrewTime = 0
latestRecordedWeight = 0.0
ipCommand = "hostname -I | cut -d\' \' -f1"
ipAddress = ""
fullBrew = True


def setup():
    global dbSession, ipAddress

    # LCD Stuff
    print("Setting up LCD...")
    lcd.lcd_clear()
    lcd.lcd_display_string("Please Wait...", 1)
    printIP()

    # Scale Stuff
    print("Setting up scale...")
    scale.set_reading_format("MSB", "MSB")
    scale.set_reference_unit(21)
    scale.reset()
    time.sleep(1.0)     # Small delay for settling
    scale.tare()           # Reset the scale to 0

    # Database Stuff
    print("Setting up database...")
    if PERSIST_TO_DB:
        Base = declarative_base()
        engine = db.create_engine('mysql+mysqldb://adminuser:adminPa$$word1!@localhost/coffee_scale')
        session = sessionmaker()
        session.configure(bind=engine)
        Base.metadata.create_all(engine)
        dbSession = session()

    # Setup the scale
    print("Initializing Coffee Monitor...")
    initScale()
    GPIO.setup(EVENT_PIN, GPIO.OUT)


def cleanAndExit():
    print("Cleaning...")
    GPIO.cleanup()

    print("Bye!")
    sys.exit()


def initScale():
    global ipAddress
    # Ready
    lcd.lcd_clear()
    lcd.lcd_display_string("Ready", 1)
    lcd.lcd_display_string("Add container", 2)

    # Wait for scale to have weight added to it.
    while getScaleReading() < 3.0:
        printIP()

        time.sleep(1.0)


# *******************************************************************************************************
# *******************************************************************************************************
# ************************************ State Functions **************************************************
# *******************************************************************************************************
# *******************************************************************************************************

def getAgeString():
    global lastBrewTime
    # Ugly hack
    if lastBrewTime == 0:
        lastBrewTime = millis()
    minutes = (millis() - lastBrewTime) / MILLIS_IN_MINUTE

    # Compute the hours
    strHours = str(int(math.floor(minutes / MINUTES_IN_HOUR))) + "H "

    # Compute the remaining minutes
    strMinutes = str(int(math.floor(minutes % MINUTES_IN_HOUR))) + "M"

    return str(strHours + strMinutes)


def handleCarafeEmpty():
    global ipAddress
    lcd.lcd_clear()
    lcd.lcd_display_string("Empty Container", 1)
    printIP()


def handleCarafeNotEmpty(reading):
    global ipAddress, fullBrew
    # Display the age and cups remaining
    lcd.lcd_clear()
    lcd.lcd_display_string("Age: " + str(getAgeString()), 1)
    lcd.lcd_display_string("Cups Left: " + str(round(getCupsRemaining(reading), 2)) + "" if fullBrew else "*", 2)
    printIP()


def handleEmptyScale():
    global latestRecordedWeight, ipAddress, fullBrew

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
        # if SERIAL_DEBUG > 0:
        #     print("Tare")

        printIP()

        # TODO: Need more data to determine whether taring here is a good idea
        # Taking out the tare, on two occasions it "tared" with the weight on it due to delays
        # scale.tare()
        time.sleep(2.0)

    # Now that the scale isn't empty, determine if more coffee was added (at least one cup)
    if latestRecordedWeight > previousWeight + FULL_CUP:
        # If the weight is within two cups of HALF_CARAFE then assume a half brew
        # TODO: This weight needs to be double checked (half brew may not literally be a half brew)
        if HALF_CARAFE - FULL_CUP < latestRecordedWeight - previousWeight < HALF_CARAFE + FULL_CUP:
            fullBrew = False
        else:
            fullBrew = True
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
    global latestRecordedWeight, s
    # Keep taking readings one second apart until they are within 1 ounce of each other (indicating stability)
    # This should ensure a reading isn't taken while weight is added or removed from the scale
    firstReading = 0
    secondReading = 10
    while abs(firstReading - secondReading) >= 1:
        printIP()

        firstReading = abs(scale.get_weight(NUM_READINGS)) / GRAMS_PER_OZ
        # Delay between readings
        time.sleep(1.0)
        secondReading = abs(scale.get_weight(NUM_READINGS)) / GRAMS_PER_OZ

        if PERSIST_TO_DB:
            # Insert the record into the database
            # TODO: Need to do multi-reading commits to save on time
            reading = WeightReading()
            reading.value = firstReading
            dbSession.add(reading)
            dbSession.commit()

    if SERIAL_DEBUG > 0:
        print("Reading is " + str(round(secondReading, 2)))

    # If the scale isn't empty, record the last weight
    if not scaleIsEmpty(secondReading):
        latestRecordedWeight = secondReading

    return secondReading


def printIP():
    global ipCommand, ipAddress
    # Check for an IP address (for debugging)
    ipAddress = subprocess.check_output(ipCommand, shell=True).decode("utf-8").strip()
    if ipAddress:
        lcd.lcd_display_string("IP: " + ipAddress, 4)


def main():
    global ipCommand, ipAddress

    try:
        setup()

        while True:
            # Take a reading
            reading = getScaleReading()

            # Check for an IP address (for debugging)
            ipAddress = subprocess.check_output(ipCommand, shell=True).decode("utf-8").strip()

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

            # Take some time between refreshes
            time.sleep(2.0)

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()


if __name__ == "__main__":
    main()
