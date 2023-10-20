import os
from copy import deepcopy
import json
from .runners import load_action, load_action_list
from .database import Database
from .tools import serialize_json
from attrs import define, field, Factory


@define
class ModelManager:
    items:       dict = field(init=False, default=Factory(dict))
    _workdir:    str = field(init=False, default=".")

    def load_state_dict(self, state_dict):
        self._workdir = state_dict["workdir"] if "workdir" in state_dict.keys() else "."
        for e in state_dict["items"]:
            if e["type"] == "Database":
                self.add(Database.from_json(e))
            elif e["type"] == "Algorithm":
                self.add(Algorithm.from_json(e))

    def add(self, obj):
        self.items[obj.name] = obj
        if hasattr(obj, "workdir"):
            obj.workdir = self._workdir
        return self.items[obj.name]

    def get(self, key):
        return self.items[key]
    
    @property    
    def state_dict(self):
        return {"items": [ item.state_dict for item in self.items.values()], "_workdir": self._workdir }

    def save(self, filename):
        serialize_json(self.state_dict, filename)



from os.path import join

@define
class Algorithm():
    actions: dict = field(init=False, default=Factory(dict))
    config:  dict = field(init=False, default=Factory(dict))
    _workdir: str = field(init=False, default=".")
    name:     str = field(init=True)

    def __repr__(self) -> str:
        return f"Algorithm {self.name} with {len(self.actions)} actions."

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
        return {"actions": [value.state_dict for value in self.actions.values() ], "config": self.config, "workdir": self.workdir, "name": self.name, "type": "Algorithm"}
    
    @classmethod
    def from_json(cls, data):
        obj = cls(data["name"])
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
