def __requires__():
    return {"variables": ["fevals", "nagents", "fom", "variables", "doe"]}

import numpy as np
from keever.database import count_continuous_variables, countinuous_variables_boundaries
from sko.PSO import PSO

def __run__(fevals, nagents, fom, doe):
    ndim = count_continuous_variables(doe.variables_descr)
    bounds = countinuous_variables_boundaries(doe.variables_descr)
    def fun(x):
        return fom.action("evaluate-dummy", args={"x": x})
    pso = PSO(func=fun, n_dim=ndim, pop=nagents, max_iter=fevals//nagents, lb=bounds[0], ub=bounds[1], w=0.7298, c1=1.49618, c2=1.49618)
    pso.run()
    
    return pso.gbest_y
