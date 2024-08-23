def __requires__():
    return {"variables": ["x", "categ"]}

import numpy as np
def __run__(x, categ=0):
    if categ == 0:
        return np.sum(np.power(x, 2), axis=-1)
    else:
        return np.sum(np.power(x[:, :-2], 2), axis=-1)**x[:,-1]
