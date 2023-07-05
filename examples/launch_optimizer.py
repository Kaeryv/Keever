import sys
sys.path.append(".")
from keever.algorithm import ModelManager
import yaml

config = yaml.safe_load(open("examples/example.yaml", "r"))
mm = ModelManager()
mm.load_state_dict(config)
mm.get("doe").save("doe-no-evaluations")
result = mm.get("fom").action("evaluate-dummy", args={"x": [10, 10]})
best_fitness = mm.get("opt").action("optimize", args={"fom": mm.get("fom"), "doe": mm.get("doe")})
