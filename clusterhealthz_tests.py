#!/usr/bin/env python3

# This file is part of ClusterHealthz.
 
# ClusterHealthz is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
 
# ClusterHealthz is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
 
# You should have received a copy of the GNU General Public License
# along with ClusterHealthz.  If not, see <http://www.gnu.org/licenses/>.
import json
import unittest

from clusterhealthz.server import app, ClusterHealthz


class ClusterHealthzTests(unittest.TestCase):
    ''' A set of unit tests for the ClusterHealthz service.

    This module will test for correct server startup and an HTTP 200 OK
    response and the methods of the ClusterHealthz module, including the
    different conditions that could be encountered.
    '''

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.valid_prometheus_alerts_non_impacting = (
            '{"status":"success","data":{"resultType":"vector","result":[{"'
            'metric":{"__name__":"ALERTS","alertname":"ExampleAlertAlwaysFirin'
            'g","alertstate":"firing","job":"alertmanager"},"value":[150642265'
            '6.757,"1"]},{"metric":{"__name__":"ALERTS","alertname":"ExampleAl'
            'ertAlwaysFiring","alertstate":"firing","job":"node"},"value":[150'
            '6422656.757,"1"]},{"metric":{"__name__":"ALERTS","alertname":"Exa'
            'mpleAlertAlwaysFiring","alertstate":"firing","job":"prometheus"},'
            '"value":[1506422656.757,"1"]},{"metric":{"__name__":"ALERTS","ale'
            'rtname":"ExampleAlertAlwaysFiring","alertstate":"firing","job":"p'
            'ushgateway"},"value":[1506422656.757,"1"]}]}}'
        )
        self.valid_prometheus_alerts_impacting = (
            '{"status":"success","data":{"resultType":"vector","result":[{"'
            'metric":{"__name__":"ALERTS","alertname":"KubernetesMasterDown'
            '","alertstate":"firing","job":"alertmanager"},"value":[150642265'
            '6.757,"1"]},{"metric":{"__name__":"ALERTS","alertname":"ExampleAl'
            'ertAlwaysFiring","alertstate":"firing","job":"node"},"value":[150'
            '6422656.757,"1"]},{"metric":{"__name__":"ALERTS","alertname":"Exa'
            'mpleAlertAlwaysFiring","alertstate":"firing","job":"prometheus"},'
            '"value":[1506422656.757,"1"]},{"metric":{"__name__":"ALERTS","ale'
            'rtname":"ExampleAlertAlwaysFiring","alertstate":"firing","job":"p'
            'ushgateway"},"value":[1506422656.757,"1"]}]}}'
        )
        self.invalid_prometheus_response = 'narp'
        self.no_alerts = (
            '{"status":"success","data":{"resultType":"vector","result":[]}}'
        )
        self.no_alerts_json = json.loads(self.no_alerts)
        self.valid_prometheus_alerts_non_impacting_json = json.loads(
            self.valid_prometheus_alerts_non_impacting
        )
        self.valid_prometheus_alerts_impacting_json = json.loads(
            self.valid_prometheus_alerts_impacting
        )
        self.invalid_configuration = {'test': 'test'}
        self.valid_configuration = ['AlertOne', 'AlertTwo']
        self.app = app.test_client()

    def tearDown(self):
        pass

    def test_server_start_up(self):
        ''' Assert an HTTP 200 response from the server
        '''
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_cannot_resolve_prometheus(self):
        ''' Assert a DNS exception with an invalid hostname
        '''
        test_clusterhealthz_instance = ClusterHealthz(
            prometheus_url='not_in_dns'
        )
        test_clusterhealthz_instance.start()
        self.assertEqual(test_clusterhealthz_instance.status, 'unhealthy')

    def test_prometheus_connection_failure(self):
        ''' Assert a connection failure to the Prometheus instance
        '''
        test_clusterhealthz_instance = ClusterHealthz(
            prometheus_url='google.co.uk'
        )
        test_clusterhealthz_instance.start()
        self.assertEqual(test_clusterhealthz_instance.status, 'unhealthy')

    def test_json_encoding_of_valid_prometheus_response_active_alerts(self):
        ''' Assert the JSON encoding of a valid Prometheus response
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        self.assertTrue(isinstance(
            test_clusterhealthz_instance.json_prometheus_response(
                self.valid_prometheus_alerts_non_impacting), dict)
        )

    def test_json_encoding_of_valid_prometheus_response_no_active_alerts(self):
        ''' Assert the JSON encoding of a valid Prometheus response
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        self.assertTrue(isinstance(
            test_clusterhealthz_instance.json_prometheus_response(
                self.no_alerts), dict)
        )

    def test_json_encoding_of_an_invalid_prometheus_response(self):
        ''' Assert the JSON encoding of an invalid Prometheus response
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        test_clusterhealthz_instance.json_prometheus_response(
                self.invalid_prometheus_response
            )
        self.assertEqual(test_clusterhealthz_instance.status, 'unhealthy')

    def test_process_prometheus_no_alerts(self):
        ''' The status of the cluster should be healthy with no alerts
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        test_clusterhealthz_instance.process_prometheus_alerts(
            self.no_alerts_json
        )
        self.assertEqual(test_clusterhealthz_instance.status, 'healthy')

    def test_process_prometheus_active_alerts_cluster_impacting(self):
        ''' Test the condition there are active cluster impacting alerts
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        test_clusterhealthz_instance.process_prometheus_alerts(
            self.valid_prometheus_alerts_impacting_json
        )
        self.assertEqual(test_clusterhealthz_instance.status, 'unhealthy')

    def test_process_prometheus_active_alerts_non_cluster_impacting(self):
        ''' Test the condition there are active alerts but non-impacting
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        test_clusterhealthz_instance.process_prometheus_alerts(
            self.valid_prometheus_alerts_non_impacting_json
        )
        self.assertEqual(test_clusterhealthz_instance.status, 'healthy')

    def test_open_configuration_failure_invalid_path(self):
        ''' Test an invalid path for the configuration definition
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        with self.assertRaises(SystemExit):
            test_clusterhealthz_instance.open_configuration(
                alert_configuration_path='does_not_exist'
            )

    def test_process_invalid_configuration(self):
        ''' Test an invalid data structure
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        with self.assertRaises(TypeError):
            test_clusterhealthz_instance.process_configuration(
                self.invalid_configuration
            )

    def test_process_valid_configuration(self):
        ''' Test a valid data structure
        '''
        test_clusterhealthz_instance = ClusterHealthz()
        test_clusterhealthz_instance.process_configuration(
            self.valid_configuration
        )


if __name__ == "__main__":
    unittest.main()
