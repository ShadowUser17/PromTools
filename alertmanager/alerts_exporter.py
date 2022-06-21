#!/usr/bin/env python3
from urllib import parse as urllib
from http import server as http
from urllib import request
from urllib import error
import socketserver
import threading
import traceback
import argparse
import typing
import json
import sys


class HandleAlerts:
    def __init__(self, target: str) -> None:
        if not target.startswith('http'):
            target = 'http://' + target

        target = urllib.urljoin(target, '/api/v2/alerts')
        self._target = request.Request(target, method='GET')
        self._lock = threading.Lock()

        self._metrics = {
            'amanager_exp_err_request': {
                'help': 'Requests error counter',
                'type': 'gauge', 'value': 0.0
            },
            'amanager_exp_err_parser': {
                'help': 'Parser error counter',
                'type': 'gauge', 'value': 0.0
            },
            'amanager_exp_alert': {
                'help': 'Alert from AlertManager',
                'type': 'gauge', 'value': None
            }
        }


    def get(self, key: str) -> list:
        'Return [help, type value]'
        self._lock.acquire()
        data = [
            self._metrics[key].get('help'),
            self._metrics[key].get('type'),
            self._metrics[key].get('value')
        ]

        self._lock.release()
        return data


    def set(self, key: str, value: typing.Any) -> None:
        self._lock.acquire()
        self._metrics[key]['value'] = value
        self._lock.release()


    def inc(self, key: str) -> None:
        self._lock.acquire()
        self._metrics[key]['value'] += 1
        self._lock.release()


    def _request_alerts(self) -> None:
        data = None

        try:
            with request.urlopen(self._target) as client:
                data = client.read()
                data = json.loads(data.decode())

            data = list(self._filter_alerts(data))
            self.set('amanager_exp_alert', data)

        except (error.ContentTooShortError, error.HTTPError, error.URLError):
            self.inc('amanager_exp_err_request')
            self.set('amanager_exp_alert', [])

        except (KeyError, AttributeError):
            self.inc('amanager_exp_err_parser')
            self.set('amanager_exp_alert', [])


    def _filter_alerts(self, data: list) -> typing.Generator:
        accept_labels = ['alertname', 'severity']
        accept_annotations = ['fingerprint', 'dashboard', 'docs']

        for item in data:
            alert = list()

            labels = item.get('labels', {})
            for key in accept_labels:
                if labels.get(key):
                    alert.append('{}=\"{}\"'.format(key, labels.get(key)))

            annotations = item.get('annotations', {})
            for key in accept_annotations:
                if annotations.get(key):
                    alert.append('{}=\"{}\"'.format(key, annotations.get(key)))

            yield ','.join(alert)


    def _format_alerts(self) -> str:
        line = list()

        # Add error counters.
        for key in ['amanager_exp_err_request', 'amanager_exp_err_parser']:
            items = self.get(key)
            line.extend([
            '# HELP {} {}'.format(key, items[0]),
            '# TYPE {} {}'.format(key, items[1]),
            '{} {}'.format(key, items[2])
        ])

        # Add alerts metric.
        alerts_key = 'amanager_exp_alert'
        alerts = self.get(alerts_key)

        line.extend([
            '# HELP {} {}'.format(alerts_key, alerts[0]),
            '# TYPE {} {}'.format(alerts_key, alerts[1])
        ])

        for item in alerts[2]:
            line.append(alerts_key + '{' + item + '} 1.0')

        return '\n'.join(line)


    def __call__(self) -> bytes:
        self._request_alerts()
        line = self._format_alerts()
        return line.encode()


class HandlerRequest(http.BaseHTTPRequestHandler):
    alerts_handler = None
    server_version = 'AlertManagerExporter'
    sys_version = 'Python3'


    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(self.alerts_handler())
        self.wfile.write('\n'.encode())


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='''\
This is an AlertManager exporter.
The main goal of this tool is to get alerts from AlertManager and convert them to Prometheus metrics.\
''')
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9093', help='Set alertmanager address.')
    parser.add_argument('-l', dest='listen', default='127.0.0.1', help='Set exporter listen address.')
    parser.add_argument('-p', dest='port', default=49152, type=int, help='Set exporter listen port.')
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    try:
        HandlerRequest.alerts_handler = HandleAlerts(args.target)

        with socketserver.ThreadingTCPServer((args.listen, args.port), HandlerRequest) as srv:
            print('Target: {} Listen: {}:{}'.format(args.target, args.listen, args.port))
            srv.serve_forever()

    except KeyboardInterrupt:
        srv.shutdown()
        sys.exit(0)

    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main(get_args())
