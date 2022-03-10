#!./env/bin/python3
from urllib import parse as urllib
from urllib import request

import json
import time
import argparse
import traceback
import prometheus_client


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9093', help='Set alertmanager address.')
    parser.add_argument('-l', dest='listen', default='http://127.0.0.1:49152', help='Set exporter listen address.')
    parser.add_argument('-i', dest='interval', default=30.0, type=float, help='Set scrape interval.')
    return parser.parse_args()


def get_alerts(target: str) -> list:
    url = urllib.urljoin(target, '/api/v2/alerts')
    req = request.Request(url, method='GET')

    with request.urlopen(req) as client:
        data = client.read()
        return json.loads(data.decode())


def parse_alerts(raw_data: list) -> list:
    parsed_data = []

    for item in iter(raw_data):
        severity = item['labels']['severity']
        description = item['annotations']['description']
        parsed_data.append((severity, description))

    return parsed_data


def req_handler(data: list, metric: prometheus_client.Counter) -> None:
    for (severity, description) in data:
        item = metric.labels(severity, description)
        item.inc()


if __name__ == '__main__':
    try:
        args = get_args()
        listen = urllib.urlparse(args.listen)

        metric = prometheus_client.Counter(
            'amanager_exp_alert',
            'Alerts from AlertManager.',
            ['severity', 'description']
        )

        print('Listen: {}:{}'.format(listen.hostname, listen.port))
        prometheus_client.start_http_server(listen.port, listen.hostname)

        while True:
            data = get_alerts(args.target)
            data = parse_alerts(data)
            req_handler(data, metric)
            time.sleep(args.interval)

    except Exception:
        traceback.print_exc()
