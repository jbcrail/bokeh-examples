#!/usr/bin/env python

from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep

import argparse
import calendar
import csv
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
    if month is None:
        months = range(1, 13)
    else:
        months = [month]
    dates = []
    for m in months:
        if day is None:
            for d in xrange(1, calendar.monthrange(year, m)[1]+1):
                if datetime(year, m, d) <= today:
                    dates.append("{0:02d}-{1:02d}-{2:02d}".format(year, m, d))
        elif datetime(year, m, day) <= today:
            dates.append("{0:02d}-{1:02d}-{2:02d}".format(year, m, day))
    return dates

def has_data(cursor, airport, date):
    cursor.execute("SELECT COUNT(*) FROM weather WHERE airport=? AND date=?", (airport, date))
    (number_of_rows,) = cursor.fetchone()
    return number_of_rows == 6

def save_data(cursor, airport, date, key, value):
    cursor.execute("INSERT OR IGNORE INTO weather VALUES (?, ?, ?, ?)", (airport, date, key, value))

def cache(args):
    with sqlite3.connect(args.database) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS weather (airport text, date text, key text, value numeric, UNIQUE(airport, date, key) ON CONFLICT IGNORE)")
        for date in get_valid_date_range(args.year, args.month, args.day):
            continue
            if not has_data(c, args.airport, date):
                print "Retrieving weather for {0} on {1}".format(args.airport, date)
                statistics = get_temperatures(args.airport, date)
                for key, value in statistics.items():
                    save_data(c, args.airport, date, key, value)
                conn.commit()
                if not args.no_sleep:
                    sleep(random.randint(5, 10))

def export(args):
    stats = {}
    with sqlite3.connect(args.database) as conn:
        c = conn.cursor()
        for row in c.execute("SELECT airport, date, key, value FROM weather"):
            key = (row[0], row[1])
            if key not in stats:
                stats[key] = {}
            stats[key][row[2]] = row[3]
    statistics = ['actual_max_temp', 'average_max_temp', 'record_max_temp', 'actual_min_temp', 'average_min_temp', 'record_min_temp']
    writer = csv.writer(sys.stdout)
    writer.writerow(['airport', 'date'] + statistics)
    for key in stats.keys():
        writer.writerow(list(key) + [stats[key][k] for k in statistics])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='wunderground')
    subparsers = parser.add_subparsers(help='sub-command help')

    cache_parser = subparsers.add_parser('cache', help='cache weather statistics')
    cache_parser.add_argument('airport', type=str)
    cache_parser.add_argument('year', nargs='?', type=int)
    cache_parser.add_argument('month', nargs='?', type=int)
    cache_parser.add_argument('day', nargs='?', type=int)
    cache_parser.add_argument('-n', '--no-sleep', action='store_true', help='')
    cache_parser.add_argument('-d', '--database', metavar='DB', type=str, default='wunderground.db', help='SQLite database to store statistics')
    cache_parser.set_defaults(func=cache)

    export_parser = subparsers.add_parser('export', help='export cached weather statistics to CSV')
    export_parser.add_argument('-d', '--database', metavar='DB', type=str, default='wunderground.db', help='SQLite database to get statistics')
    export_parser.set_defaults(func=export)

    args = parser.parse_args(sys.argv[1:])
    args.func(args)
