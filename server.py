#!/usr/bin/env python3
import json
import logging
import os
import signal
import socket
import sys

from flask import Flask
import requests


app = Flask(__name__)


class ClusterHealthz:
    ''' ClusterHealthz: A module to determine if the Kubernetes cluster is
    happy. The failure domain needs to be determined and preconfigured in
    /config/clusterhealthz.conf

    If any of these failure events occur an 'unhealthy' string is returned as
    an indication of the loss of redundancy.
    '''
    def __init__(self, prometheus_url='service-prometheus.monitoring:9090'):
        logging.info('Starting ClusterHealthz')
        self.prometheus_url = prometheus_url
        self.open_configuration()
        self.status = 'unhealthy'
        self.signal = signal.signal(signal.SIGHUP, self.signal_handler)

    def signal_handler(self, signal, frame):
        ''' This method handles the SIGHUP sent to the PID that this runs
        this server. The SIGHUP signal is sent to indicate to server.py that
        there has been an update in the configuration and it should reload.

        @param signal: The SIGHUP signal number
        @type signal: int
        @param frame: The frame reference of the signal
        @type signal: dict
        '''
        logging.info(
            'SIGHUP Received and handled. Will attempt to reload the alert '
            'configuration'
        )
        self.open_configuration()

    def open_configuration(self, alert_configuration_path=None):
        ''' Attempt to open the configuration file which defines the alerts
        that are considered negative to cluster operation.
        '''
        logging.info('Attempting to open the alert configuration')
        if not alert_configuration_path:
            cwd = os.getcwd()
            alert_configuration_path = cwd + '/config/clusterhealthz.conf'
        try:
            with open(alert_configuration_path, 'r') as config:
                config_contents = config.readlines()
        except FileNotFoundError:
            logging.critical(
                'Could not find the configuration file'
            )
            sys.exit(1)

        self.process_configuration(config_contents)

    def process_configuration(self, config_contents):
        ''' Process the alert file for the alerts that this service should
        check are active.

        @param config_contents: The configuration entities
        @type config_contents: list
        '''
        if not isinstance(config_contents, list):
            logging.critical(
                'Process configuration is expects list but received {}'.format(
                    type(config_contents)
                )
            )
            raise TypeError
        config_contents = [x.strip('\n') for x in config_contents]
        logging.info('Setting cluster critical alarms to: {}'.format(
            config_contents)
        )
        self.alerts = config_contents

    def start(self):
        ''' Start the ClusterHealthz workflow

        Firstly obtain the alerts from Prometheus. If they the query executes
        and a response is received, attempt to JSON serialise the object.
        Then process for alerts that are impacting to the cluster.
        '''
        prometheus_query = self.get_prometheus_alerts()
        if prometheus_query:
            prometheus_alerts_json = self.json_prometheus_response(
                prometheus_query
            )
            if prometheus_alerts_json:
                self.process_prometheus_alerts(prometheus_alerts_json)
        else:
            logging.critical('Could not get alerts from Prometheus')

    def get_prometheus_alerts(self):
        ''' Retrieve the active alerts from Prometheus

        This method makes a PrometheusQL lookup to retrieve the active alerts.
        If there are no alerts a string object is still returned that can be
        dumped into JSON for verification of no alert conditions.

        @return alerts: If an exception occurs log it and return None for flow
        @rtype str/None
        '''
        alerts = None
        alert_path = (
            'http://' + self.prometheus_url + '/api/v1/query?query=ALERTS'
        )
        try:
            alerts = requests.get(alert_path)
        except socket.gaierror:
            logging.critical('Could not resolve Prometheus in DNS')
            self.status = 'unhealthy'
        except requests.ConnectionError:
            logging.critical(
                'Could not get the alert data from Prometheus. Path tried '
                'was {}'.format(alert_path)
            )
            self.status = 'unhealthy'
            return None

        return alerts.text

    def json_prometheus_response(self, prometheus_string):
        ''' Dump the string response from Prometheus into a JSON object

        @param prometheus_string: The response of the PromQL query
        @type prometheus_string: str
        @return json.loads(prometheus_string): JSON object of the PromQL query
        @rtype json.loads(prometheus_string): JSON object
        '''
        try:
            return json.loads(prometheus_string)
        except json.JSONDecodeError:
            logging.critical('JSONDecodeError of the response from Prometheus')
            self.status = 'unhealthy'
            return None

    def process_prometheus_alerts(self, prometheus_query):
        ''' Process the alerts and determine whether the cluster is healthy

        If any of the alarms that we consider to have a negative impact on the
        cluster are active in Prometheus, return an unhealthy status.

        @param prometheus_query: JSON object of the alerts in Prometheus
        @type prometheus_query: JSON object
        '''
        if len(prometheus_query['data']['result']) == 0:
            logging.info('No alerts in Prometheus')
            self.status = 'healthy'
            return

        active_alert_names = []
        for alert in prometheus_query['data']['result']:
            active_alert_names.append(alert['metric']['alertname'])

        if any([x in active_alert_names for x in self.alerts]):
            logging.warning('Alert condition detected. Setting to unhealthy')
            logging.warning('Active alerts: {}'.format(active_alert_names))
            self.status = 'unhealthy'
        else:
            logging.warning('Alerts found but did not match any of: {}'.format(
                self.alerts)
            )
            logging.warning('Active alerts are {}'.format(active_alert_names))
            self.status = 'healthy'

    @property
    def status(self):
        ''' Returns the status of the cluster to Flask

        @return status: The status of the cluster state
        @rtype: str
        '''
        return self._status

    @status.setter
    def status(self, value):
        ''' Sets the status of the cluster based on the alarms

        @param status: The status level of the cluster
        @type status: str
        '''
        self._status = value


@app.route("/healthz")
def return_status():
    ''' Returns the status of the cluster for usage by an external user/service
    to determine the health.

    @return result: The cluster state
    @rtype string: str
    '''
    clusterheathz.start()
    return clusterheathz.status


@app.route("/")
def default_url_path():
    ''' Returns a string for if a user does not append the /healthz to the URL

    @return string: Message for the user for the default URL path
    @rtype string: str
    '''
    return "You're probably looking for /healthz"


@app.route("/howsyourfather")
def hows_your_father():
    ''' Wurzels are life

    @return string: Properjob young 'un
    @rtype string: str
    '''
    return "alright!"


def set_logger(log_level='INFO'):
    ''' Sets the logging module parameters

    @param log_level: The logging level required to display log information
    @type log_level: str
    '''
    root = logging.getLogger('')
    for handler in root.handlers:
        root.removeHandler(handler)
    format = '%(asctime)s %(levelname)-8s:%(message)s'
    logging.basicConfig(format=format, level=log_level)


if __name__ == "__main__":
    set_logger()
    clusterheathz = ClusterHealthz()
    app.run(host='0.0.0.0')
