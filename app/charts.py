from flask_appbuilder import DirectByChartView
from flask_appbuilder.models.sqla.interface import SQLAInterface

from app import appbuilder
from app.models import WeightReading


class ScaleChart(DirectByChartView):
    datamodel = SQLAInterface(WeightReading)
    chart_title = 'Coffee Scale Readings'
    chart_type = 'LineChart'
    legend = 'Weight'

    definitions = [
        {
            'label': 'Weight',
            'group': 'value',
            'series': ['value']
        }
    ]


appbuilder.add_view(ScaleChart, "Coffee Scale Readings", icon="fa-folder-open-o", category="Charts")
