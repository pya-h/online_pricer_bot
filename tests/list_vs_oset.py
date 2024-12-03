import time
from random import randint
from ordered_set import OrderedSet

inputs = [str(randint(1, 1000)) for _ in range(10000)]

s = set()

start = time.time()

for x in inputs:
    if x not in s:
        s.add(x)
    else:
        s.remove(x)

print('For set: ', time.time() - start)
start = time.time()
l = []
for x in inputs:
    if x not in l:
        l.append(x)
    else:
        l.remove(x)
print('For list: ', time.time() - start)
