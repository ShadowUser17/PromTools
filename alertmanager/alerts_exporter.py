#!./env/bin/python3
from urllib import parse as urllib
from urllib import request

import sys
import json
import time
import argparse
import traceback

# Warning! The next dependencies are external.
# Make env and use ./env/bin/pip install -r <dir>/requirements.txt
import prometheus_client


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='''\
This is an AlertManager exporter.
The main goal of this tool is to get alerts from AlertManager and convert them to Prometheus metrics.\
''')
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9093', help='Set alertmanager address.')
    parser.add_argument('-l', dest='listen', default='127.0.0.1:49152', help='Set exporter listen address.')
    parser.add_argument('-i', dest='interval', default=30.0, type=float, help='Set scrape interval.')
    return parser.parse_args()


def get_alerts(target: str) -> list:
    url = urllib.urljoin(target, '/api/v2/alerts')
    req = request.Request(url, method='GET')

    try:
        with request.urlopen(req) as client:
            data = client.read()
            data = json.loads(data.decode())

        parsed_data = []
        for item in data:
            severity = item['labels']['severity']
            summary = item['annotations']['summary']
            parsed_data.append((severity, summary))

        return parsed_data

    except Exception:
        traceback.print_exc()
        return []


def req_handler(data: list, metric: prometheus_client.Gauge) -> None:
    metric.clear()

    for (severity, summary) in data:
        item = metric.labels(severity, summary)
        item.set(1.0)


if __name__ == '__main__':
    try:
        args = get_args()
        listen = args.listen.split(':')

        metric = prometheus_client.Gauge(
            'amanager_exp_alert',
            'Alerts from AlertManager.',
            ['severity', 'summary']
        )

        print('Listen: {}:{}'.format(*listen))
        prometheus_client.start_http_server(addr=listen[0], port=int(listen[1]))

        while True:
            data = get_alerts(args.target)
            req_handler(data, metric)
            time.sleep(args.interval)

    except KeyboardInterrupt:
        sys.exit(0)

    except Exception:
        traceback.print_exc()
        sys.exit(1)
