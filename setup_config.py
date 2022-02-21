#!/usr/bin/env python
import os
from shutil import copyfile


DEFAULT_CONFIG_DIR = "/tmp/data/config"
CONFIG_DIR = "root/.scan-o-matic/config"


def setup_config(
    default_config_dir: str, config_dir: str,
):
    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)
    for filename in os.listdir(default_config_dir):
        source_path = os.path.join(default_config_dir, filename)
        destination_path = os.path.join(config_dir, filename)
        if (
            os.path.isfile(source_path)
            and not os.path.isfile(destination_path)
        ):
            copyfile(source_path, destination_path)
        elif os.path.isdir(source_path):
            setup_config(source_path, destination_path)


if __name__ == "__main__":
    setup_config(DEFAULT_CONFIG_DIR, CONFIG_DIR)
