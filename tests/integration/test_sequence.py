import sys
sys.path.append(".")
from keever.algorithm import ModelManager
import yaml

config = yaml.safe_load(open("tests/integration/resources/sequence.yml", "r"))
mm = ModelManager()
mm.load_state_dict(config)
mm.get("sequence").action("test", args={"var1": 0})
