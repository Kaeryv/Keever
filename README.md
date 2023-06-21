# Using the Surrogate Optimizer

## Before to start

First, you will want to prepare your optimizer and simulation routines.
Theses scripts schould be placed in the `user` folder.

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

## Writing runners for non-python or decoupled codes

If you want to run any code as a job on a cluster, in a different python env or with another language, you should use these runners. Here we define an `algorithm` for the U-Net metamodel.

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

Here is an example for training the U-Net. This is a slurm cluster script. All variables
to be replaced are placed between double curly brackets. Beware that the touchfile variable is
generated automatically and serves as a way to detect job completion.

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