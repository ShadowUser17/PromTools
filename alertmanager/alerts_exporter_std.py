#!/usr/bin/env python3
from urllib import parse as urllib
from urllib import request
from http import server as http
import socketserver
import json
import argparse
import traceback


class HandleAlerts:
    def __init__(self, target: str, metric_name: str, metric_help: str) -> None:
        self._target = urllib.urljoin(target, '/api/v2/alerts')
        self._metric = metric_name
        self._alerts = dict()

        self.metric_help_line = '# HELP {} {}'.format(metric_name, metric_help)
        self.metric_name_line = '# TYPE {} gauge'.format(metric_name)

    def __str__(self) -> str:
        line = [self.metric_help_line, self.metric_name_line]
        template = 'severity=\"{}\",summary=\"{}\",'

        for (severity, summary) in self._alerts.values():
            line.append(self._metric + '{' + template.format(severity, summary) + '} 1.0')

        return '\n'.join(line)

    def __repr__(self) -> str:
        return self.__str__()

    def _parser(self, raw_data: list) -> None:
        self._alerts.clear()

        for item in iter(raw_data):
            severity = item['labels']['severity']
            summary = item['annotations']['summary']
            summary = summary.replace('\n', '\\n')
            self._alerts[item['fingerprint']] = [severity, summary]

    def request(self) -> None:
        req = request.Request(self._target, method='GET')
        data = None

        with request.urlopen(req) as client:
            data = client.read()
            data = json.loads(data.decode())

        self._parser(data)

    def encode(self) -> bytes:
        line = self.__str__()
        return line.encode()


class HandlerRequest(http.BaseHTTPRequestHandler):
    alert_handler = None
    server_version = 'AlertManagerExporter'
    sys_version = 'Python3'

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.alert_handler.request()
        self.wfile.write(self.alert_handler.encode())
        self.wfile.write('\n'.encode())


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='''\
This is an AlertManager exporter.
The main goal of this tool is to get alerts from AlertManager and convert them to Prometheus metrics.\
''')
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9093', help='Set alertmanager address.')
    parser.add_argument('-l', dest='listen', default='127.0.0.1:49152', help='Set exporter listen address.')
    return parser.parse_args()


def get_listen(address: str) -> tuple:
    (addr, port) = address.split(':')
    return (addr, int(port))


def main() -> None:
    try:
        args = get_args()

        HandlerRequest.alert_handler = HandleAlerts(args.target, 'amanager_exp_alert', 'Alerts from AlertManager')
        with socketserver.ThreadingTCPServer(get_listen(args.listen), HandlerRequest) as srv:
            print('Listen: {}:{}'.format(*srv.server_address))
            srv.serve_forever()

    except KeyboardInterrupt:
        srv.shutdown()

    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    main()
