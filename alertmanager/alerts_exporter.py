#!/usr/bin/env python3
from urllib import parse as urllib
from http import server as http
from urllib import request
from urllib import error
import socketserver
import argparse
import logging
import typing
import json
import sys


logging.basicConfig(
    format=r'%(levelname)s [%(asctime)s]: "%(message)s"',
    datefmt=r'%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

try:
    from prometheus_client import Gauge
    from prometheus_client import CollectorRegistry
    from prometheus_client.exposition import generate_latest

except ImportError as message:
    logging.error('Dependencies: ' + str(message))
    sys.exit(1)


class RequestHandler(http.BaseHTTPRequestHandler):
    metric_handler = None
    server_version = 'AlertManagerExporter'
    sys_version = 'Python3'

    def log_error(self, format: str, *args: typing.Any) -> None:
        logging.error("%s - - %s" % (self.address_string(), format % args))


    def log_message(self, format: str, *args: typing.Any) -> None:
        logging.info("%s - - %s" % (self.address_string(), format % args))


    def _handle_404(self) -> None:
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('Target {} not found!\n'.format(self.path).encode())


    def do_POST(self) -> None:
        if self.path == '/reset':
            self.send_response(200)
            self.end_headers()

            self.log_message('Request of clean all alerts.')
            self.metric_handler.clean()

        else:
            self._handle_404()


    def do_GET(self) -> None:
        if (self.path == '/') or (self.path == '/metrics'):
            data = self.metric_handler()
            size = str(len(data))

            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', size)
            self.end_headers()
            self.wfile.write(data)

        else:
            self._handle_404()


class MetricsHandler:
    def __init__(self, target: str, registry: CollectorRegistry) -> None:
        self._registry = registry
        self._alerts_name = 'amanager_exp_alert'

        if not target.startswith('http'):
            target = 'http://' + target

        self._target = request.Request(
            url=urllib.urljoin(target, '/api/v2/alerts'),
            method='GET'
        )

        self._alerts = Gauge(
            name=self._alerts_name,
            documentation='Alert from AlertManager',
            labelnames=['alertname', 'severity', 'fingerprint', 'dashboard', 'docs'],
            registry=registry
        )

        self._req_count = Gauge(
            name='amanager_exp_req_count',
            documentation='Requests of data',
            registry=registry
        )

        self._error_request = Gauge(
            name='amanager_exp_err_request',
            documentation='Requests error counter',
            registry=registry
        )

        self._error_parser = Gauge(
            name='amanager_exp_err_parser',
            documentation='Parser error counter',
            registry=registry
        )


    def __call__(self) -> bytes:
        'Start collecting metrics data.'
        self._request_alerts()
        return generate_latest(self._registry)


    def clean(self) -> None:
        'Clean all alerts.'
        self._alerts.clear()
        self._req_count.set(0.0)
        self._error_request.set(0.0)
        self._error_parser.set(0.0)


    def _request_alerts(self) -> None:
        try:
            with request.urlopen(self._target) as client:
                data = client.read()
                data = json.loads(data.decode())

                self._req_count.inc()
                logging.info('Request: ' + client.geturl())

            data = self._filter_alerts(data)
            self._update_alerts(data)

        except (error.ContentTooShortError, error.HTTPError, error.URLError) as message:
            self._error_request.inc()
            logging.error('Request: ' + str(message))

        except (KeyError, AttributeError) as message:
            self._error_parser.inc()
            logging.error(logging.error('Parser: ' + str(message)))


    def _filter_alerts(self, data: typing.Iterable) -> typing.Generator:
        accept_labels = ['alertname', 'severity']
        accept_annotations = ['fingerprint', 'dashboard', 'docs']

        for item in data:
            alert = dict()

            labels = item.get('labels', {})
            for key in accept_labels:
                alert[key] = labels.get(key, '')

            annotations = item.get('annotations', {})
            for key in accept_annotations:
                alert[key] = annotations.get(key, '')

            yield alert


    def _update_alerts(self, new_data: typing.Iterable) -> None:
        for metric in self._registry.collect():
            if metric.name != self._alerts_name:
                continue

            for sample in metric.samples:
                if not (sample.labels in new_data):
                    self._alerts.labels(**sample.labels).set(0.0)

            for item in new_data:
                self._alerts.labels(**item).inc()


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='''\
This is an AlertManager exporter.
The main goal of this tool is to get alerts from AlertManager and convert them to Prometheus metrics.\
''')
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9093', help='Set alertmanager address.')
    parser.add_argument('-l', dest='listen', default='127.0.0.1', help='Set exporter listen address.')
    parser.add_argument('-p', dest='port', default=49152, type=int, help='Set exporter listen port.')
    return parser.parse_args()


if __name__ == '__main__':
    try:
        args = get_args()
        RequestHandler.metric_handler = MetricsHandler(args.target, CollectorRegistry())

        with socketserver.ThreadingTCPServer((args.listen, args.port), RequestHandler) as srv:
            logging.info('Listen: http://{}:{}/ (AlertManager: {})'.format(args.listen, args.port, args.target))
            srv.serve_forever()

    except KeyboardInterrupt:
        logging.info('Interrupting...')
        srv.server_close()
        sys.exit(0)

    except Exception as message:
        logging.error('__main__: ' + str(message))
        sys.exit(2)
