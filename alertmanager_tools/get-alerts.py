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
    if not target.startswith('http'):
        target = 'http://' + target

    url = urllib.urljoin(target, '/api/v2/alerts')
    req = request.Request(url, method='GET')

    with request.urlopen(req) as client:
        data = client.read()
        return json.loads(data.decode())


def parse_alerts(raw_data: list) -> list:
    parsed_data = []

    for item in iter(raw_data):
        severity = item['labels']['severity']

        summary = item['annotations']['summary']
        summary = summary.replace('\n', '\\n')

        description = item['annotations']['description']
        description = description.replace('\n', '\\n')
        parsed_data.append((severity, summary, description))

    return parsed_data


def print_alerts(parsed_data: list) -> None:
    for (severity, summary, description) in parsed_data:
        print('Severity: {}'.format(severity))
        print('Summary: {}'.format(summary))
        print('Description: {}'.format(description))


if __name__ == '__main__':
    try:
        args = get_args()
        data = get_alerts(args.target)
        data = parse_alerts(data)
        print_alerts(data)

    except Exception:
        traceback.print_exc()
