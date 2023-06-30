import os
USER = os.getenv('USER')

# Try to find a temporary directory
if os.getenv("KEEVER_TMP"):
    TMPDIR = os.getenv('TMP')
elif os.getenv('TMP'):
    TMPDIR = os.getenv('TMP')
else:
    TMPDIR = "./tmp/"

os.makedirs(TMPDIR, exist_ok=True)

import sys
sys.path.append(".")
sys.path.append("./user/")


import json
import numpy as np

def load(path):
    with open(path, "r") as f:
        return json.load(f)


