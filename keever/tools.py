from typing import Any, AnyStr
import os
import json
from json import JSONEncoder
import logging
from os.path import join

import uuid

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

def serialize_json(object: Any, path: AnyStr):
    path = path if path.endswith('.json') else path + ".json"
    with open(path, "w") as f:
        return json.dump(object, f, cls=NumpyArrayEncoder)

def randid(length=None):
    if length:
        return str(uuid.uuid1())[:length]
    else:
        return str(uuid.uuid1())

def str_rm_substrings(string, substrings):
    for ss in substrings:
        string = string.replace(ss, "")
    return string

def export_item(obj, exporter_dotstring, filepath=None):
    ''' Used for exporting keever item to any supported format 
    '''
    exporter_args = exporter_dotstring.split(".")
    assert len(exporter_args) > 0, "No exporter was specified"
    exporter = exporter_args[0]
    logging.debug(f"Exporting {obj.name} using {exporter}")
    if exporter == 'object':
        method = exporter_args[1] if len(exporter_args) > 1 else "json"
        filepath = join(obj.workdir, obj.name + ".json") if filepath is None else filepath
        if method == "json":
            serialize_json(obj.state_dict, filepath)
            return filepath
        #elif method == "pickle":
        #    serialize_pickle(obj.state_dict, filepath)
    elif exporter in obj.exporters:
        return obj.export_data(exporter)
