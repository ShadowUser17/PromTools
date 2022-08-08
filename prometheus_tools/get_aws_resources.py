#!/usr/bin/env python3
from urllib import parse as urllib
from urllib import request

import json
import typing
import argparse
import traceback


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9090', help='Set Prometheus address.')
    parser.add_argument('-f', dest='filter', default='=', help='Set field of filtering. (key=value)')
    return parser.parse_args()


def get_resources(target: str) -> list:
    if not target.startswith('http'):
        target = 'http://' + target

    url = urllib.urljoin(target, '/api/v1/query?query=aws_resource_info')
    req = request.Request(url, method='GET')

    with request.urlopen(req) as client:
        data = client.read()
        return json.loads(data.decode())


def parse_resources(raw_data: list) -> typing.Generator:
    for item in iter(raw_data['data']['result']):
        yield item['metric']


def filter_resources(parsed_data: typing.Generator, field: str) -> typing.Generator:
    (field_key, field_val) = field.split('=')

    for item in parsed_data:
        if (item.get(field_key, '') == field_val):
            for (key, val) in item.items():
                yield (key, val)


def print_resources(filtered_data: typing.Generator) -> None:
    for (key, val) in filtered_data:
        if key != '__name__':
            print('{}: {}'.format(key, val))

        else:
            print()


if __name__ == '__main__':
    try:
        args = get_args()
        data = get_resources(args.target)
        data = parse_resources(data)
        data = filter_resources(data, args.filter)
        print_resources(data)

    except Exception:
        traceback.print_exc()
