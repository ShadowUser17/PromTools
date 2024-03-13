#!/usr/bin/env python3
import sys
import json
import logging
import argparse
import traceback

from urllib import request
from urllib import parse as urllib


def configure_logger() -> None:
    logging.basicConfig(
        format=r'%(levelname)s [%(asctime)s]: "%(message)s"',
        datefmt=r'%Y-%m-%d %H:%M:%S', level=logging.INFO
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='target', default='http://127.0.0.1:9090', help='Set Prometheus address.')
    parser.add_argument('labels', help='Set list of labels. (label,...)')
    return parser.parse_args()


def get_values(target: str, label: str) -> list:
    url = urllib.urljoin(target, 'api/v1/label/{}/values'.format(label))
    req = request.Request(url, method='GET')

    logging.info("{} {}".format(req.method, req.full_url))
    with request.urlopen(req) as client:
        data = client.read().decode()
        data = json.loads(data)
        return data.get('data', [])


try:
    configure_logger()
    args = parse_args()

    target = args.target
    if not target.startswith('http'):
        target = 'http://' + target

    labels = args.labels.split(',')
    for item in labels:
        data = get_values(target, item)
        logging.info('{}:\n - {}\n'.format(item, '\n - '.join(data)))

except Exception:
    logging.error(traceback.format_exc())
    sys.exit(1)
