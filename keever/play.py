import sys
sys.path.append(".")

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--logfile", default="keever.log")
args = parser.parse_args()

from keever.algorithm import ModelManager
import yaml
from types import SimpleNamespace
import numpy as np


import logging
import os
if os.path.isfile(args.logfile):
    os.remove(args.logfile)
fh = logging.FileHandler(args.logfile)
sh = logging.StreamHandler()
fh.setLevel(logging.DEBUG)
sh.setLevel(logging.WARN)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        fh,
        sh
    ]
)


config = yaml.safe_load(open(args.project, "r"))
mm = ModelManager()
mm.load_state_dict(config)

global_vars = SimpleNamespace()
state = global_vars.state = SimpleNamespace(running=True, iterations=0)


logging.getLogger().setLevel(logging.INFO)


def varpath(root, path):
    cur = root
    for p in path:
        if p in cur.__dict__:
            cur = cur.__dict__[p]
        else:
            logging.error(f"Variable not found {path}.")
            exit()
            return None
    return cur

def var(x):
    if isinstance(x, str):
        if list(x)[0] == '@':
            return mm.get(x.replace("@",""))
        elif list(x)[0] == '#':
            path = x.replace("#","").split(".")
            return varpath(global_vars, path)
        else:
            return x
    else:
        return x

def play_action(action):
    global state
    logging.debug(f"Playing {action=}")
    if action.type == "serialize":
        ret = mm.get(action.item).serialize("json", action.filename)
    elif action.type == "dump_npz":
        filepath = action.directory + "/" + action.filename
        saved_dict = { e: global_vars.__dict__[e] for e in action.args }
        np.savez_compressed(filepath, **saved_dict)
        ret = filepath
    elif action.type == "action":
        ret = mm.get(action.item).action(action.action, args={ key: var(value) for key, value in action.args.items()})
    elif action.type == "log-info":
        logging.info(action.msg.format(*[var(x) for x in action.args]))
    elif action.type == "update-entries":
        mm.get(action.item).update_entries(action.tags, {key: var(value) for key, value in action.values.items() })
    elif action.type == "clear":
        mm.get(action.item).clear()
    elif action.type == "merge":
        target = mm.get(action.target)
        mm.get(action.item).merge(target)

    elif action.type == "stop":
        if "loops" in action.__dict__:
            if action.loops <= state.iterations:
                state.running = False
        else:
            state.running = False
    else:
        logging.error(f"(action) Unknown Action {action.type}")

    if hasattr(action, "output"):
        if "type" in action.output and action.output["type"] == "copydict":
            for key in ret.keys():
                global_vars.__dict__[key] = ret[key]

        elif isinstance(action.output, list):
            if isinstance(ret, list):
                for key, value in zip(action.output, ret):
                    global_vars.__dict__[key] = value
            elif isinstance(ret, dict):
                for key in action.output:
                    if key not in ret.keys():
                        logging.error(f"[action.output] Key {key} is not in returned dict.")
                        exit()
                    global_vars.__dict__[key] = ret[key]
        else:
            global_vars.__dict__[action.output] = ret

for i, action in enumerate(config["playbook"]["init"]):
    if not state.running:
        logging.info("Playbook is over.")
        break
    action = SimpleNamespace(**action)
    play_action(action)

if not "loop" in config["playbook"]:
    exit()

while state.running:
    for i, action in enumerate(config["playbook"]["loop"]):
        action = SimpleNamespace(**action)
        play_action(action)
    state.iterations += 1


#mm.get("doe").save("doe-no-evaluations")
#result = mm.get("fom").action("evaluate-dummy", args={"x": [10, 10]})
#best_fitness = mm.get("opt").reload().action("optimize", args={"fom": mm.get("fom"), "doe": mm.get("doe")})
