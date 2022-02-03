#!/usr/bin/env python
import os
from shutil import copyfile


DEFAULT_CONFIG_DIR = "/tmp/data/config"
CONFIG_DIR = "root/.scan-o-matic/config"


def setup_config():
    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    for file in os.listdir(DEFAULT_CONFIG_DIR):
        source_path = os.path.join(DEFAULT_CONFIG_DIR, file)
        destination_path = os.path.join(CONFIG_DIR, file)
        if not os.path.isfile(os.path.join(CONFIG_DIR, file)):
            copyfile(source_path, destination_path)


if __name__ == "__main__":
    setup_config()
