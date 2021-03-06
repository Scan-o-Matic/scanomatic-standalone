#!/usr/bin/env python3.9
"""Part of analysis work-flow that holds a grid arrays"""
import os

__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson", "Mats Kvarnstroem", "Andreas Skyman", ""]
__license__ = "GPL v3.0"
__version__ = "v3.0.0"
__maintainer__ = "Martin Zackrisson"
__status__ = "Development"

__branch = "dev"


def get_version() -> str:
    return __version__


def get_branch() -> str:
    return __branch


def get_location() -> str:
    return os.path.dirname(__file__)
