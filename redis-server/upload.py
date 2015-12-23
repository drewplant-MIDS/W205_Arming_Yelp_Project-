import json
import numpy as np
import cPickle as pickle

from nearpy import Engine
from nearpy.hashes import RandomBinaryProjections
from nearpy.storage import RedisStorage
from redis import Redis

dimension = 100

lshash = RandomBinaryProjections('DocHash', 12, rand_seed=123)

redis_storage = RedisStorage(Redis(host='localhost', port=6379, db=1))
engine = Engine(dimension, lshashes=[lshash], storage=redis_storage)

with open("ids.json") as f:
    ids = json.load(f)

docvecs = np.load("dm.docvecs.doctag_syn0.npy", mmap_mode='r')

for i,id in enumerate(ids):
    vec = docvecs[i] # 1x100 nparray
    engine.store_vector(vec, id)

redis_storage.store_hash_configuration(lshash)
