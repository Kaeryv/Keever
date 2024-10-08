import subprocess
import re
import os
import sys
from os.path import isfile, join
from os import remove
from time import sleep
from keever.tools import randid
import logging
from copy import copy
from .tools import str_rm_substrings

from keever import TMPDIR

def module_checks(module):
    if not hasattr(module, "__run__"):
        logging.critical(f"[Error][ModuleRunner] Module file {module.__file__} has no __run__ function.")
        exit()
    if not hasattr(module, "__requires__"):
        logging.warning(f"[Warning][ModuleRunner] Module file {module.__file__} has no __requires__ function, assuming defaults.")

def ensure_arguments_match(required, provided):
    r = set(required)
    p = set(provided)

    if not r.issubset(p):
        logging.critical("Error: Not enough arguments.")
        logging.error("List of missing arguments:")
        missing = r.difference(p)
        for m in missing:
            logging.error(f" - {m}")
        exit()
    if r.issubset(p) and r != p:
        logging.warning("Excess arguments will be ignored:")
        excess = p.difference(r)
        for e in excess:
            logging.warning(f" - {e}")


action_types = ["module_runner", "script_runner", "sequence_runner"]
def load_action(data):
    at = data["type"]
    assert(at in action_types)
    if at == "module_runner":
        return ModuleRunner.from_json(data)
    elif at == "script_runner":
        return ScriptRunner.from_json(data)
    elif at == "sequence_runner":
        return SequenceRunner.from_json(data)
    else:
        print(f"Unknown runner type: {at}.")
        exit()

def load_action_list(data):
    return dict([(action["name"], load_action(action)) for action in data])

def wait_files(files, sleep_time=60):
    logging.info(f"[wait_files] There are {len(files)} touchfiles.")
    file_present = [ False for file in files ]
    while True:
        for i, file in enumerate(files):
            if not file_present[i]:
                logging.debug(f"[wait_files] Looking for {file}")
                file_present[i] = isfile(file)
        if all(file_present):
            logging.debug("[wait_files] All touchfiles exist")
            for file in files:
                remove(file) 
            break

        sleep(sleep_time)

class RunnerVariable:
    def __init__(self, src) -> None:
        self.src = copy(src)
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

class SequenceRunner:
    def __init__(self, name, actions=[]) -> None:
        self.actions = actions
        self.global_variables = []
        self.name = name

    @property
    def state_dict(self):
        return {"name": self.name, "type": "sequence_runner","actions": [ value.state_dict for value in self.actions.values() ]}

    @classmethod
    def from_json(cls, data):
        return cls(data["name"], load_action_list(data["actions"]))

    def run_with_dict(self, dictionnary: dict):
        conf = copy(dictionnary)

        for action in self.actions.values():
            vars = {key: conf[key] for key in action.requirements["variables"] if key in conf}
            returns = action.run_with_dict(vars)
            if returns:
                conf.update(returns) 
        return conf

class ModuleRunner():
    def __init__(self, name, path, workdir=".") -> None:
        self.m = load_module(path)
        module_checks(self.m)
        self.name = name
        self.path = path
        self._required_variables = dict()
        self._workdir = workdir
        
        variables = []
        if hasattr(self.m, "__requires__"):
            variables = self.m.__requires__()["variables"]

        for req in variables:
            newvar = RunnerVariable(req)
            self._required_variables[newvar.name] = newvar

    @property
    def workdir(self):
        return self._workdir
    @workdir.setter
    def workdir(self, value):
        self._workdir = value
        os.makedirs(value, exist_ok=True)
        
        

    def run_with_dict(self, dictionnary: dict):
        for key in dictionnary.keys():
            if key not in self._required_variables:
                logging.warning(f"[ModuleRunner/{self.name}] variable '{key}' was not in requirements.")

        return self.m.__run__(**dictionnary)
    
    @property
    def requirements(self):
        return self.m.__requires__()
    
    @property
    def declares(self):
        return self.m.__declares__()

    @property
    def state_dict(self):
        return {"name": self.name, "path": self.path, "type": "module_runner", "workdir": "./wd/" }

    @classmethod
    def from_json(cls, data):
        return cls(data["name"], data["path"], workdir=data["workdir"])

    @property
    def variables(self):
        return list(self._required_variables.keys())

class ScriptRunner:
    def __init__(self, name, path, shell="bash", parallel=False, workdir=".") -> None:
        self.path = path
        self.shell = shell
        self.content = ""
        self._required_variables = dict()
        self.build_from_script(path)
        self.parallel = parallel
        self._workdir = workdir
        self.name = name

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
        '''
            Reads the prototype <any> shell script.
            There should be {{statements}} that we can interpret to define I/O
        '''
        assert (os.path.isfile(path) and path.endswith(".proto.sh")),\
                f"Prototype {path} required does not exist."
        with open(path, "r") as f:
            self.content = f.read()
            statements = [ str_rm_substrings(r, ["{{","}}"]) for r in  re.findall(r'\{\{.*?\}\}', self.content)]
            statements = list(set(statements))
            for statement in statements:
                variable = RunnerVariable(statement)
                self._required_variables[variable.name] = variable
        
        self.array = False
        self.array_var = None
        for name, var in self._required_variables.items():
            self.array |= var.array
            if var.array:
                self.array_var = name

    def run_with_dict(self, dictionnary: dict):
        assert "touchfile" in self._required_variables, f"Set touchfile in {self.path}"
        dictionnary.update({"touchfile": f"{self.workdir}/{randid()}.ended"})
        for name in self.generated_files:
            metavar = self._required_variables[name]
            file = f"{self.workdir}/{name}.{randid()}.npz"
            dictionnary[metavar.name] = file

        src_dictionnary = dict()
        exported_filenames = list()
        for name, value in dictionnary.items():
            if name not in self._required_variables:
                logging.warn(f"Unused variable {name}")
                continue
            metavar = self._required_variables[name]
            if hasattr(value,"export"):
                src_dictionnary[metavar.src] = value.export(metavar.type)
                exported_filenames.append(src_dictionnary[metavar.src])
            elif isinstance(value,list) and not metavar.array:
                src_dictionnary[metavar.src] = " ".join(map(str, value))
            else:
                src_dictionnary[metavar.src] = value
        
        script_files = list()
        if self.array:
            logging.debug("Running array job.")
            touchfiles = list()
            returns = { var: [] for var in self.declares }
            for i, value in enumerate(dictionnary[self.array_var]):
                logging.debug(f" - {value}")
                src_dictionnary.update({"touchfile": dictionnary["touchfile"].replace(".ended", f".{i}.ended")})
                src_dictionnary.update({self._required_variables[self.array_var].src: value})

                for name in self.generated_files:
                    metavar = self._required_variables[name]
                    src_dictionnary[metavar.src] = dictionnary[metavar.name].replace(name, f"{name}.{i}.")
                ensure_arguments_match(self.variables, dictionnary.keys())
                script_files.append(generate_job(self.content, src_dictionnary, launch=True, shell=self.shell, name=self.path))
                touchfiles.append(src_dictionnary["touchfile"])
                [ returns[name].append(src_dictionnary[self._required_variables[name].src]) for name in self.declares]
            wait_files(touchfiles, sleep_time=10)

        else:
            ensure_arguments_match(self.variables, dictionnary.keys())
            script_files.append(generate_job(self.content, src_dictionnary, launch=True, shell=self.shell, name=self.path))
            wait_files([src_dictionnary["touchfile"]],sleep_time=10)
            returns = { var: dictionnary[var] for var in self.declares }
        
        for file in script_files:
            os.remove(file)

        # Removing files created for export
        for name in exported_filenames:
            os.remove(name)

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
        return {"name": self.name, "type": "script_runner", "path": self.path, "content": self.content, "workdir":self.workdir, "shell":self.shell, "_required_variables": {key: val.state_dict for key,val in self._required_variables.items()}, "parallel":self.parallel  }


    @classmethod
    def from_json(cls, data):
        return cls(data["name"], data["path"], data["shell"], data["parallel"], workdir=data["workdir"])


def generate_job(prototype, dictionnary, launch=False, shell="bash", name="./submit.sh"):
    '''
        Generates a runnable instance of a prototype shell script.
        prototype: The shell script to be completed
        dictionnary: Variables required to complete the script
        launch: whether to write and launch the script on completion
        shell: The shell to run the script with
    '''
    completed_script = copy(prototype)
    for key, value in dictionnary.items():
        completed_script = completed_script.replace(f'{{{{{key}}}}}', str(value))

    
    if launch:
        logging.debug("Launching job")
        os.makedirs("./tmp/", exist_ok=True)

        script_name = os.path.basename(name).replace(".proto.", f".{randid(5)}.")
        script_name = join(TMPDIR, script_name)
        with open(script_name, "w") as f2:
            f2.write(completed_script)
        subprocess.call([shell, script_name], shell=False)
        return script_name
    else:
        return completed_script  
