import uuid
import numpy as np
from scipy.stats.qmc import LatinHypercube
import os
from keever.tools import serialize_json
from copy import copy
from keever import TMPDIR 
from os.path import join

import logging

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
        print(variables_descr)
        self.storage_descr = storages
        self._data = { key: {} for key in storages}
        self._data.update({"variables": {}})
        self.exporters = {}
        self.name = name

    def __iter__(self):
        class DatabaseIterator:
            def __init__(self, db) -> None:
                self.current = 0
                self.db = db
            def __next__(self):
                if self.current < len(self.db.entries):
                    entry = self.db.entries[self.current]
                    self.current += 1
                    return entry, self.db[entry]
                else:
                    raise StopIteration
        
        return DatabaseIterator(self)

    @property
    def state_dict(self, include_data=True):
        '''
            Produces a dict serialization of the Database.
        '''
        ret = {
            "storage":      self.storage_descr,
            "exporters":    self.exporters,
            "name":         self.name,
            "type":         "Database",
            "variables":    self.variables_descr # @TODO Should be moved outside soon
        }
        if include_data:
            ret.update({"_data": self._data})
        return ret

    def load_state_dict(self, state_dict):
        self.name = state_dict["name"]
        self.variables_descr = state_dict["variables"] if "variables" in state_dict else {}
        self.storage_descr   = state_dict["storages"]   if "storages"  in state_dict else []
        self.exporters = state_dict["exporters"] if "exporters" in state_dict else {}
        self._data = { variable['name']: {} for variable in self.variables_descr  }
        self._data.update({ key: {} for key in self.storage_descr })

        if "_data" in state_dict.keys():
            self._data.update(state_dict["_data"])

        # @TODO This should go away with variables descr
        if "populate-on-creation" in state_dict.keys() and state_dict["populate-on-creation"]:
            self.populate(state_dict["populate-on-creation"]["algo"], state_dict["populate-on-creation"]["count"])

        return self

    @classmethod
    def from_json(cls, data):
        return cls().load_state_dict(data)
    
    @property
    def entries(self):
        '''
            Returns the unique identifiers of all individuals
            @TODO I want to remove the 'magic and always present' variables key by something more robust.
        '''
        entries = set()
        for variable in self._data.keys():
            for indiv in self._data[variable].keys():
                entries.add(indiv)

        return list(entries)
    
    def save(self, filename):
        serialize_json(self.state_dict, filename)
        return self
    
    def __len__(self):
        ''' Returns the number of individuals in the database '''
        return len(self.entries)
    
    def clear(self):
        for key in self._data.keys():
            self._data[key].clear()
    
    def add_entry(self, name, dictionnary):
        for key in dictionnary.keys():
            self._data[key][name] = dictionnary[key]
        
    def merge(self, lhs):
        for key in self._data.keys():
            self._data[key].update(lhs._data[key])

    def update_entry(self, name, dictionnary):
        for key in dictionnary.keys():
            assert(key in self.storage_descr, f"Key {key} is not allowed in storage.")
            self._data[key][name] = dictionnary[key]

    def update_entries(self, entries, dictionnary):
        for i, entry in enumerate(entries):
            self.update_entry(entry, {key: dictionnary[key][i] for key in dictionnary.keys()})


    def __getitem__(self, key):
        return { k: self._data[k][key] for k in self._data.keys() if key in self._data[k] }
    
    def store_in_file(self, path, method, keys):
        payload = { key: np.asarray([ self._data[key][entity] for entity in self._data[key].keys() ]) for key in keys }
        if method == "npz":
            np.savez_compressed(path, **payload)
        else:
            logging.error("Unsupported export format")

    def export(self, exporter):
        ''' Used for exporting Database keys to any file format '''
        print(exporter)
        assert exporter != 'object', f"Invalid database exporter: {exporter}."
        assert exporter.count('.') == 1, "Database exporter expected 1 argument."
        export_format, export_name = exporter.split(".")
        export_filename = join(TMPDIR, f"{self.name}.dbexport.{str(uuid.uuid1())[:5]}.{export_format}")
        self.store_in_file(export_filename, export_format, self.exporters[exporter])
        return export_filename

    @property
    def num_scalar_variables(self):
        ''' @TODO Remove '''
        return count_continuous_variables(self.variables_descr)

    @property
    def continuous_variables_names(self):
        names = list()
        for i in self.continuous_variables_indices:
            names.append(self.variables_descr[i]["name"])
        return names

    @property
    def continuous_variables_indices(self):
        indices = list()
        for i, variable in enumerate(self.variables_descr):
            if variable["type"] in ["vreal", "real"]:
                indices.append(i)
        return indices

    @property
    def continuous_variables_sizes(self):
        sizes = list()
        for i in self.continuous_variables_indices:
            sizes.append(self.variables_descr[i]["size"])
        return sizes

    def assert_empty(self):
        for key in self._data.keys():
            assert(len(self._data[key]) == 0)
        return self

    def populate(self, algorithm, count):
        logging.debug(f"populating with {algorithm} {count} individuals.")
        sampler = LatinHypercube(d=self.num_scalar_variables)
        configs = sampler.random(n=count)
        bounds = countinuous_variables_boundaries(self.variables_descr)
        configs *= (bounds[1] - bounds[0])
        configs += bounds[0]

        variables = self.continuous_variables_names
        variables_sizes = self.continuous_variables_sizes
        variables_positions = np.cumsum([0]+variables_sizes)

        for conf in configs:
            individual_name = str(uuid.uuid1())
            logging.debug(f"Adding individual {individual_name}.")
            entry = {}
            for variable, offset, size in zip(variables, variables_positions, variables_sizes):
                entry.update({variable: conf[offset:offset+size]})
            self.add_entry(individual_name, entry)
        logging.info("Finished populating.")

        
    def same_variables(self, lhs):
        self.variables_descr = copy(lhs.variables_descr)

    def append_npz_keys(self, file, keys):
        d = np.load(file)
        num = d[keys[0]].shape[0]
        for i in range(num):
            individual_name = str(uuid.uuid1())
            self.add_entry(individual_name, { key: d[key][i] for key in keys})


