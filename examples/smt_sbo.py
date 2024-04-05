from smt.surrogate_models import KRG

import sys

method = sys.argv[1]
dbpath = sys.argv[2]

import numpy as np
db = np.load(dbpath)
X = db['r']
y = db['metric']
import matplotlib.pyplot as plt
print(y)
plt.scatter(*X.T[:2], c=y)
plt.savefig('test.png')
print(list(db.keys()))
print(X.shape)
