#!/usr/bin/env python3
from urllib import parse as urllib
from urllib import request

import json
import argparse
import traceback


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9090', help='Set Prometheus address.')
    return parser.parse_args()


def get_resources(target: str) -> list:
    url = urllib.urljoin(target, '/api/v1/query?query=aws_resource_info')
    req = request.Request(url, method='GET')

    with request.urlopen(req) as client:
        data = client.read()
        return json.loads(data.decode())


def parse_resources(raw_data: list) -> list:
    parsed_data = []

    for item in iter(raw_data['data']['result']):
        parsed_data.append(item['metric'])

    return parsed_data


def print_resources(parsed_data: list) -> None:
    for item in parsed_data:
        for (key, val) in item.items():
            print('{}: {}'.format(key, val))

        else:
            print()


if __name__ == '__main__':
    try:
        args = get_args()
        data = get_resources(args.target)
        data = parse_resources(data)
        print_resources(data)

    except Exception:
        traceback.print_exc()
