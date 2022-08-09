#!/usr/bin/env python3
from pathlib import Path

import sys
import argparse
import traceback

try:
    import jinja2

except ImportError:
    print('Missing dependencies!', file=sys.stderr)
    sys.exit(2)


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('env',      help='Set rules env')
    parser.add_argument('source',   help='Set servies list file')
    parser.add_argument('template', help='Set template file')
    parser.add_argument('output',   help='Set output file')
    return parser.parse_args()


try:
    args = get_args()
    env = args.env

    services = Path(args.source).read_text()
    services = list(filter(None, services.split('\n')))
    template = jinja2.Template(Path(args.template).read_text())

    data = template.render(env=env, services=services)
    Path(args.output).write_text(data)

except Exception:
    traceback.print_exc()
    sys.exit(1)
