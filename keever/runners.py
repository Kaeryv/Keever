import subprocess
import re
import os
import sys
from os.path import isfile
from os import remove
from time import sleep
import uuid

def module_checks(module):
    if not hasattr(module, "__run__"):
        print(f"[Error][ModuleRunner] Module file {module.__file__} has no __run__ function.")
        exit()
    if not hasattr(module, "__requires__"):
        print(f"[Warning][ModuleRunner] Module file {module.__file__} has no __requires__ function, assuming defaults.")

def ensure_arguments_match(required, provided):
    r = set(required)
    p = set(provided)

    if not r.issubset(p):
        print("Error: Not enough arguments.")
        print("List of missing arguments:")
        missing = r.difference(p)
        for m in missing:
            print(f" - {m}")
        exit()
    if r.issubset(p) and r != p:
        print("Excess arguments will be ignored:")
        excess = p.difference(r)
        for e in excess:
            print(f" - {e}")


action_types = ["module_runner", "script_runner", "sequence_runner"]
def load_action(data):
    for at in action_types:
        if at in data.keys():
            if at == "module_runner":
                return data[at], ModuleRunner.from_json(data)
            elif at == "script_runner":
                return data[at], ScriptRunner.from_json(data)
            elif at == "sequence_runner":
                return data[at], SequenceRunner.from_json(data)

def load_action_list(data):
    actions = {}
    for action in data:
        key, value = load_action(action)
        actions.update({ key: value })
    return actions

def wait_files(files, sleep_time=60):
    while True:
        all_files_present = True
        for file in files:
            all_files_present &= isfile(file)
        if all_files_present:
            for file in files:
                remove(file) 
            break
        sleep(sleep_time)

class RunnerVariable:
    def __init__(self, src) -> None:
        self.src = src
        self.array = False
        self.name = self.src
        if "[]" in src:
            self.array = True
            self.name = self.name.replace("[]","")
        if ":" in self.name:
            src = self.name.split(":")
            self.name = src[0]
            self.type = src[1]
        else:
            self.type = "object"

        
    @property
    def state_dict(self):
        return vars(self)

    @classmethod
    def from_json(cls, data):
        return cls(data["src"])

def load_module(module):
    module_path = module

    if module_path in sys.modules:
        return sys.modules[module_path]

    return __import__(module_path, fromlist=[module])

from copy import copy
class SequenceRunner:
    def __init__(self, actions=[]) -> None:
        self.actions = actions
        self.global_variables = []

    @property
    def state_dict(self):
        return {"__object_type__": "SequenceRunner","actions": { key: value.state_dict for key, value in self.actions.items()}}

    @classmethod
    def from_json(cls, data):
        return cls(load_action_list(data["actions"]))

    def run_with_dict(self, dictionnary: dict):
        conf = copy(dictionnary)

        for action in self.actions.values():
            vars = {key: conf[key] for key in action.requirements["variables"] if key in conf}
            returns = action.run_with_dict(vars)
            if returns:
                conf.update(returns) 
        return conf

class ModuleRunner():
    def __init__(self, name, workdir=".") -> None:
        self.m = load_module(name)
        module_checks(self.m)
        self.name = name
        self._required_variables = dict()
        self._workdir = workdir

    @property
    def workdir(self):
        return self._workdir
    @workdir.setter
    def workdir(self, value):
        self._workdir = value
        os.makedirs(value, exist_ok=True)
        
        variables = []
        if hasattr(self.m, "__requires__"):
            variables = self.m.__requires__()["variables"]

        for req in variables:
            newvar = RunnerVariable(req)
            self._required_variables[newvar.name] = newvar

    def run_with_dict(self, dictionnary: dict):
        for key in dictionnary.keys():
            if not key in self._required_variables:
                print(f"[Warning][ModuleRunner] variable '{key}' was not in requirements.")

        return self.m.__run__(**dictionnary)
    
    @property
    def requirements(self):
        return self.m.__requires__()
    
    @property
    def declares(self):
        return self.m.__declares__()

    @property
    def state_dict(self):
        return {"path": self.name, "algorithm": "module_runner", "workdir": "./wd/" }

    @classmethod
    def from_json(cls, data):
        return cls(data["path"], workdir=data["workdir"])

    @property
    def variables(self):
        return list(self._required_variables.keys())

class ScriptRunner:
    def __init__(self, path, shell="bash", parallel=False, workdir=".") -> None:
        self.path = path
        self.shell = shell
        self.content = ""
        self._required_variables = dict()
        self.build_from_script(path)
        self.parallel = parallel
        self._workdir = workdir

    @property
    def workdir(self):
        return self._workdir
    @workdir.setter
    def workdir(self, value):
        self._workdir = value
        os.makedirs(value, exist_ok=True)
    @property
    def variables(self):
        return list(self._required_variables.keys())

    def build_from_script(self, path: str):
        assert os.path.isfile(path) and path.endswith(".proto.sh")
        with open(path, "r") as f:
            self.content = f.read()
            variables = [ r.replace("{{", "").replace("}}","") for r in  re.findall(r'\{\{.*?\}\}', self.content)]
            variables = list(set(variables))
            for req in variables:
                newvar = RunnerVariable(req)
                self._required_variables[newvar.name] = newvar
        
        self.array = False
        self.array_var = None
        for name, var in self._required_variables.items():
            self.array |= var.array
            if var.array:
                self.array_var = name

    def run_with_dict(self, dictionnary: dict):
        dictionnary.update({"touchfile": f"{self.workdir}/{str(uuid.uuid1())}.ended"})
        for name in self.generated_files:
            metavar = self._required_variables[name]
            file = f"{self.workdir}/{name}.{str(uuid.uuid1())}.npz"
            dictionnary[metavar.name] = file
        #print(set(self.variables) , set(dictionnary.keys()))

        src_dictionnary = dict()
        for name, value in dictionnary.items():
            metavar = self._required_variables[name]
            if hasattr(value,"export"):
                src_dictionnary[metavar.src] = value.export(metavar.type)
            elif isinstance(value,list) and not metavar.array:
                src_dictionnary[metavar.src] = " ".join(map(str, value))
            else:
                src_dictionnary[metavar.src] = value
        if self.array:
            print("Running array job.")
            touchfiles = list()
            returns = { var: [] for var in self.declares }
            for i, value in enumerate(dictionnary[self.array_var]):
                print(f" - {value}")
                src_dictionnary.update({"touchfile": dictionnary["touchfile"].replace(".ended", f".{i}.ended")})
                src_dictionnary.update({self._required_variables[self.array_var].src: value})

                for name in self.generated_files:
                    metavar = self._required_variables[name]
                    src_dictionnary[metavar.src] = dictionnary[metavar.name].replace(name, f"{name}.{i}.")
                ensure_arguments_match(self.variables, dictionnary.keys())
                generate_job(self.content, src_dictionnary, launch=True, shell=self.shell)
                touchfiles.append(src_dictionnary["touchfile"])
                [ returns[name].append(src_dictionnary[self._required_variables[name].src]) for name in self.declares]
            wait_files(touchfiles, sleep_time=10)

        else:
            ensure_arguments_match(self.variables, dictionnary.keys())
            generate_job(self.content, src_dictionnary, launch=True, shell=self.shell)
            wait_files([src_dictionnary["touchfile"]],sleep_time=10)
            returns = { var: dictionnary[var] for var in self.declares }

        return returns



    @property
    def requirements(self):
        return {"variables" : self.variables , "type": ("single", "parallel")[self.parallel]}

    @property
    def declares(self):
        return [ m.name for m in self._required_variables.values() if m.type=="declare_output" or m.type == "declare_file_output"]
    
    @property
    def generated_files(self):
        return [ m.name for m in self._required_variables.values() if m.type == "declare_file_output"]
    
    @property
    def state_dict(self):
        return {"__object_type__": "ScriptRunner", "path": self.path, "content": self.content, "workdir":self.workdir, "shell":self.shell, "_required_variables": {key: val.state_dict for key,val in self._required_variables.items()}, "parallel":self.parallel  }


    @classmethod
    def from_json(cls, data):
        return cls(data["path"], data["shell"], data["parallel"], workdir=data["workdir"])
def generate_job(current, dictionnary, launch=False, shell="bash"):
    for key, value in dictionnary.items():
        current = current.replace(f'{{{{{key}}}}}', str(value))
    
    if launch:
        os.makedirs("./tmp/", exist_ok=True)

        with open("./tmp/submit.now.sh", "w") as f2:
            f2.write(current)
        subprocess.call(f"{shell} ./tmp/submit.now.sh", shell=True)
