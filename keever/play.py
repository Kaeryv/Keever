import sys
sys.path.append(".")

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument("--project", required=True)
args = parser.parse_args()

import logging
from keever.algorithm import ModelManager
import yaml
from types import SimpleNamespace
import numpy as np

config = yaml.safe_load(open(args.project, "r"))
mm = ModelManager()
mm.load_state_dict(config)

global_vars = {}
logging.getLogger().setLevel(logging.INFO)


def var(x):
    if isinstance(x, str):
        if list(x)[0] == '@':
            return mm.get(x.replace("@",""))
        elif list(x)[0] == '#':
            return global_vars[x.replace("#","")]
        else:
            return x
    else:
        return x

for i, action in enumerate(config["playbook"]["init"]):
    action = SimpleNamespace(**action)
    logging.info(f"Playing {action=}")
    if action.type == "serialize":
        ret = mm.get(action.item).serialize(**action.args)
    elif action.type == "dump_npz":
        filepath = action.directory + "/" + action.filename
        saved_dict = { e: global_vars[e] for e in action.args }
        np.savez_compressed(filepath, **saved_dict)
        ret = filepath
    elif action.type == "action":
        ret = mm.get(action.item).action(action.action, args={ key: var(value) for key, value in action.args.items()})
    elif action.type == "log-info":
        logging.info(action.msg.format(*[var(x) for x in action.args]))
    else:
        logging.error(f"Unknown Action {action.type}")

    if hasattr(action, "output"):
        if isinstance(action.output, list):
            for key, value in zip(action.output, ret):
                global_vars[key] = value
        else:
            global_vars[action.output] = ret


#mm.get("doe").save("doe-no-evaluations")
#result = mm.get("fom").action("evaluate-dummy", args={"x": [10, 10]})
#best_fitness = mm.get("opt").reload().action("optimize", args={"fom": mm.get("fom"), "doe": mm.get("doe")})
