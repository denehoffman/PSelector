#!/usr/bin/env python3

import yaml
import sys

with open(sys.argv[1], 'r') as stream:
    try:
        print(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        print(exc)
