from flask import render_template
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView

from . import appbuilder, db

from app.models import WeightReading, Event, DetectedEvent


class EventView(ModelView):
    datamodel = SQLAInterface(Event)

    add_columns = ['name']
    list_columns = ['name']


class DetectedEventView(ModelView):
    datamodel = SQLAInterface(DetectedEvent)

    list_columns = ['event', 'datetime']
    add_columns = list_columns


class WeightReadingView(ModelView):
    datamodel = SQLAInterface(WeightReading)

    list_columns = ['datetime', 'value']


# fa-flask
appbuilder.add_view(WeightReadingView, "Coffee Scale Readings", icon="fa-flask", category="Coffee Monitor")
appbuilder.add_view(EventView, "Events", icon="fa-folder-open-o", category="Coffee Monitor")
appbuilder.add_view(DetectedEventView, "Detected Events", icon="fa-folder-open-o", category="Coffee Monitor")

"""
    Create your Model based REST API::

    class MyModelApi(ModelRestApi):
        datamodel = SQLAInterface(MyModel)

    appbuilder.add_api(MyModelApi)


    Create your Views::


    class MyModelView(ModelView):
        datamodel = SQLAInterface(MyModel)


    Next, register your Views::


    appbuilder.add_view(
        MyModelView,
        "My View",
        icon="fa-folder-open-o",
        category="My Category",
        category_icon='fa-envelope'
    )
"""

"""
    Application wide 404 error handler
"""


@appbuilder.app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )


db.create_all()
