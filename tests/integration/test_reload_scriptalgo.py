import unittest

import sys
sys.path.append(".")
from keever.algorithm import ModelManager
import yaml

class ScriptAlgo(unittest.TestCase):
    def test_lauch(self):
        config = yaml.safe_load(open("tests/integration/resources/test_scriptalgo.yml", "r"))
        mm = ModelManager()
        mm.load_state_dict(config)
        mm.get("algo").action("run", args={})

    def test_reload_and_lauch(self):
        config = yaml.safe_load(open("tests/integration/resources/test_scriptalgo.yml", "r"))
        mm = ModelManager()
        mm.load_state_dict(config)
        mm.get("algo").reload().action("run", args={})

    def test_sequence(self):
        config = yaml.safe_load(open("tests/integration/resources/sequence.yml", "r"))
        mm = ModelManager()
        mm.load_state_dict(config)
        mm.get("sequence").action("test", args={"var1": 0})

