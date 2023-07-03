[![Python package](https://github.com/Kaeryv/Keever/actions/workflows/python-package.yml/badge.svg)](https://github.com/Kaeryv/Keever/actions/workflows/python-package.yml)

# Using the Surrogate Optimizer

```bash
pip install 'keever @ git+https://github.com/Kaeryv/Keever'
```

## Before using Keever

First, you will want to prepare your optimizer and simulation routines.
Theses scripts should be placed in the `user` folder. 
You can use local packages that should also be placed in the user folder.
Other packages should preferably be installed using a virtual environment.

## Algorithms and Datasets

In Keever, there are two kinds of items you will handle: datasets and algorithms.

### Your first dataset

To create a dataset, you will declare one the field `dataset`. In the following code snippet, we define a dataset named `doe`.
This dataset has a single array of five real variables defining each design. Parameters range from -0.5 to 0.5.
We create an additional variable called `metric` to store the figure of merit.
The final item generates an initial population of `40` designs using the Latin Hypercube Sampling (LHS).

```yaml
workdir: "./"
datasets:
  doe:
    name: doe
    variables:
        - variable:
          name: r
          type : vreal
          lower: -0.5
          upper: 0.5
          size: 5
    storages:
      - metric
    populate-on-creation:
      algo: LHS
      count: 40
```

We can load this in python by using. The last line serializes to json the whole dataset.

```python
import sys
sys.path.append(".")
from keever.algorithm import ModelManager
import yaml

config = yaml.safe_load(open("example.yaml", "r"))
mm = ModelManager()
mm.load_state_dict(config)
mm.get("doe").save("doe-no-evaluations")
```

Now, if we want to perform a dummy optimization, we need a way to compute a figure of merit. For this, we will build an algorithm.
First, we build a python module in `examples/dummy_evaluation.py` to evaluate a simple figure of merit: the sphere function:

$$
f(\vec x) = \sum x_i^2.
$$

```python
def __requires__():
    return {"variables": ["x"]}

import numpy as np
def __run__(x):
    return np.sum(np.power(x, 2))
```

We need to register the algorithm in the yaml file:
```yaml
algorithms:
  fom:
    name: fom
    actions:
      evaluate-dummy:
        __object_type__: ModuleRunner
        shell: false
        path: examples.dummy_evaluation
        workdir: "./wd/"
```

Once set-up, we can use this module in our main file:
```python
result = mm.get("fom").action("evaluate-dummy", args={"x": [10, 10]})
print(result) # Prints 10**2 + 10**2 = 200
```

Now we can create a simple optimizer as a python module runner.

```python
def __requires__():
    return {"variables": ["fevals", "nagents", "fom"]}

import numpy as np
from hybris.optim import Optimizer

def __run__(fevals, nagents, fom):
    opt = Optimizer(nagents, [5, 0], max_fevals=fevals)
    opt.reset(42)

    while not opt.stop():
        x = opt.ask()
        y = fom.action("evaluate-dummy", args={"x": x})
        opt.tell(y)

    return opt.profile[-1]
```
```yaml
opt:
  name: opt
  actions:
    optimize:
      __object_type__: ModuleRunner
      shell: false
      path: examples.simple_pso
      workdir: "./wd/"
  config:
    fevals: 160
    nagents: 40
```

We run the optimizer on the problem using in the main file.
```python
best_fitness = mm.get("opt").action("optimize", args={"fom": mm.get("fom")})
print(best_fitness)
```


## Writing runners for non-python or decoupled codes

If you want to run any code as a job on a cluster, in a different python **virtualenv** or with another language, you should use these runners. Here we define an `algorithm` for the U-Net metamodel.

Under the `actions` item, you will find a single runner to train the network. 
- It uses **sbatch** as a shell as we work with a slurm job. You can of course replace this with a simple bash launcher script.
- The `path` should be a launcher script template (see dedicated section).

Under the `config` item, you will find all the algorithm's configuration. They can be changed at runtime in you main script but they serve as defaults/basis. These variables will be transmitted to the templated script.

```yaml
algorithms:
  model:
    name: unet
    actions:
      train:
        __object_type__: ScriptRunner
        shell: sbatch
        parallel: false
        path: user/templates/submit_unet.proto.sh
        workdir: "./wd/"
    config:
      model_file: *model_file
      epochs: 100
      hours: 4
      complexity: 3
      angle: 90
      decay: 1e-5
      batch_size: 64
      lr: 4e-4
      validratio: 0.05
```

### Writing a template script

Here is an example for training the U-Net. This the slurm cluster script `submit_unet.proto.sh` found above. 
All variables are placed between double curly brackets. Beware that the `touchfile` variable is
generated automatically. It serves as a generic way to detect job completion, your job should then always create this file upon successful completion.

Note that in some case, i.e. `{{dataset:npz.maps}}` there is a `:` followed by a token. This
is a custom exporter that you can define for datasets.

```bash
#!/bin/bash
#SBATCH --job-name=unet
#SBATCH --output=logs/%x.%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time={{hours}}:15:00
#SBATCH --mem-per-cpu=1024

source config
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
python user/train_unet.py \
    -nthreads $SLURM_CPUS_PER_TASK \
    -epochs {{epochs}} \
    -name {{model_file}} \
    -device cpu -hours {{hours}} \
    -complexity {{complexity}}\
    -augment_angle {{angle}} \
    -wd {{decay}}  \
    -bs {{batch_size}} \
    -lr {{lr}} \
    -data {{dataset:npz.maps}}\
    -validratio {{validratio}}\
    -copy_contour
touch {{touchfile}}

```


## The main loop

Your main script will define how the elements defined in the yaml file will interact.

```python
import sys
sys.path.append(".")

from keever.algorithm import ModelManager
import yaml

import numpy as np
from tqdm import trange

num_sbo_loops = 40
debug_mode = True
# Load the yaml setup.
config = yaml.safe_load(open("sbo.yml", "r"))

mm = ModelManager()
mm.load_state_dict(config)
mm.get("doe").save("doe-no-evaluations")

# We evaluate the first random designs with FDTD.
eval = mm.get("fom").action("evaluate-fdtd", args={"population": mm.get("doe")})
mm.get("doe").update_entries(eval["individual_tag"], {key: eval[key] for key in ["epsilon_map", "leakage_map", "metric"]})

# We emplace the evaluated random configuration as the starting population.
mm.get("main").clear()
mm.get("main").merge(mm.get("doe"))

# We train the first U-Net
mm.get("unet").action("train", args={"dataset": mm.get("main")})

for i in trange(num_sbo_loops):
    pso_seeds = np.random.randint(999999, size=10).tolist()
    # We sample the figure of merit with PSO (it will automatically use the U-Net fidelity)
    # The reload method reloads the algorithm from filesystem before executing.
    # This allows for fixing bug during the run.
    opt_files = mm.get("pso").reload(debug_mode)
        .action("run", args={"fom": mm.get("fom"), "seed": pso_seeds, "workdir": "wd/"})
    # The selection process needs the optimizer archive and the current population.
    selections = mm.get("sel").reload(debug_mode)
        .action("run", args={
            "dataset": mm.get("main"), "optimizer_archive": opt_files["output"], "workdir":"wd"
        })
    mm.get("selected").append_npz_keys(selections["output"], ["variables"])
    eval = mm.get("fom").action("evaluate-fdtd", args={"population": mm.get("selected")})
    mm.get("selected").update_entries(eval["individual_tag"], {key: eval[key] for key in ["epsilon_map", "leakage_map", "metric"]})
    
    # We add the selection to the main database.
    mm.get("main").merge(mm.get("selected"))
    mm.get("unet").action("train", args={"dataset": mm.get("main")})
    mm.get("selected").clear()

```

## Writing runnables modules

You can create conversion scripts to turn databases into input files for your application, for instance, this scripts converts the database from keever (which is a dict) to Konïg's npz input files using functions that are stored in `user/tools/`.

```python
from os.path import join
from user.tools import metasurface_raw_to_npz, angle_raw_to_npz, annular_raw_to_npz

type2converter = {
    "angles": angle_raw_to_npz,
    "annular": annular_raw_to_npz,
    "metasurface": metasurface_raw_to_npz
}

def __run__(population, workdir="", tmpdir="", type=""):
    assert(type in type2converter.keys())
    for indiv, props in population:
        type2converter[type](props["variables"], join(workdir, indiv + ".in.npz"))

    return {"individual_tag": list(population.keys()) }

def __requires__():
    return {"variables":["population", "workdir", "type"]}

def __declares__():
    return ["individual_tag"]
```

##
