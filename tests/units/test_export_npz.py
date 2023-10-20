import unittest
import sys
sys.path.append("./tests/units/")
from keever.algorithm import ModelManager
import yaml
from os.path import isfile
import numpy as np

class ExportBasic(unittest.TestCase):
    def test_launch(self):
        with open("tests/units/resources/exporttest.yml", "r") as file:
            config = yaml.safe_load(file)
        mm = ModelManager()
        mm.load_state_dict(config)
        export_filename = mm.get("pop").export("npz.variables")
        assert(isfile(export_filename))
        d = np.load(export_filename)
        assert(d["variables"].shape == (25, 10))
        assert(np.all(np.abs(d["variables"]) <= 1.0))
        assert(np.all(~np.isnan(d["variables"])))


