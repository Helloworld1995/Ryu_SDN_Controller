import random
container=set()
container.add((1,2,'a'))
container.add((1,2,'b'))
c=set([1,2,'b'])
for contain in container:
    if c.intersection(contain)==c:
        print contain
