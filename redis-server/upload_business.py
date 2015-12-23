import json
import numpy as np
import cPickle as pickle
import redis

dimension = 100

with open("business.json") as f:
    buz = json.load(f)

r = redis.StrictRedis(host='localhost', port=6379, db=0)

for b in buz:
    if 'business_id' in b:
        r.set(b['business_id'], json.dumps(b))
