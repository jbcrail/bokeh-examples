from __future__ import division
from os.path import join, dirname

import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.models import ColumnDataSource, DataRange1d, Range1d, VBox, HBox, Select, GridPlot
from bokeh.palettes import Blues4, Greens4
from bokeh.plotting import Figure
from scipy.signal import savgol_filter

STATISTICS = ['record_min_temp', 'actual_min_temp', 'average_min_temp', 'average_max_temp', 'actual_max_temp', 'record_max_temp']

# Filter for smoothing data originates from http://stackoverflow.com/questions/20618804/how-to-smooth-a-curve-in-the-right-way
def get_dataset(src, name, distribution):
    df = src[src.airport == name].copy()
    del df['airport']
    df['date'] = pd.to_datetime(df.date)
    df['left'] = df.date - pd.DateOffset(days=0.5)
    df['right'] = df.date + pd.DateOffset(days=0.5)
    df['actual_precipitation'] = df.actual_precipitation / 100
    df = df.set_index(['date'])
    df.sort_index(inplace=True)
    if distribution == 'Smooth':
        window, order = 51, 3
        for key in STATISTICS:
            df[key] = savgol_filter(df[key], window, order)

    return ColumnDataSource(data=df)


def make_temperature_plot(source, title):
    plot = Figure(x_axis_type="datetime", plot_width=1000, min_border_bottom=0, toolbar_location=None)
    plot.title = title
    colors = Blues4[0:3]

    plot.quad(top='record_max_temp', bottom='record_min_temp', left='left', right='right', color=colors[2], source=source, legend="Record")
    plot.quad(top='average_max_temp', bottom='average_min_temp', left='left', right='right', color=colors[1], source=source, legend="Average")
    plot.quad(top='actual_max_temp', bottom='actual_min_temp', left='left', right='right', color=colors[0], alpha=0.5, line_color="black", source=source, legend="Actual")

    # fixed attributes
    plot.border_fill_color = "whitesmoke"
    plot.xaxis.visible = None
    plot.yaxis.axis_label = "Temperature (F)"
    plot.axis.major_label_text_font_size = "8pt"
    plot.axis.axis_label_text_font_size = "8pt"
    plot.axis.axis_label_text_font_style = "bold"
    plot.x_range = DataRange1d(range_padding=0.0, bounds=None)
    plot.grid.grid_line_alpha = 0.3
    plot.grid[0].ticker.desired_num_ticks = 12

    return plot


def make_precipitation_plot(source):
    plot = Figure(x_axis_type="datetime", plot_width=1000, plot_height=125, min_border_left=50, min_border_right=50, min_border_top=0, min_border_bottom=0, toolbar_location=None)
    plot.title = None

    plot.quad(top='actual_precipitation', bottom=0, left='left', right='right', color=Greens4[1], source=source)

    # fixed attributes
    plot.border_fill_color = "whitesmoke"
    plot.yaxis.axis_label = "Precipitation (in)"
    plot.axis.major_label_text_font_size = "8pt"
    plot.axis.axis_label_text_font_size = "8pt"
    plot.axis.axis_label_text_font_style = "bold"
    plot.x_range = DataRange1d(range_padding=0.0, bounds=None)
    plot.y_range = DataRange1d(range_padding=0.0, bounds=None)
    plot.grid.grid_line_alpha = 0.3
    plot.grid[0].ticker.desired_num_ticks = 12

    return plot


# set up callbacks
def update_plot(attrname, old, new):
    city = city_select.value
    tplot.title = cities[city]['title']

    src = get_dataset(df, cities[city]['airport'], distribution_select.value)
    source.data.update(src.data)

# set up initial data
city = 'Austin'
distribution = 'Discrete'

cities = {
    'Austin': {
        'airport': 'AUS',
        'title': 'Austin, TX',
    },
    'Boston': {
        'airport': 'BOS',
        'title': 'Boston, MA',
    },
    'Seattle': {
        'airport': 'SEA',
        'title': 'Seattle, WA',
    }
}

city_select = Select(value=city, title='City', options=sorted(cities.keys()))
distribution_select = Select(value=distribution, title='Distribution', options=['Discrete', 'Smooth'])

df = pd.read_csv(join(dirname(__file__), 'data/2015_weather.csv'))
source = get_dataset(df, cities[city]['airport'], distribution)
tplot = make_temperature_plot(source, cities[city]['title'])
pplot = make_precipitation_plot(source)

city_select.on_change('value', update_plot)
distribution_select.on_change('value', update_plot)

controls = VBox(city_select, distribution_select)

# add to document
curdoc().add_root(HBox(controls, GridPlot(children=[[tplot], [pplot]], toolbar_location=None), width=1200))
