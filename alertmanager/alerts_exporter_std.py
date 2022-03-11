#!/usr/bin/env python3
from urllib import parse as urllib
from http import server as http
from urllib import request
import socketserver
import traceback
import argparse
import json


class HandleAlerts:
    def __init__(self, target: str) -> None:
        self._metric = 'amanager_exp_alert'
        self._metric_help = 'Alerts from AlertManager'
        self._target = urllib.urljoin(target, '/api/v2/alerts')
        self._alerts = dict()

        self._err_request_name = 'amanager_exp_err_request'
        self._err_request_help = ''
        self._err_request = 0.0

        self._err_parser_name = 'amanager_exp_err_parser'
        self._err_parser_help = ''
        self._err_parser = 0.0


    def __str__(self) -> str:
        line = [
            '# HELP {} {}'.format(self._metric, self._metric_help),
            '# TYPE {} gauge'.format(self._metric)
        ]

        template = 'severity=\"{}\",summary=\"{}\",'
        for (severity, summary) in self._alerts.values():
            line.append(self._metric + '{' + template.format(severity, summary) + '} 1.0')

        line.extend([
            '# HELP {} {}'.format(self._err_request_name, self._err_request_help),
            '# TYPE {} gauge'.format(self._err_request_name),
            '{} {}'.format(self._err_request_name, self._err_request),

            '# HELP {} {}'.format(self._err_parser_name, self._err_parser_help),
            '# TYPE {} gauge'.format(self._err_parser_name),
            '{} {}'.format(self._err_parser_name, self._err_parser)
        ])

        return '\n'.join(line)


    def __repr__(self) -> str:
        return self.__str__()


    def request(self) -> None:
        self._alerts.clear()
        req = request.Request(self._target, method='GET')
        data = None

        try:
            with request.urlopen(req) as client:
                data = client.read()
                data = json.loads(data.decode())

        except Exception:
            self._err_request += 1
            traceback.print_exc()
            return

        try:
            for item in data:
                severity = item['labels']['severity']
                summary = item['annotations']['summary']
                summary = summary.replace('\n', '\\n')
                self._alerts[item['fingerprint']] = [severity, summary]

        except Exception:
            self._err_parser += 1
            traceback.print_exc()


    def __call__(self) -> bytes:
        self.request()
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
        self.wfile.write(self.alert_handler())
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

        HandlerRequest.alert_handler = HandleAlerts(args.target)
        with socketserver.ThreadingTCPServer(get_listen(args.listen), HandlerRequest) as srv:
            print('Listen: {}:{}'.format(*srv.server_address))
            srv.serve_forever()

    except KeyboardInterrupt:
        srv.shutdown()

    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    main()
