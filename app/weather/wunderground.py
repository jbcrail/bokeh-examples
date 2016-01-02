from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep

import calendar
import random
import re
import sqlite3
import sys
import urllib2

def get_temperatures(airport, date):
    url = 'http://www.wunderground.com/history/airport/{0}/{1}/DailyHistory.html'.format(airport, date.replace('-', '/'))

    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    html = response.read()
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find(id="historyTable")

    temperatures = {}
    for row in table.find_all('tr'):
        weather_data = [span.text for span in row.find_all('span')]
        if weather_data and "Max Temperature" in weather_data[0]:
            data = [re.sub(r'[^\-0-9]+', '', data) for data in weather_data if data]
            temperatures['actual-max-temp'] = int(data[2])
            temperatures['average-max-temp'] = int(data[5])
            temperatures['record-max-temp'] = int(data[8])
        elif weather_data and "Min Temperature" in weather_data[0]:
            data = [re.sub(r'[^\-0-9]+', '', data) for data in weather_data if data]
            temperatures['actual-min-temp'] = int(data[2])
            temperatures['average-min-temp'] = int(data[5])
            temperatures['record-min-temp'] = int(data[8])
    return temperatures

def get_valid_date_range(year, month, day):
    today = datetime.now()
    if year is None:
        year = today.year
    else:
        year = int(year)
    if month is None:
        months = range(1, 13)
    else:
        months = [int(month)]
    dates = []
    for m in months:
        if day is None:
            for d in xrange(1, calendar.monthrange(year, m)[1]+1):
                if datetime(year, m, d) <= today:
                    dates.append("{0:02d}-{1:02d}-{2:02d}".format(year, m, d))
        elif datetime(year, m, int(day)) <= today:
            dates.append("{0:02d}-{1:02d}-{2:02d}".format(year, m, int(day)))
    return dates

def has_data(cursor, airport, date):
    cursor.execute("SELECT COUNT(*) FROM weather WHERE airport=? AND date=?", (airport, date))
    (number_of_rows,) = cursor.fetchone()
    return number_of_rows == 6

def save_data(cursor, airport, date, key, value):
    cursor.execute("INSERT OR IGNORE INTO weather VALUES (?, ?, ?, ?)", (airport, date, key, value))

if __name__ == '__main__':
    airport, year, month, day = zip(*map(None, sys.argv[1:], xrange(4)))[0]
    if airport is None:
        print "Please supply a valid airport code"
        sys.exit(1)
    conn = sqlite3.connect('wunderground.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS weather (airport text, date text, key text, value numeric, UNIQUE(airport, date, key) ON CONFLICT IGNORE)")
    for date in get_valid_date_range(year, month, day):
        if not has_data(c, airport, date):
            print "Retrieving weather for {0} on {1}".format(airport, date)
            statistics = get_temperatures(airport, date)
            for key, value in statistics.items():
                save_data(c, airport, date, key, value)
            conn.commit()
            sleep(random.randint(5, 10))
    conn.close()
