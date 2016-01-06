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
        if not weather_data:
            continue
        data = [re.sub(r'[^\-0-9]+', '', data) for data in weather_data if data]
        if "Max Temperature" in weather_data[0]:
            temperatures['actual_max_temp'] = int(data[2])
            temperatures['average_max_temp'] = int(data[5])
            temperatures['record_max_temp'] = int(data[8])
        elif "Min Temperature" in weather_data[0]:
            temperatures['actual_min_temp'] = int(data[2])
            temperatures['average_min_temp'] = int(data[5])
            temperatures['record_min_temp'] = int(data[8])
        elif "Precipitation" in weather_data[0]:
            temperatures['actual_precipitation'] = int(data[2])
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
    return number_of_rows == 7

def save_data(cursor, airport, date, key, value):
    cursor.execute("INSERT OR IGNORE INTO weather VALUES (?, ?, ?, ?)", (airport, date, key, value))

def cache(args):
    with sqlite3.connect(args.database) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS weather (airport text, date text, key text, value numeric, UNIQUE(airport, date, key) ON CONFLICT IGNORE)")
        for date in get_valid_date_range(args.year, args.month, args.day):
            if args.force or not has_data(c, args.airport, date):
                print "Retrieving weather for {0} on {1}".format(args.airport, date)
                statistics = get_temperatures(args.airport, date)
                for key, value in statistics.items():
                    save_data(c, args.airport, date, key, value)
                if not args.nop:
                    conn.commit()
                if not args.no_sleep:
                    sleep(random.randint(5, 10))

def export(args):
    with sqlite3.connect(args.database) as conn:
        writer = csv.writer(sys.stdout)
        sql = '''SELECT
            airport, date,
            MAX(CASE WHEN key='actual_max_temp'      THEN value END) actual_max_temp,
            MAX(CASE WHEN key='average_max_temp'     THEN value END) average_max_temp,
            MAX(CASE WHEN key='record_max_temp'      THEN value END) record_max_temp,
            MAX(CASE WHEN key='actual_min_temp'      THEN value END) actual_min_temp,
            MAX(CASE WHEN key='average_min_temp'     THEN value END) average_min_temp,
            MAX(CASE WHEN key='record_min_temp'      THEN value END) record_min_temp,
            MAX(CASE WHEN key='actual_precipitation' THEN value END) actual_precipitation
            FROM weather
            GROUP BY airport, date
        '''
        cursor = conn.execute(sql)
        writer.writerow([d[0] for d in cursor.description])
        for row in cursor.execute(sql):
            writer.writerow(row)

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
    cache_parser.add_argument('-f', '--force', action='store_true', help='force data to be cached')
    cache_parser.add_argument('--nop', action='store_true', help='do not commit the cached data')
    cache_parser.set_defaults(func=cache)

    export_parser = subparsers.add_parser('export', help='export cached weather statistics to CSV')
    export_parser.add_argument('-d', '--database', metavar='DB', type=str, default='wunderground.db', help='SQLite database to get statistics')
    export_parser.set_defaults(func=export)

    args = parser.parse_args(sys.argv[1:])
    args.func(args)
