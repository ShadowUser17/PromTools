import os
import sys
import yaml
import logging
import pathlib
import argparse

from kubernetes import config as k8s_config
from kubernetes import client as k8s_client


def configure_logger() -> None:
    log_level = logging.DEBUG if os.environ.get("DEBUG_MODE", "") else logging.INFO
    logging.basicConfig(
        format=r'%(levelname)s [%(asctime)s]: "%(message)s"',
        datefmt=r'%Y-%m-%d %H:%M:%S', level=log_level
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', dest='namespace', default="default", help='Set resource namespace.')
    parser.add_argument('-d', dest='directory', default='rules', help='Set rules directory.')
    return parser.parse_args()


def get_namespaced_custom_objects(client: any, namespace: str) -> list:
    resource_group = "monitoring.coreos.com"
    resource_version = "v1"
    resource_type = "prometheusrules"

    logging.debug("Run: get_namespaced_custom_objects({})".format(namespace))
    res = client.list_namespaced_custom_object(resource_group, resource_version, namespace, resource_type)
    return res.get("items", [])


def dump_custom_object(base_dir: str, item: dict) -> None:
    logging.debug("Run: dump_custom_object()")
    path = pathlib.Path(base_dir)
    path.mkdir(exist_ok=True)

    path = path.joinpath(item["metadata"]["name"])
    logging.info("Dump: {}".format(path))
    path.write_text(yaml.dump(item.get("spec", {})))


try:
    configure_logger()
    args = parse_args()

    k8s_config.load_kube_config()
    client = k8s_client.CustomObjectsApi()

    for item in get_namespaced_custom_objects(client, args.namespace):
        dump_custom_object(args.directory, item)

except Exception:
    logging.exception(__name__)
    sys.exit(1)
