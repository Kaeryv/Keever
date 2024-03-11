import sys
sys.path.append(".")

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument("--project")
args = parser.parse_args()

import logging
from keever.algorithm import ModelManager
import yaml
from types import SimpleNamespace

config = yaml.safe_load(open(args.project, "r"))
mm = ModelManager()
mm.load_state_dict(config)

global_vars = {}
logging.getLogger().setLevel(logging.INFO)


def var(x):
    if list(x)[0] == '@':
        return mm.get(x.replace("@",""))
    elif list(x)[0] == '#':
        return global_vars[x.replace("#","")]
    else:
        return x

for i, action in enumerate(config["playbook"]["init"]):
    action = SimpleNamespace(**action)
    if action.type == "save":
        ret = mm.get(action.item).save(**action.args)
    elif action.type == "action":
        ret = mm.get(action.item).action(action.action, args={ key: var(value) for key, value in action.args.items()})
    elif action.type == "log-info":
        logging.info(action.msg.format(*[var(x) for x in action.args]))
    else:
        logging.error(f"Unknown Action {action.type}")

    if hasattr(action, "output"):
        global_vars[action.output] = ret


mm.get("doe").save("doe-no-evaluations")
result = mm.get("fom").action("evaluate-dummy", args={"x": [10, 10]})
best_fitness = mm.get("opt").reload().action("optimize", args={"fom": mm.get("fom"), "doe": mm.get("doe")})
