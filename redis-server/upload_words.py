import json
import numpy as np
import cPickle as pickle

from nearpy import Engine
from nearpy.hashes import RandomBinaryProjections
from nearpy.storage import RedisStorage
from redis import Redis

from ne import CosineSim

dimension = 100

with open("hndbow.index2word", 'r') as f:
    index2words = json.load(f)

wordvecs = np.load("hndbow.syn0.npy")

redis_storage = RedisStorage(Redis(host='localhost', port=6379, db=3))

lshash = RandomBinaryProjections('WordHash', 5, rand_seed=123)

engine = Engine(dimension, distance=CosineSim(), lshashes=[lshash], storage=redis_storage)

for i,w in enumerate(index2words):
    vec = wordvecs[i] # 1x100 nparray
    engine.store_vector(vec, w)

redis_storage.store_hash_configuration(lshash)
