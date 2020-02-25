from datetime import datetime

from flask_appbuilder import Model
from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship


class WeightReading(Model):
    __tablename__ = 'weight_reading'
    __bind_key__ = 'coffee_scale'

    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, default=datetime.now)
    value = Column(Integer, nullable=False)

    def __repr__(self):
        return "WeightReading(%r, %r)" % (
            self.datetime, self.value)


class Event(Model):
    __tablename__ = 'event'
    __bind_key__ = 'coffee_scale'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name.encode("utf8")


class DetectedEvent(Model):
    __tablename__ = 'detected_event'
    __bind_key__ = 'coffee_scale'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
    event = relationship("Event", backref='events')
    datetime = Column(DateTime, default=datetime.now)

    def serialize(self):
        return {
            'id': self.id,
            'event': self.event.serialize(),
            'datetime': self.datetime
        }

    def __repr__(self):
        return "DetectedEvent(%r, %r)" % (
            self.event.serialize(), str(self.datetime))
