def __requires__():
    return {"variables": ["fevals", "nagents", "fom", "variables"]}

import numpy as np
from hybris.optim import Optimizer
from keever.database import count_continuous_variables, countinuous_variables_boundaries

def __run__(fevals, nagents, fom, doe):
    ndim = count_continuous_variables(doe.variables_descr)
    bounds = countinuous_variables_boundaries(doe.variables_descr)

    opt = Optimizer(nagents, [ndim, 0], max_fevals=fevals)
    opt.vmin = bounds[0]
    opt.vmax = bounds[1]
    opt.reset(142)
    
    print(fevals)
    while not opt.stop():
        x = opt.ask()
        y = fom.action("evaluate-dummy", args={"x": x})
        opt.tell(y)
    import matplotlib.pyplot as plt
    plt.plot(opt.profile)
    plt.savefig("prof.png")
    return opt.profile[-1]
