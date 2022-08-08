#!/usr/bin/env python3
from urllib import parse as urllib
from urllib import request

import sys
import json
import argparse
import traceback


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9090', help='Set Prometheus address.')
    parser.add_argument('labels', help='Set list of labels. (label,...)')
    return parser.parse_args()


def get_values(target: str, label: str) -> list:
    url = urllib.urljoin(target, '/api/v1/label/{}/values'.format(label))
    req = request.Request(url, method='GET')

    with request.urlopen(req) as client:
        data = client.read().decode()
        data = json.loads(data)
        return data.get('data', [])


try:
    args = get_args()

    target = args.target
    if not target.startswith('http'):
        target = 'http://' + target

    labels = args.labels.split(',')
    for item in labels:
        data = get_values(target, item)
        print('{}:\n - {}\n'.format(item, '\n - '.join(data)))


except Exception:
    traceback.print_exc()
    sys.exit(1)
