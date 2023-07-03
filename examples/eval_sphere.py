def __requires__():
    return {"variables": ["x"]}

import numpy as np
def __run__(x):
    return np.sum(np.power(x, 2), axis=-1)
