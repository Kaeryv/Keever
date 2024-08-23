def __requires__():
    return {"variables": ["fevals", "nagents", "fom", "variables"]}

import numpy as np
from hybris.optim import ParticleSwarm
from keever.database import (
        count_continuous_variables, 
        countinuous_variables_boundaries, 
        count_categorical_variables,
        categorical_variables_num_values)


def __run__(fevals, nagents, fom, doe):
    ncat = count_continuous_variables(doe.variables_descr)
    ncnt = count_categorical_variables(doe.variables_descr)
    bounds = countinuous_variables_boundaries(doe.variables_descr)
    cats = list(categorical_variables_num_values(doe.variables_descr))

    opt = ParticleSwarm(nagents, [ncat, ncnt], max_fevals=fevals)
    opt.vmin = bounds[0]
    opt.vmax = bounds[1]
    if ncnt > 0:
        opt.num_categories(cats)

    print(f"Optimizing with hybris using {ncnt} cont vars and {ncat} cat vars.")
    print(f"Categ vars are {cats}.")
    print(f"Cont vars are {bounds}.")
    opt.reset(142)
    
    while not opt.stop():
        x = opt.ask()
        y = fom.action("evaluate-dummy", args={"x": x})
        opt.tell(y)
    import matplotlib.pyplot as plt
    plt.plot(opt.profile)
    plt.savefig("prof.png")
    return opt.profile[-1]
