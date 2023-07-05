import os
from copy import deepcopy
import json
from .runners import load_action, load_action_list
from .database import Database

class ModelManager:
    def __init__(self, workdir=".") -> None:
        self.items = {}
        self._workdir = workdir

    def load_state_dict(self, state):
        self._workdir = state["workdir"]
        if "datasets" in state.keys():
            for db in state["datasets"]:
                self.add(Database.from_json(db))
        if "algorithms" in state.keys():
            for content in state["algorithms"]:
                self.add(Algorithm.from_json(content))

    def add(self, obj):
        self.items[obj.name] = obj
        obj.workdir = self._workdir
        return self.items[obj.name]

    def get(self, key):
        return self.items[key]
        

from os.path import join

class Algorithm():
    def __init__(self, name, actions={}, config={}) -> None:
        self.actions = actions
        self.config = config
        self._workdir = "."
        self.name = name

    @property
    def workdir(self):
        return self._workdir
    
    @workdir.setter
    def workdir(self, value):
        if value:
            self._workdir = value
            os.makedirs(value, exist_ok=True)

    def reload(self):
        for key, action in self.actions.items():
            self.actions[key] = load_action(action.state_dict)
        return self
        
    def action(self, name, args={}):
        action = self.actions[name]
        action.workdir = self.workdir
        conf = deepcopy(self.config)
        conf.update(args)
        return action.run_with_dict(conf)
    
    @property
    def state_dict(self):
        return {"actions": [value.state_dict for value in self.actions.values() ], "config": self.config, "workdir": self.workdir, "name": self.name}
    
    @classmethod
    def from_json(cls, data):
        obj = Algorithm(data["name"])
        obj._workdir = data["workdir"] if "workdir" in data.keys() else None
        obj.actions.update(load_action_list(data["actions"]))
        obj.config = data["config"] if "config" in data else {}
        return obj

    def export(self, type):
        filepath = join(self.workdir, self.name + ".json")
        if type == "serialize":
            with open(filepath, "w") as f:
                json.dump(self.state_dict, f)
            
        return filepath
