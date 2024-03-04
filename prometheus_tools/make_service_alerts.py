#!/usr/bin/env python3
import sys
import jinja2
import logging
import argparse
import traceback

from pathlib import Path


def configure_logger() -> None:
    logging.basicConfig(
        format=r'%(levelname)s [%(asctime)s]: "%(message)s"',
        datefmt=r'%Y-%m-%d %H:%M:%S', level=logging.INFO
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('env',      help='Set rules env')
    parser.add_argument('source',   help='Set servies list file')
    parser.add_argument('template', help='Set template file')
    parser.add_argument('output',   help='Set output file')
    return parser.parse_args()


try:
    configure_logger()
    args = parse_args()
    env = args.env

    services = Path(args.source).read_text()
    services = list(filter(None, services.split('\n')))
    template = jinja2.Template(Path(args.template).read_text())

    data = template.render(env=env, services=services)
    Path(args.output).write_text(data)

except Exception:
    logging.error(traceback.format_exc())
    sys.exit(1)
