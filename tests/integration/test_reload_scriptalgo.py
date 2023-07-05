import unittest

import sys
sys.path.append(".")
from keever.algorithm import ModelManager
import yaml

class ScriptAlgo(unittest.TestCase):
    def test_lauch(self):
        mm = ModelManager()
        with open("tests/integration/resources/test_scriptalgo.yml", "r") as f:
            config = yaml.safe_load(f)
            mm.load_state_dict(config)
        mm.get("algo").action("run", args={})

    def test_reload_and_lauch(self):
        mm = ModelManager()
        with open("tests/integration/resources/test_scriptalgo.yml", "r") as f:
            config = yaml.safe_load(f)
        mm.load_state_dict(config)
        mm.get("algo").reload().action("run", args={})

    def test_sequence(self):
        mm = ModelManager()
        with open("tests/integration/resources/sequence.yml", "r") as f:
            config = yaml.safe_load(f)
        mm.load_state_dict(config)
        mm.get("sequence").action("test", args={"var1": 0})

