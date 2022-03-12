#!/usr/bin/env python3
from urllib import parse as urllib
from http import server as http
from urllib import request
from urllib import error
import socketserver
import threading
import traceback
import argparse
import json


class HandleAlerts:
    def __init__(self, target: str) -> None:
        if not target.startswith('http'):
            target = 'http://' + target

        target = urllib.urljoin(target, '/api/v2/alerts')
        self._target = request.Request(target, method='GET')

        self._metric = 'amanager_exp_alert'
        self._metric_help = 'Alerts from AlertManager'
        self._alerts_lock = threading.Lock()
        self._alerts = dict()

        self._err_request_name = 'amanager_exp_err_request'
        self._err_request_help = ''
        self._err_request = 0.0

        self._err_parser_name = 'amanager_exp_err_parser'
        self._err_parser_help = ''
        self._err_parser = 0.0


    def _request_alerts(self) -> bool:
        self._alerts.clear()
        data = None

        try:
            with request.urlopen(self._target) as client:
                data = client.read()
                data = json.loads(data.decode())

            for item in data:
                severity = item['labels']['severity']
                summary = item['annotations']['summary']
                summary = summary.replace('\n', '\\n')
                self._alerts[item['fingerprint']] = [severity, summary]

        except (error.ContentTooShortError, error.HTTPError, error.URLError):
            self._err_request += 1
            traceback.print_exc()
            return True

        except (KeyError, AttributeError):
            self._err_parser += 1
            traceback.print_exc()
            return True


    def _format_alerts(self, skip_data: bool) -> str:
        line = list()

        # Skip data if error.
        if not skip_data:
            line.extend([
                '# HELP {} {}'.format(self._metric, self._metric_help),
                '# TYPE {} gauge'.format(self._metric)
            ])

            template = 'severity=\"{}\",summary=\"{}\",'
            for (severity, summary) in self._alerts.values():
                line.append(self._metric + '{' + template.format(severity, summary) + '} 1.0')

        # Add error counters.
        line.extend([
            '# HELP {} {}'.format(self._err_request_name, self._err_request_help),
            '# TYPE {} gauge'.format(self._err_request_name),
            '{} {}'.format(self._err_request_name, self._err_request),

            '# HELP {} {}'.format(self._err_parser_name, self._err_parser_help),
            '# TYPE {} gauge'.format(self._err_parser_name),
            '{} {}'.format(self._err_parser_name, self._err_parser)
        ])

        return '\n'.join(line)


    def __call__(self) -> bytes:
        self._alerts_lock.acquire()
        line = self._format_alerts(self._request_alerts())

        self._alerts_lock.release()
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
    parser.add_argument('-l', dest='listen', default='127.0.0.1:49152', help='Set exporter listen address.')
    return parser.parse_args()


def get_listen(address: str) -> tuple:
    (addr, port) = address.split(':')
    return (addr, int(port))


def main(args: argparse.Namespace) -> None:
    try:
        HandlerRequest.alerts_handler = HandleAlerts(args.target)
        with socketserver.ThreadingTCPServer(get_listen(args.listen), HandlerRequest) as srv:
            print('Target: {} Listen: {}'.format(args.target, args.listen))
            srv.serve_forever()

    except KeyboardInterrupt:
        srv.shutdown()

    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    main(get_args())
