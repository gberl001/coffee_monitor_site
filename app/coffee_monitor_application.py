import enum
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
from models import WeightReading, ScaleOffsetRecording, Event, DetectedEvent, Carafe, Scale
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from decimal import Decimal

# Config
GRAMS_PER_OZ = 28.35            # Grams to Oz conversion factor
NUM_READINGS = 21               # Number of readings to take on the scale, we then take the median reading
MINUTES_IN_HOUR = 60            # 60 Minutes in an hour
MILLIS_IN_MINUTE = 60000        # 60000 ms in a minute
PERSIST_TO_DB = True            # Set to True to persist readings to database


class State(enum.Enum):
    emptyScale = 1
    emptyCarafe = 2
    nonEmptyCarafe = 3
    freshBrew = 4


# Global variables
lastBrewTime = 0
latestRecordedWeight = 0.0
ipCommand = "hostname -I | cut -d\' \' -f1"
logging.basicConfig(filename='/home/pi/repos/python/coffee_monitor_site/app/application.log', level=logging.ERROR)
isLCD = True

# Create objects
scaleSensor = ADS1232(5, 6, 21)
try:
    lcd = lcddriver()
except OSError:
    logging.info(str(datetime.now()) + ": " + "Failed to initialize LCD")
    isLCD = False
dbSession = None

# Global variables
lastBrewTime = 0
latestRecordedWeight = 0.0
ipCommand = "hostname -I | cut -d\' \' -f1"
currentState = State.emptyCarafe    # Start with non-empty scale so it initially records empty scale
logging.basicConfig(filename='application.log', level=logging.INFO)
scale = None
carafe = None


def setup():
    global dbSession, carafe, scale

    # LCD Stuff
    logging.debug(str(datetime.now()) + ": " + "Setting up LCD...")
    printToLCD("Please Wait...")

    # Scale Stuff
    logging.debug(str(datetime.now()) + ": " + "Setting up scale...")
    scaleSensor.set_reading_format("MSB", "MSB")
    scaleSensor.set_reference_unit(21)
    scaleSensor.reset()
    time.sleep(1.0)     # Small delay for settling
    scaleSensor.tare()           # Reset the scale to 0

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
        reading.value = scaleSensor.get_offset()
        dbSession.add(reading)
        dbSession.commit()

    # Load the scale and carafe objects
    carafe = dbSession.query(Carafe).filter(Carafe.name == 'Home').first()
    scale = dbSession.query(Scale).filter(Scale.name == 'PTC').first()

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
    global currentState

    # Record the event in the database
    if PERSIST_TO_DB and currentState != State.emptyCarafe:
        emptyCarafeEvent = dbSession.query(Event).filter(Event.name == 'Empty Carafe').first()
        emptyCarafe = DetectedEvent()
        emptyCarafe.event = emptyCarafeEvent
        dbSession.add(emptyCarafe)
        dbSession.commit()

    currentState = State.emptyCarafe

    printToLCD("Empty Container")


def handleCarafeNotEmpty(reading):
    global currentState

    # Display the age and cups remaining
    printToLCD("Age: " + str(getAgeString()), "Cups Left: " + str(round(getCupsRemaining(reading), 2)))

    currentState = State.nonEmptyCarafe


def handleEmptyScale():
    global latestRecordedWeight, currentState, scale

    # Either there is a new brew coming or someone simply lifted the carafe temporarily, record the previous weight
    previousWeight = latestRecordedWeight

    # While the scale is empty, display that we're waiting for more coffee
    printToLCD("Waiting for", "next brew")

    # Record the event in the database
    if PERSIST_TO_DB and currentState != State.emptyScale:
        emptyScaleEvent = dbSession.query(Event).filter(Event.name == 'Empty Scale').first()
        emptyScale = DetectedEvent()
        emptyScale.event = emptyScaleEvent
        dbSession.add(emptyScale)
        dbSession.commit()

    currentState = State.emptyScale

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
    if latestRecordedWeight > previousWeight + scale.full_cup_weight:
        # If the new wight is at least one more cup of coffee more than the old, assume a new brew
        handleFreshBrew()


def handleFreshBrew():
    global lastBrewTime, currentState

    # Update the last brew time
    lastBrewTime = millis()

    # Record the event in the database
    if PERSIST_TO_DB and currentState != State.freshBrew:
        fullBrewEvent = dbSession.query(Event).filter(Event.name == 'Full Brew').first()
        newBrew = DetectedEvent()
        newBrew.event = fullBrewEvent
        dbSession.add(newBrew)
        dbSession.commit()

    # Notify Slack
    pingSlack()

    currentState = State.freshBrew


# *******************************************************************************************************
# *******************************************************************************************************
# *********************************** Utility Functions *************************************************
# *******************************************************************************************************
# *******************************************************************************************************

def millis():
    return int(round(time.time() * 1000))


def scaleIsEmpty(reading):
    global scale
    return reading < scale.empty_scale_threshold


def carafeIsEmpty(reading):
    global carafe
    # If the reading is between empty and where the coffee splatters...
    return carafe.empty_weight <= reading <= carafe.splatter_point


def getCupsRemaining(reading):
    global carafe, scale
    return (Decimal(reading) - carafe.splatter_point) / scale.full_cup_weight


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
        scaleSensor.reset()

        firstReading = abs(scaleSensor.get_weight(NUM_READINGS)) / GRAMS_PER_OZ
        # Delay between readings
        time.sleep(1.0)
        secondReading = abs(scaleSensor.get_weight(NUM_READINGS)) / GRAMS_PER_OZ

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
    message = {'text': 'There is fresh coffee! :coffee::coffee:'}
    response = 0

    try:
        response = requests.post(url, json=message, headers={"Content-Type": "application/json"})
    except requests.exceptions.HTTPError as e:
        logging.error(str(datetime.now()) + ": " + "Slack ping failed", e)
    except requests.exceptions.Timeout as e:
        logging.error(str(datetime.now()) + ": " + "Slack ping failed", e)
    except requests.exceptions.TooManyRedirects as e:
        logging.error(str(datetime.now()) + ": " + "Slack ping failed", e)
    except requests.exceptions.RequestException as e:
        logging.error(str(datetime.now()) + ": " + "Slack ping failed", e)
    except:
        logging.error(str(datetime.now()) + ": " + "Slack ping failed for unhandled exception")

    if response.status_code != 200:
        logging.error(str(datetime.now()) + ": " + "Slack Message Failed, HTTP code: " + str(response.status_code))
    else:
        logging.debug(str(datetime.now()) + ": " + "Slack Message successfully sent")


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
