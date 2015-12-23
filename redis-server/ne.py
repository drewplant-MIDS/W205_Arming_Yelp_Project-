import numpy
import scipy

from nearpy.distances.distance import Distance

from nearpy import Engine
from nearpy.hashes import RandomBinaryProjections

from redis import Redis
from nearpy.storage import RedisStorage

import cPickle as pickle

def create_engine():
    redis_storage = RedisStorage(Redis(host='localhost', port=6379, db=1))

    # Dimension of our vector space
    dimension = 100

    drbp = get_hash_config(redis_storage, "DocHash")

    # Create engine with pipeline configuration
    engine_doc = Engine(dimension, distance=CosineSim(),
                lshashes=[drbp], storage=redis_storage)
    return engine_doc

def get_hash_config(redis_storage, name):
    config = redis_storage.load_hash_configuration(name)
    if config is not None:
        # Config is existing, create hash with None parameters
        lshash = RandomBinaryProjections(None, None, rand_seed=123)
        # Apply configuration loaded from redis
        lshash.apply_config(config)
    else:
        raise RuntimeError("Hash Config not found")

    return lshash

class CosineSim(Distance):
    def distance(self, x, y):
        """
        Computes distance measure between vectors x and y. Returns float.
        """

        if scipy.sparse.issparse(x):
            x = x.toarray().ravel()
            y = y.toarray().ravel()
        return 1 - numpy.dot(x, y)
