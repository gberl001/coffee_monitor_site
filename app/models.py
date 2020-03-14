from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class WeightReading(Base):
    __tablename__ = 'weight_reading'
    __bind_key__ = 'coffee_scale'

    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, default=datetime.now)
    value = Column(DECIMAL(13, 4), nullable=False)

    def reading(self):
        return int(self.value)

    def __repr__(self):
        return "WeightReading(%r, %r)" % (
            self.datetime, self.value)


class Event(Base):
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


class ScaleOffsetRecording(Base):
    __tablename__ = 'scale_offset_recording'
    __bind_key__ = 'coffee_scale'

    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, default=datetime.now)
    value = Column(DECIMAL(9, 4), nullable=False)

    def reading(self):
        return int(self.value)

    def __repr__(self):
        return "ScaleOffsetRecording(%r, %r)" % (
            self.datetime, self.value)


class DetectedEvent(Base):
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


class Carafe(Base):
    __tablename__ = 'carafe'
    __bind_key__ = 'coffee_scale'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    splatter_point = Column(DECIMAL(5, 2), nullable=False)
    empty_weight = Column(DECIMAL(5, 2), nullable=False)
    full_weight = Column(DECIMAL(5, 2), nullable=False)

    def __repr__(self):
        return "Carafe(%r, %r, %r, %r)" % (
            self.name, self.splatter_point, self.empty_weight, self.full_weight)


class Scale(Base):
    __tablename__ = 'scale'
    __bind_key__ = 'coffee_scale'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    full_cup_weight = Column(DECIMAL(5, 2), nullable=False)
    empty_scale_threshold = Column(DECIMAL(5, 2), nullable=False)

    def __repr__(self):
        return "Scale(%r, %r, %r)" % (
            self.name, self.full_cup_weight, self.empty_scale_threshold)