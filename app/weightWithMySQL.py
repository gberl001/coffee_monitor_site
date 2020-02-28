import sys
import time

import RPi.GPIO as GPIO
import sqlalchemy as db
from lib.hx711 import HX711
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from models import WeightReading


def cleanAndExit():
    print("Cleaning...")
    GPIO.cleanup()

    print("Bye!")
    sys.exit()


# Create the device on pins 5 and 6
hx = HX711(5, 6)

# Create a database connection
Base = declarative_base()
engine = db.create_engine('mysql+mysqldb://adminuser:adminPa$$word1!@localhost/coffee_scale')
session = sessionmaker()
session.configure(bind=engine)
Base.metadata.create_all(engine)
s = session()

# I've found out that, for some reason, the order of the bytes is not always the same between versions of python,
# numpy and the hx711 itself, still need to figure out why it changes.
# If you're experiencing super random values, change these values to MSB or LSB until to get more stable values.
# There is some code below to debug and log the order of the bits and the bytes.
# The first parameter is the order in which the bytes are used to build the "long" value.
# The second parameter is the order of the bits inside each byte.
# According to the HX711 datasheet, the second parameter is MSB so you shouldn't need to modify it.
hx.set_reading_format("MSB", "MSB")

# HOW TO CALCULATE THE REFERENCE UNIT
# Set the reference unit to 1. Put 1kg on your sensor or anything you have and know exactly how much it weighs.
# In this case, 92 is 1 gram because, with 1 as a reference unit I got numbers near 0 without any weight
# and I got numbers around 10600 when I added 500g. So, if 500 grams is 10600 then 10600/500 = 21
hx.set_reference_unit(21)

hx.reset()

hx.tare()

print("Tare done! Add weight now...")

while True:
    try:
        # These three lines are useful to debug whether to use MSB or LSB in the reading formats
        # for the first parameter of "hx.set_reading_format("LSB", "MSB")".
        # Comment the two lines "val = hx.get_weight(5)" and "print val" and uncomment these
        # three lines to see what it prints.

        # np_arr8_string = hx.get_np_arr8_string()
        # binary_string = hx.get_binary_string()
        # print binary_string + " " + np_arr8_string

        # Print the weight. Comment if you're debugging the MSB and LSB issue.
        val = abs(hx.get_weight(33))
        print(val)

        # Insert the record into the database
        reading = WeightReading()
        reading.value = val
        s.add(reading)
        s.commit()

        # Not sure if power down and up between readings is necessary
        # hx.power_down()
        # hx.power_up()
        time.sleep(0.1)

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()
