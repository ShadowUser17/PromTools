#!/usr/bin/env python3
from urllib import parse as urllib
from http import server as http
import socketserver
import threading
import traceback
import argparse
import sys
import ssl

try:
    from cryptography.hazmat.backends import default_backend
    from urllib3 import disable_warnings
    from cryptography import x509
    from requests import Session

except ImportError:
    print(traceback.format_exc())
    sys.exit(1)


class MetricHandler:
    def __init__(self) -> None:
        self._lock = threading.Lock()

        self._data = {
            'probe_ssl_earliest_cert_expiry': {
                'help': 'Returns earliest SSL cert expiry in unixtime',
                'type': 'gauge', 'value': None
            },
            'probe_http_status_code': {
                'help': 'Response HTTP status code',
                'type': 'gauge', 'value': None
            },
            'probe_duration_seconds': {
                'help': 'Returns how long the probe took to complete in seconds',
                'type': 'gauge', 'value': None
            },
            'probe_success': {
                'help': 'Contains SSL leaf certificate information',
                'type': 'gauge', 'value': None
            }
        }

    def set(self, key: str, value) -> None:
        self._lock.acquire()
        self._data[key]['value'] = value
        self._lock.release()

    def get(self, key: str) -> tuple:
        'Return: tuple(help, type, value)'
        self._lock.acquire()
        data = (
            self._data[key].get('help'),
            self._data[key].get('type'),
            self._data[key].get('value')
        )
        self._lock.release()
        return data


    def clear(self) -> None:
        self._lock.acquire()

        for key in self._data:
            self._data[key]['value'] = None

        self._lock.release()

    def __call__(self, target: str, writer) -> None:
        url = urllib.urlparse(target)
        self.clear()
        self._request_data(url)

        for item in self._format_data():
            writer.write(item)

    def _request_data(self, url: urllib.ParseResult) -> None:
        self.set('probe_success', 1)

        try:
            if url.scheme.startswith('https'):
                port = 443 if not url.port else url.port
                peer_cert = ssl.get_server_certificate((url.hostname, port))
                peer_cert = x509.load_pem_x509_certificate(peer_cert.encode(), default_backend())
                self.set('probe_ssl_earliest_cert_expiry', peer_cert.not_valid_after.timestamp())

        except Exception:
            self.set('probe_success', 0)

        try:
            with Session() as client:
                resp = client.request("GET", url.geturl(), verify=False)
                self.set('probe_http_status_code', resp.status_code)
                self.set('probe_duration_seconds', resp.elapsed.seconds)

        except Exception:
            self.set('probe_success', 0)

    def _format_data(self) -> bytes:
        for key in self._data:
            items = self.get(key)

            yield '# HELP {} {}\n'.format(key, items[0]).encode()
            yield '# TYPE {} {}\n'.format(key, items[1]).encode()

            if items[2]:
                yield '{} {}\n'.format(key, items[2]).encode()


class RequestHandler(http.BaseHTTPRequestHandler):
    metric_handler = None
    server_version = 'HealthCheckExporter'
    sys_version = 'Python3'

    def do_GET(self):
        path = urllib.urlparse(self.path)
        args = urllib.parse_qs(path.query)

        if (path.path == '/probe') and (args.get('target')):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.metric_handler(args.get('target')[0], self.wfile)

        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"No target defined!\nUse /probe?target=<url>\n")


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='''\
This is a Health Check Exporter
The main goal of this tool is to check URLs and convert them to Prometheus metrics.\
''')
        parser.add_argument('-l', dest='address', default='127.0.0.1', help='Set exporter listen address.')
        parser.add_argument('-p', dest='port', default=9097, type=int, help='Set exporter listen port.')

        disable_warnings()
        args = parser.parse_args()
        RequestHandler.metric_handler = MetricHandler()

        with socketserver.ThreadingTCPServer((args.address, args.port), RequestHandler) as srv:
            print('Listen {}:{}'.format(args.address, args.port))
            srv.serve_forever()

    except KeyboardInterrupt:
        srv.shutdown()
        sys.exit(0)

    except Exception:
        print(traceback.format_exc())
        sys.exit(2)
