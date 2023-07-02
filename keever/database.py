import uuid
import numpy as np
from scipy.stats.qmc import LatinHypercube
import os
from keever.tools import serialize_json

def count_continuous_variables(variables_description):
    count = 0
    for var in variables_description:
        if "size" in var.keys():
            count += var["size"]
        else:
            count += 1
    return int(count)

def countinuous_variables_boundaries(variables_description):
    varcount = count_continuous_variables(variables_description)
    bounds = np.zeros((2, varcount))
    cur = 0
    for i, var in enumerate(variables_description):
        lc = var["size"] if "size" in var else 1
        bounds[0, cur:cur+lc] = var["lower"]
        bounds[1, cur:cur+lc] = var["upper"]
        cur += lc
    return bounds



class Database:
    def __init__(self, name="untitled", variables_descr={}, storages=[]) -> None:
        if variables_descr:
            self.variables_descr = variables_descr["params"]
        self.storage_descr = storages
        self._data = { key: {} for key in storages}
        self._data.update({"variables": {}})
        self._workdir = "."
        self.exporters = {}
        self.name = name

    def load_state_dict(self, data):
        self.name = data["name"]
        self.variables_descr = data["variables"] if "variables" in data else {}
        self.exporters = data["exporters"] if "exporters" in data else {}
        self._data = { "variables": {} }
        self._data.update({ key: {} for key in data["storages"] } if "storages" in data else {})
        if "populate-on-creation" in data.keys() and data["populate-on-creation"]:
            self.populate(data["populate-on-creation"]["algo"], data["populate-on-creation"]["count"])
        return self
    
    @property
    def entries(self):
        return list(self._data["variables"].keys())
    @property
    def state_dict(self, include_data=True):
        ret = {
            "storage": self.storage_descr,
            "workdir": self.workdir,
            "exporters": self.exporters,
            "name": self.name,
            "variables": self.variables_descr
        }
        if include_data:
            ret.update({"_data": self._data})
        return ret
    
    def save(self, path):
        serialize_json(self.state_dict, path)
        return self
    
    @classmethod
    def from_json(cls, data):
        return cls().load_state_dict(data)
    
    def __len__(self):
        return len(self._data["variables"])
    
    def __iter__(self):
        class DatabaseIterator:
            def __init__(self, db) -> None:
                self.current = 0
                self.db = db
            def __next__(self):
                if self.current < len(self.db.entries):
                    entry = self.entries[self.db.current]
                    self.current += 1
                    return entry, self.db[entry]
                else:
                    raise StopIteration
        
        return DatabaseIterator(self)



    @property
    def workdir(self):
        return self._workdir
    
    def clear(self):
        for key in self._data.keys():
            self._data[key].clear()
    
    @workdir.setter
    def workdir(self, value):
        self._workdir = value
        os.makedirs(value, exist_ok=True)

    def add_entry(self, name, dictionnary):
        for key in dictionnary.keys():
            self._data[key][name] = dictionnary[key]
        
    def merge(self, lhs):
        for key in self._data.keys():
            self._data[key].update(lhs._data[key])

    def update_entry(self, name, dictionnary):
        for key in dictionnary.keys():
            self._data[key][name] = dictionnary[key]

    def update_entries(self, entries, dictionnary):
        for i, entry in enumerate(entries):
            self.update_entry(entry, {key: dictionnary[key][i] for key in dictionnary.keys()})


    def __getitem__(self, key):
        return { k: self._data[k][key] for k in self._data.keys() if key in self._data[k] }
    
    def store_in_file(self, path, keys):
        tmp = { key: np.asarray([ self._data[key][entity] for entity in self._data[key].keys() ]) for key in keys }
        np.savez_compressed(path, **tmp)

    def export(self,type):
        self.store_in_file(self._workdir + "/db.npz", self.exporters[type])
        return self._workdir + "/db.npz"

    @property
    def num_scalar_variables(self):
        return count_continuous_variables(self.variables_descr)


    def assert_empty(self):
        for key in self._data.keys():
            assert(len(self._data[key]) == 0)
        return self

    def populate(self, algorithm, count):
        print(f"populating with {algorithm} {count} individuals.")
        sampler = LatinHypercube(d=self.num_scalar_variables)
        configs = sampler.random(n=count)
        bounds = countinuous_variables_boundaries(self.variables_descr)
        configs *= (bounds[1] - bounds[0])
        configs += bounds[0]
        for conf in configs:
            individual_name = str(uuid.uuid1())
            self.add_entry(individual_name, {"variables": conf})

        
    def same_variables(self, lhs):
        self.variables_descr = lhs.variables_descr

    def append_npz_keys(self, file, keys):
        d = np.load(file)
        num = d[keys[0]].shape[0]
        for i in range(num):
            individual_name = str(uuid.uuid1())
            self.add_entry(individual_name, { key: d[key][i] for key in keys})


