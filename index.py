# /usr/bin/env python
# Copyright 2014-2015 Boundary, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from datetime import timedelta, datetime
import socket
import sys
import time
import json
import requests
from requests.packages import urllib3
import unicodedata

hostname = socket.gethostname()

def msToTime(ms):
    s = float(ms) / 1000000
    return int(s)  # datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S.%f')

def getmillis(year, month, day, hour, min, sec):
    return int(datetime(year, month, day, hour, min, sec).strftime("%s")) * 1000

def netcat(hostname, port, content):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))
    if sys.version_info >= (3, 0, 0):
        s.sendall(bytes(content, 'UTF-8'))
    else:
        s.sendall(content)
    s.shutdown(socket.SHUT_WR)
    # print "Connection closed."
    s.close()


def send_event(title, message, type, tags=None):
    tags = tags or ''
    event = {'data': '_bevent:{0}|m:{1}|t:{2}|tags:{3}'.format(title, message, type, tags)}

    payload = {
        "method": "event",
        "params": event,
        "jsonrpc": "2.0",
        "id": 1
    }
    netcat("localhost", 9192, json.dumps(payload))


def send_measurement(name, value, source, timestamp=''):
    data_str = '_bmetric:{0}|v:{1}|s:{2}'.format(name, value, source)

    if timestamp is not '':
        data_str = data_str + '|t:{0}'.format(timestamp)

    data = {'data': data_str}
    payload = {
        "method": "metric",
        "params": data,
        "jsonrpc": "2.0",
        "id": 1
    }
    netcat("localhost", 9192, json.dumps(payload))

def getDataTimes(dataInput):
    if ('point' in dataInput):
        points = dataInput['point']

        startMilliseconds = 0
        endMilliseconds = 0
        for point in points:
            if startMilliseconds < point['startTimeNanos']:
                startMilliseconds = point['startTimeNanos']
            if endMilliseconds < point['endTimeNanos']:
                endMilliseconds = point['endTimeNanos']
    return (len(points), msToTime(startMilliseconds), msToTime(endMilliseconds))


class Fitness():
    """Implements a meter plugin that gets current stock price and volume"""

    def load_parameters(self):
        """ Reads the meter plugin runtime parameters"""
        json_data = open("param.json")
        data = json.load(json_data)
        self.items = data["items"]
        self.pollInterval = self.items[0]['poll_interval']

    def send_event(self, title, message, type, timestamp):
        sys.stdout.write('_bevent:{0}|m:{1}|t:{2}\n'.format(title, message, type, timestamp).decode('utf-8'))
        sys.stdout.flush()

    def sendMeasurement(self, metric, value, source, timestamp=None):
        """ Sends measurements to standard out to be read by plugin manager"""
        sys.stdout.write('{0} {1} {2} {3}\n'.format(metric, value, source, timestamp).decode('utf-8'))
        sys.stdout.flush()

    def getRefreshedAccessToken(self, url, client_id, client_secret, refresh_token, grant_type):

        form = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": grant_type
        }
        response = requests.post(url, form)
        obj = json.loads(response.content)
        accessToken = obj["access_token"]
        return accessToken

    def run(self):
        """Plugin main loop"""
        self.load_parameters()
        self.send_event("Plugin started", "Starting fitness plugin", "info", int(time.time()))
        while True:
            # Loop over the items and lookup the fitness data
            for i in self.items:
                client_id = i['client_id']
                client_secret = i['client_secret']
                refresh_token = i['refresh_token']
                url = "https://accounts.google.com/o/oauth2/token"
                grant_type = "refresh_token"

                access_token = self.getRefreshedAccessToken(url, client_id, client_secret, refresh_token, grant_type)

                today = datetime.utcnow().date()
                today_ns = int(today.strftime("%s")) * 1000 * 1000000

                tomorrow = today + timedelta(1)
                tomorrow_ns = int(tomorrow.strftime("%s")) * 1000 * 1000000
                time_window = str(0) + "-" + str(tomorrow_ns)

                data_sources = get_information_source_list(access_token)
                source_list = get_summaries_for_data_sources(data_sources, time_window, access_token)
                for i in range(len(source_list)):
                    ds_str = unicodedata.normalize('NFKD', source_list[i]).encode('ascii', 'ignore')
                    start_times, values = extract_data(source_list[i], access_token, time_window)
                    if ("merge_heart_rate_bpm" in ds_str):
                        for indx in range(len(start_times)):
                            send_measurement('GOOGLE_FIT_MERGE_HEART_RATE_BPM', str(values[indx][0]), "MyFitness", start_times[indx])
                            # self.sendMeasurement('GOOGLE_FIT_MERGE_HEART_RATE_BPM', str(values[indx][0]), "MyFitness", start_times[indx])
                    elif ("merge_step_deltas" in ds_str):
                        daily_steps_total = 0
                        current_date = datetime.fromtimestamp(start_times[0] / 1000).date()
                        for indx in range(len(start_times)):
                            send_measurement('GOOGLE_FIT_MERGE_STEP_DELTAS', str(values[indx][0]), "MyFitness", start_times[indx])
                            date = datetime.fromtimestamp(start_times[indx] / 1000).date()
                            if(current_date != date):
                                send_measurement('GOOGLE_FIT_MERGE_STEP', str(daily_steps_total), "MyFitness", getmillis(current_date.year, current_date.month, current_date.day, 23, 59, 59))
                                current_date = date
                                daily_steps_total = 0
                            elif(indx == len(start_times) - 1):
                                daily_steps_total += int(values[indx][0])
                                send_measurement('GOOGLE_FIT_MERGE_STEP', str(daily_steps_total), "MyFitness", getmillis(date.year, date.month, date.day, 23, 59, 59))
                            else:
                                daily_steps_total += int(values[indx][0])
            time.sleep(self.pollInterval / 1000)


def get_information_source_list(accessToken):
    get_datasource_url_tmpl = 'https://www.googleapis.com/fitness/v1/users/me/dataSources?access_token=<accessToken>'
    get_datasource_url = get_datasource_url_tmpl.replace('<accessToken>', accessToken)
    response = requests.get(get_datasource_url)
    all_sources = json.loads(response.content)
    data_sources = []
    for source_list in all_sources['dataSource']:
        data_sources.append(source_list['dataStreamId'])
    return data_sources


def extract_data(dataSource, accessToken, timeWindow):
    get_dataset_url_tmpl = 'https://www.googleapis.com/fitness/v1/users/me/dataSources/<dataSource>/datasets/<timeWindow>' + \
                           '?access_token=<accessToken>'

    get_dataset_url = get_dataset_url_tmpl \
        .replace('<accessToken>', accessToken) \
        .replace('<dataSource>', dataSource) \
        .replace('<timeWindow>', timeWindow)
    response = requests.get(get_dataset_url)
    dataInput = json.loads(response.content)

    if('point' in dataInput):
	points = dataInput['point']

    	start_times = []
    	start_milliseconds = []
    	end_times = []
    	end_milliseconds = []
    	keys = []
    	values = []
    	for point in points:
            start_milliseconds.append(point['startTimeNanos'])
            start_times.append(msToTime(point['startTimeNanos']))
            end_milliseconds.append(point['endTimeNanos'])
            end_times.append(msToTime(point['endTimeNanos']))
            key = []
            value = []
            for i in range(len(point['value'])):
            	key.append(point['value'][i].keys()[0])
            	value.append(point['value'][i].values()[0])
            if len(keys) == 0:
            	keys = key
            values.append(value)

    return (start_times, values)


def get_summaries_for_data_sources(dataSources, timeWindow, accessToken):
    get_summaries_url_tmpl = "https://www.googleapis.com/fitness/v1/users/me/dataSources/<dataSource>/datasets/<timeWindow>?access_token=<accessToken>"
    nPoints = []
    sourceList = []
    lastBeginTime = []
    lastEndTime = []
    for dSource in dataSources:
        dsStr = unicodedata.normalize('NFKD', dSource).encode('ascii', 'ignore')
        if ("merge_heart_rate_bpm" in dsStr or "merge_step_deltas" in dsStr):
            get_summaries_url = get_summaries_url_tmpl.replace('<accessToken>', accessToken) \
                .replace('<dataSource>', dSource) \
                .replace('<timeWindow>', timeWindow)
            try:
                response = requests.get(get_summaries_url)
                dataInput = json.loads(response.content)
                nP, lastBegin, lastEnd = getDataTimes(dataInput)
                nPoints.append(nP)
                lastBeginTime.append(lastBegin)
                lastEndTime.append(lastEnd)
                sourceList.append(dSource)
            except:
                doNothing = True
    return sourceList


if __name__ == "__main__":
    urllib3.disable_warnings()
    plugin = Fitness()
    plugin.run()
