#!/usr/bin/env python3
from urllib import parse as urllib
from http import server as http
import socketserver
import argparse
import logging
import typing
import sys
import ssl


logging.basicConfig(
    format=r'%(levelname)s [%(asctime)s]: "%(message)s"',
    datefmt=r'%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

try:
    from prometheus_client import Gauge
    from prometheus_client import CollectorRegistry
    from prometheus_client.exposition import generate_latest

    from requests import Session
    from cryptography import x509
    from urllib3 import disable_warnings
    from cryptography.hazmat.backends import default_backend

except ImportError as message:
    logging.error('Dependencies: ' + str(message))
    sys.exit(1)


class MetricHandler:
    def __init__(self, registry: CollectorRegistry) -> None:
        self._registry = registry

        self.probe_ssl_earliest_cert_expiry = Gauge(
            name='probe_ssl_earliest_cert_expiry',
            documentation='Returns earliest SSL cert expiry in unixtime',
            registry=registry
        )

        self.probe_http_status_code = Gauge(
            name='probe_http_status_code',
            documentation='Response HTTP status code',
            registry=registry
        )

        self.probe_duration_seconds = Gauge(
            name='probe_duration_seconds',
            documentation='Returns how long the probe took to complete in seconds',
            registry=registry
        )

        self.probe_success = Gauge(
            name='probe_success',
            documentation='Contains SSL leaf certificate information',
            registry=registry
        )


    def _clear_data(self) -> None:
        self.probe_ssl_earliest_cert_expiry.set(0.0)
        self.probe_http_status_code.set(0.0)
        self.probe_duration_seconds.set(0.0)
        self.probe_success.set(0.0)


    def __call__(self, target: str) -> bytes:
        self._clear_data()
        self._request_data(urllib.urlparse(target))
        return generate_latest(self._registry)


    def _request_data(self, url: urllib.ParseResult) -> None:
        self.probe_success.set(1.0)

        try:
            if url.scheme.startswith('https'):
                port = 443 if not url.port else url.port
                peer_cert = ssl.get_server_certificate((url.hostname, port))
                peer_cert = x509.load_pem_x509_certificate(peer_cert.encode(), default_backend())
                self.probe_ssl_earliest_cert_expiry.set(peer_cert.not_valid_after.timestamp())

        except Exception as message:
            logging.error(logging.error('ProbeCert: ' + str(message)))
            self.probe_success.set(0.0)

        try:
            with Session() as client:
                resp = client.request("GET", url.geturl(), verify=False)
                self.probe_http_status_code.set(resp.status_code)
                self.probe_duration_seconds.set(resp.elapsed.seconds)

        except Exception as message:
            logging.error(logging.error('ProbeHttp: ' + str(message)))
            self.probe_success.set(0.0)


class RequestHandler(http.BaseHTTPRequestHandler):
    metric_handler = None
    server_version = 'HealthCheckExporter'
    sys_version = 'Python3'

    def log_error(self, format: str, *args: typing.Any) -> None:
        logging.error("%s - - %s" % (self.address_string(), format % args))


    def log_message(self, format: str, *args: typing.Any) -> None:
        logging.info("%s - - %s" % (self.address_string(), format % args))


    def do_GET(self) -> None:
        path = urllib.urlparse(self.path)
        args = urllib.parse_qs(path.query)

        if (path.path == '/probe') and (args.get('target')):
            data = self.metric_handler(args.get('target')[0])
            size = str(len(data))

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', size)
            self.end_headers()
            self.wfile.write(data)

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
        parser.add_argument('-p', dest='port', default=49155, type=int, help='Set exporter listen port.')

        disable_warnings()
        args = parser.parse_args()
        RequestHandler.metric_handler = MetricHandler(CollectorRegistry())

        with socketserver.ThreadingTCPServer((args.address, args.port), RequestHandler) as srv:
            logging.info('Listen http://{}:{}/probe'.format(args.address, args.port))
            srv.serve_forever()

    except KeyboardInterrupt:
        logging.info('Interrupting...')
        srv.shutdown()
        sys.exit(0)

    except Exception as message:
        logging.error('__main__: ' + str(message))
        sys.exit(2)
