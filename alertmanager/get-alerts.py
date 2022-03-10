#!/usr/bin/env python3
from urllib import parse as urllib
from urllib import request

import json
import argparse
import traceback


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9093', help='Set AlertManager address.')
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


def print_alerts(parsed_data: list) -> None:
    for (severity, description) in parsed_data:
        print('{}: {}'.format(severity.capitalize(), description))


if __name__ == '__main__':
    try:
        args = get_args()
        data = get_alerts(args.target)
        data = parse_alerts(data)
        print_alerts(data)

    except Exception:
        traceback.print_exc()
