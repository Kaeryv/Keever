import unittest
import sys
sys.path.append("./tests/units/")
from keever.algorithm import ModelManager
from keever.database import Database
from keever.tools import JSON
import yaml
from os.path import isfile, join
from keever import TMPDIR
import numpy as np

class ResumeBasic(unittest.TestCase):
    def test_launch(self):
        with open("tests/units/resources/exporttest.yml", "r") as file:
            config = yaml.safe_load(file)
        mm = ModelManager()
        mm.load_state_dict(config)

        mm.get("pop").save(join(TMPDIR, "resume"))

        pop2 = Database.from_json(JSON(join(TMPDIR, "resume.json")))
        
        mm.save(join(TMPDIR, "resume_mm"))
        mm.load_state_dict(JSON(join(TMPDIR, "resume_mm.json")))
