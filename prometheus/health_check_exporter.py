#!/usr/bin/env python3
from urllib import parse as urllib
from http.server import HTTPServer
import traceback
import argparse
import sys
import ssl

try:
    from cryptography.hazmat.backends import default_backend
    from prometheus_client import MetricsHandler
    from urllib3 import disable_warnings
    from prometheus_client import Gauge
    from cryptography import x509
    from requests import Session

except ImportError:
    print(traceback.format_exc())
    sys.exit(1)


class HealthCheck(MetricsHandler):
    probe_ssl_earliest_cert_expiry = Gauge(
        'probe_ssl_earliest_cert_expiry',
        'Returns earliest SSL cert expiry in unixtime',
        ['instance']
    )

    probe_http_status_code = Gauge(
        'probe_http_status_code',
        'Response HTTP status code',
        ['instance']
    )

    probe_duration_seconds = Gauge(
        'probe_duration_seconds',
        'Returns how long the probe took to complete in seconds',
        ['instance']
    )

    def _load_ssl_cert(self, url: urllib.ParseResult):
        self.probe_ssl_earliest_cert_expiry.clear()

        if url.scheme.startswith('https'):
            port = 443 if not url.port else url.port
            peer_cert = ssl.get_server_certificate((url.hostname, port))
            peer_cert = x509.load_pem_x509_certificate(peer_cert.encode(), default_backend())
            self.probe_ssl_earliest_cert_expiry.labels(url.hostname).set(peer_cert.not_valid_after.timestamp())

    def _check_endpoint(self, url: urllib.ParseResult):
        self.probe_http_status_code.clear()
        self.probe_duration_seconds.clear()

        with Session() as client:
            resp = client.request("GET", url.geturl(), verify=False)
            self.probe_http_status_code.labels(url.hostname).set(resp.status_code)
            self.probe_duration_seconds.labels(url.hostname).set(resp.elapsed.seconds)

    def do_GET(self):
        path = urllib.urlparse(self.path)
        args = urllib.parse_qs(path.query)
        print('GET', path.geturl())

        if (path.path == '/probe') and (args.get('target')):
            target = urllib.urlparse(args.get('target')[0])

            self._load_ssl_cert(target)
            self._check_endpoint(target)
            super(HealthCheck, self).do_GET()

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"No target defined\n")


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
        print('Listen {}:{}'.format(args.address, args.port))
        HTTPServer((args.address, args.port), HealthCheck).serve_forever()

    except KeyboardInterrupt:
        sys.exit(0)

    except Exception:
        print(traceback.format_exc())
        sys.exit(2)
