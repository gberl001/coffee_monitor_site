import sqlalchemy as db
from models import *

engine = db.create_engine('mysql+mysqldb://adminuser:adminPa$$word1!@localhost/coffee_scale')
Base.metadata.create_all(engine)

