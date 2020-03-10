import logging
import math
import subprocess
import sys
import time

import requests

sys.path.append('/home/pi/repos/python/coffee_monitor_site/app/lib')

import RPi.GPIO as GPIO
import sqlalchemy as db
from lib.ads1232 import ADS1232
from lib.lcddriver import lcd as lcddriver
from models import WeightReading, ScaleOffsetRecording
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Config
GRAMS_PER_OZ = 28.35            # Grams to Oz conversion factor
NUM_READINGS = 21               # Number of readings to take on the scale, we then take the median reading
FULL_CUP = 10                   # A full cup is about 10 ounces
SPLATTER_POINT = 73             # At this point you'll get splatter, and empty carafe is actually 69.25oz
EMPTY_CARAFE = 69               # An empty carafe is about 69.25oz
FULL_CARAFE = 150               # A full carafe is about 150oz
EMPTY_SCALE_THRESHOLD = 10      # Assume the scale is empty at 10 ounces or less
MINUTES_IN_HOUR = 60            # 60 Minutes in an hour
MILLIS_IN_MINUTE = 60000        # 60000 ms in a minute
PERSIST_TO_DB = True            # Set to True to persist readings to database

# Global variables
lastBrewTime = 0
latestRecordedWeight = 0.0
ipCommand = "hostname -I | cut -d\' \' -f1"
logging.basicConfig(filename='/home/pi/repos/python/coffee_monitor_site/app/application.log', level=logging.INFO)
isLCD = True

# Create objects
scale = ADS1232(5, 6, 21)
try:
    lcd = lcddriver()
except OSError:
    logging.info(str(datetime.now()) + ": " + "Failed to initialize LCD")
    isLCD = False
dbSession = None


def setup():
    global dbSession

    # LCD Stuff
    logging.debug(str(datetime.now()) + ": " + "Setting up LCD...")
    printToLCD("Please Wait...")

    # Scale Stuff
    logging.debug(str(datetime.now()) + ": " + "Setting up scale...")
    scale.set_reading_format("MSB", "MSB")
    scale.set_reference_unit(21)
    scale.reset()
    time.sleep(1.0)     # Small delay for settling
    scale.tare()           # Reset the scale to 0

    # Database Stuff
    logging.debug(str(datetime.now()) + ": " + "Setting up database...")
    if PERSIST_TO_DB:
        engine = db.create_engine('mysql+mysqldb://adminuser:adminPa$$word1!@localhost/coffee_scale')
        session = sessionmaker()
        session.configure(bind=engine)
        dbSession = session()

    # Log the offset reading
    if PERSIST_TO_DB:
        reading = ScaleOffsetRecording()
        reading.value = scale.get_offset()
        dbSession.add(reading)
        dbSession.commit()

    # Setup the scale
    logging.info(str(datetime.now()) + ": " + "Initializing Coffee Monitor...")
    initScale()


def cleanAndExit():
    logging.info(str(datetime.now()) + ": " + "Cleaning up...")
    GPIO.cleanup()

    logging.info("Goodbye")
    sys.exit()


def initScale():
    # Ready
    printToLCD("Ready", "Add container")

    # Wait for scale to have weight added to it.
    while getScaleReading() < 3.0:
        # This will just update the IP address
        printToLCD("", "", "", "", False)

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
    printToLCD("Empty Container")


def handleCarafeNotEmpty(reading):
    # Display the age and cups remaining
    printToLCD("Age: " + str(getAgeString()), "Cups Left: " + str(round(getCupsRemaining(reading), 2)))


def handleEmptyScale():
    global latestRecordedWeight

    # Either there is a new brew coming or someone simply lifted the carafe temporarily, record the previous weight
    previousWeight = latestRecordedWeight

    # While the scale is empty, display that we're waiting for more coffee
    printToLCD("Waiting for", "next brew")

    # NOTE: By using scaleIsEmpty, technically any weight can be added to leave this state
    #       which may be undesirable but for now I like it this way. In the future I may
    #       change this to while reading is less than empty carafe so it doesn't show
    #       negative cups
    while scaleIsEmpty(getScaleReading()):
        # if SERIAL_DEBUG > 0:
        #     print("Tare")

        # This will just update the IP address
        printToLCD("", "", "", "", False)

        # TODO: Need more data to determine whether taring here is a good idea
        # Taking out the tare, on two occasions it "tared" with the weight on it due to delays
        # scale.tare()
        time.sleep(2.0)

    # Now that the scale isn't empty, determine if more coffee was added
    if latestRecordedWeight > previousWeight + FULL_CUP:
        # If the new wight is at least one more cup of coffee more than the old, assume a new brew
        handleFreshBrew()


def handleFreshBrew():
    global lastBrewTime

    # Update the last brew time
    lastBrewTime = millis()

    # Notify Slack
    pingSlack()


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
        # This will just update the IP address
        printToLCD("", "", "", "", False)

        # Added this in the hopes that it fixes the random bad readings. The problem
        # is that occasionally I will see the scale just go haywire and from that
        # point forward, the readings are useless. I'm assuming it's because somehow
        # the bit triggers are off so I'm hoping resetting the device avoids this.
        scale.reset()

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

    logging.debug(str(datetime.now()) + ": " + "Reading is " + str(round(secondReading, 2)))

    # If the scale isn't empty, record the last weight
    if not scaleIsEmpty(secondReading):
        latestRecordedWeight = secondReading

    return secondReading


def printToLCD(line1="", line2="", line3="", line4="", clearScreen=True):
    global ipCommand

    # Check if the LCD is initialized
    if not isLCD:
        return

    if clearScreen:
        lcd.lcd_clear()

    lcd.lcd_display_string(line1, 1)
    lcd.lcd_display_string(line2, 2)
    lcd.lcd_display_string(line3, 3)

    # If there is no line 4 provided, add the IP address (if there is one) for debugging
    if not line4:
        ipAddress = subprocess.check_output(ipCommand, shell=True).decode("utf-8").strip()
        if ipAddress:
            lcd.lcd_display_string("IP: " + ipAddress, 4)
    else:
        lcd.lcd_display_string(line4, 4)


def pingSlack():
    url = "https://hooks.slack.com/services/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"
    message = "{'text': 'There is fresh coffee! :coffee::coffee:'}"

    response = requests.post(url, json=message, headers={"Content-Type": "application/json"})

    logging.debug(str(datetime.now()) + ": " + "Slack Message Sent: " + str(response.status_code))


def main():
    global ipCommand

    try:
        setup()

        while True:
            # Take a reading
            reading = getScaleReading()

            # Determine the state
            if scaleIsEmpty(reading):
                logging.debug(str(datetime.now()) + ": " + "STATE: Scale is Empty")
                handleEmptyScale()
            elif carafeIsEmpty(reading):
                logging.debug(str(datetime.now()) + ": " + "STATE: Carafe is Empty")
                handleCarafeEmpty()
            elif not (carafeIsEmpty(reading)):
                logging.debug(str(datetime.now()) + ": " + "STATE: Carafe is NOT Empty")
                handleCarafeNotEmpty(reading)

            # Take some time between refreshes
            time.sleep(2.0)

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()


if __name__ == "__main__":
    main()
