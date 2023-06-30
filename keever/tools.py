from typing import Any, AnyStr

import os
from os.path import join


import json
from json import JSONEncoder

import numpy as np 

def ensure_file_directory_exists(file):
    folder_path = os.path.split(file)[0]
    if folder_path != "":
        os.makedirs(folder_path, exist_ok=True)




class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

def JSON(path):
    with open(path, "r") as f:
        return json.load(f)


def serialize_json(object: Any, path: AnyStr):
    path = path if path.endswith('.json') else path + ".json"
    with open(path, "w") as f:
        return json.dump(object, f, cls=NumpyArrayEncoder)
