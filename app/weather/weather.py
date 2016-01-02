import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.models import ColumnDataSource, DataRange1d, Range1d, VBox, HBox, Select
from bokeh.plotting import Figure
from scipy.signal import savgol_filter


# Filter for smoothing data originates from http://stackoverflow.com/questions/20618804/how-to-smooth-a-curve-in-the-right-way
def get_dataset(df, name, distribution):
    temps = ['record-min-temp', 'actual-min-temp', 'average-min-temp', 'average-max-temp', 'actual-max-temp', 'record-max-temp']
    df = df[df.airport == name]
    df['date'] = pd.to_datetime(df['date'])
    df = pd.pivot_table(df, index='date', columns=['key'])
    df.columns = [col[1] for col in df.columns.values]
    df = df[temps]
    df.reset_index(inplace=True)
    df.sort_index()
    df['left'] = df.date - pd.DateOffset(days=0.5)
    df['right'] = df.date + pd.DateOffset(days=0.5)
    if distribution == 'Smooth':
        window, order = 51, 3
        for key in temps:
            df[key] = savgol_filter(df[key], window, order)

    return ColumnDataSource(data=dict(
        record_min_temp=df['record-min-temp'],
        record_max_temp=df['record-max-temp'],
        actual_min_temp=df['actual-min-temp'],
        actual_max_temp=df['actual-max-temp'],
        average_min_temp=df['average-min-temp'],
        average_max_temp=df['average-max-temp'],
        left=df['left'],
        right=df['right'],
    ))


def make_plot(source, title):
    plot = Figure(x_axis_type="datetime", plot_width=1000, tools="", toolbar_location=None)
    plot.title = title
    colors = ["#6E4D5B", "#9A9180", "#C3BBA4"]

    plot.quad(top='record_max_temp', bottom='record_min_temp', left='left', right='right', color=colors[2], source=source, legend="Record")
    plot.quad(top='average_max_temp', bottom='average_min_temp', left='left', right='right', color=colors[1], source=source, legend="Average")
    plot.quad(top='actual_max_temp', bottom='actual_min_temp', left='left', right='right', color=colors[0], alpha=0.5, line_color="black", source=source, legend="Actual")

    # fixed attributes
    plot.border_fill_color = "whitesmoke"
    plot.xaxis.axis_label = None
    plot.yaxis.axis_label = "Temperature (F)"
    plot.axis.major_label_text_font_size = "8pt"
    plot.axis.axis_label_text_font_size = "8pt"
    plot.axis.axis_label_text_font_style = "bold"
    plot.x_range = DataRange1d(range_padding=0.0, bounds=None)
    plot.grid.grid_line_alpha = 0.3
    plot.grid[0].ticker.desired_num_ticks = 12

    return plot


# set up callbacks
def update_plot(attrname, old, new):
    city = city_select.value
    plot.title = cities[city]['title']

    src = get_dataset(df, cities[city]['airport'], distribution_select.value)
    for key in ['record_min_temp', 'actual_min_temp', 'average_min_temp', 'average_max_temp', 'actual_max_temp', 'record_max_temp', 'left', 'right']:
        source.data[key] = src.data[key]

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

df = pd.read_csv('2015_weather.csv')
source = get_dataset(df, cities[city]['airport'], distribution)
plot = make_plot(source, cities[city]['title'])

city_select.on_change('value', update_plot)
distribution_select.on_change('value', update_plot)

controls = VBox(city_select, distribution_select)

# add to document
curdoc().add_root(HBox(controls, plot))
