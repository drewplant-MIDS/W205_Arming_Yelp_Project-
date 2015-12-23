import numpy as np
from numpy import sqrt, exp, dot, zeros, outer, random, dtype, get_include, float32 as REAL,\
    uint32, seterr, array, uint8, vstack, argsort, fromstring, sqrt, newaxis, ndarray, empty, sum as np_sum
from gensim.models.word2vec import Vocab, Word2Vec
from gensim.models.doc2vec import TaggedDocument, Doc2Vec

from collections import defaultdict
from operator import add
try:
    from gensim.models.doc2vec_inner import train_document_dbow
    from gensim.models.word2vec_inner import FAST_VERSION  # blas-adaptation shared from word2vec
except:
    # failed... fall back to plain numpy (20-80x slower training than the above)
    FAST_VERSION = -1
    from gensim.models.doc2vec import train_document_dbow

class DistDoc2VecFast:
    '''
    DBOW, Skip-gram doc2vec model on Spark
    '''
    def __init__(self, model, alpha=0.025,
                 num_iterations=100,
                 num_partitions=None,
                 learn_hidden=True, learn_words=False):
        self.model = model # gensim model
        self.alpha = alpha # learning rate
        self.learn_hidden = learn_hidden
        self.learn_words = learn_words
        self.num_iterations = num_iterations
        self.num_partitions = num_partitions

    def build_vocab_from_rdd(self, corpus):
        '''
        Build model vocab from RDD, respect model's min_count, max_vocab_size
        if reset_hidden sets to True (default), reset syn1neg weights
        code borrowed from:
        https://github.com/dirkneumann/deepdist/blob/master/examples/word2vec_adagrad.py
        '''
        model = self.model
        model.corpus_count = corpus.count()
        s = corpus   \
            .flatMap(lambda s: [(w, 1) for w in s])   \
            .reduceByKey(add)            \
            .filter(lambda x: x[1] >= model.min_count)              \
            .collect()
            # .map(lambda x: (x[1], x[0]))              \
            # .sortByKey(False)                         \
            # .collect()

        model.raw_vocab = defaultdict(int, s)
        model.finalize_vocab()
        model.total_words = long(len(model.vocab))

    def saveAsPickleFile(self, path):
        syn0_path = "%s.syn0" % path 
        syn1neg_path = "%s.syn1neg" % path 
        doctagsyn0_path = "%s.doctag_syn0" % path 
        self.doctag_syn0.saveAsPickleFile(doctagsyn0_path)
        sc = self.doctag_syn0.context
        sc.parallelize(self.model.syn0, 1).saveAsPickleFile(syn0_path)
        sc.parallelize(self.model.syn1neg, 1).saveAsPickleFile(syn1neg_path)

    def init_doc_sims(self, corpus):
        model = self.model
        def make_sent_doctag(docs):
            tag2index, docvecs = {}, []
            for d in docs:
                tag = d.tags[0]
                sent = d.words
                if tag in tag2index:
                    i = tag2index[tag]
                else:
                    i = len(docvecs) 
                    seed = "%d %s" % (model.seed, tag)
                    docvec = model.seeded_vector(seed).astype(REAL)
                    tag2index[tag] = i
                    docvecs.append(docvec)
            return [{ 'lookup': tag2index, 'doctag_syn0': array(docvecs) }]
        return corpus.mapPartitions(make_sent_doctag)
      
    def train_sentences_cbow(self, corpus):
        '''
        Faster version, uses gensim's Cython training procedure
        (negative sampling, skip-gram settings)
        '''
        model = self.model
        alpha = self.alpha
        vector_size = model.vector_size
 
        if self.num_partitions:
            corpus = corpus.repartition(self.num_partitions)
        # RDD of init doc vectors
        doctag_syn0 = self.init_doc_sims(corpus) 

        n_part = corpus.getNumPartitions()
        sc = corpus.context

        corpus = corpus.glom().cache()
        doctag_locks = corpus.map(lambda x: np.ones(dtype=REAL, shape=(len(x), ))).cache()

        bc_model = sc.broadcast(model)

        syn0_zeros = np.zeros(np.shape(model.syn0), dtype=REAL)
        syn1neg_zeros = np.zeros(np.shape(model.syn1neg), dtype=REAL)

        bc_syn0_0 = sc.broadcast(syn0_zeros)
        bc_syn1neg_0 = sc.broadcast(syn1neg_zeros)
        # params is a RDD of tripplelet (delta syn0, delta syn1neg, doctag_syn0 np array)
        params = doctag_syn0.map(lambda d: (bc_syn0_0.value, bc_syn1neg_0.value, d)).cache()

        trained_count = sc.accumulator(0)
        train_passes = sc.accumulator(0)

        def mapPartitions(iterable):
            model = bc_model.value
            syn0copy = model.syn0.copy()
            syn1negcopy = model.syn1neg.copy()
            params, sentences, lockf, k = iter(iterable).next()
            _a, _b, docvecs = params
            lookup = docvecs['lookup']
            doctag_syn0_part = docvecs['doctag_syn0']
            train_passes.add(1)
            for sent in sentences:
                i = lookup[sent.tags[0]]
                # training document modify doctag_syn0_part in-place
                train_document_dbow(model, sent.words,
                                    doctag_indexes=[i],
                                    alpha=alpha * 1.0 / sqrt(k+1),
                                    doctag_vectors=doctag_syn0_part,
                                    doctag_locks=lockf,
                                    learn_words=True,
                                    train_words=True,
                                    learn_hidden=True)
            trained_count.add(i+1)

            dsyn0 = model.syn0 - syn0copy
            dsyn1neg = model.syn1neg - syn1negcopy

            return [(dsyn0, dsyn1neg, docvecs)]

        def seq_op(a, b):
            return (b[0], b[1])

        def comb_op(delta_pairs, next_deltas):
            csyn0, csyn1neg = delta_pairs
            if csyn0 is None:
                csyn0 = bc_syn0_0.value
            if csyn1neg is None:
                csyn1neg = bc_syn1neg_0.value
            dsyn0, dsyn1neg = next_deltas
            csyn0 += dsyn0
            csyn1neg += dsyn1neg
            return csyn0, csyn1neg

        def simplify(k, params, corpus, locks):
            dset = params.zip(corpus).zip(locks) \
                .map(lambda (pair, lockf): (pair[0], pair[1], lockf, k)) 
            return dset

        for k in xrange(self.num_iterations):
            dataset = simplify(k, params, corpus, doctag_locks) 
            old_params = params
            params = dataset.mapPartitions(mapPartitions).cache()
            dsyn0, dsyn1neg = params.aggregate((None, None), seq_op, comb_op)
            bc_model.unpersist()
            model.syn0 += (dsyn0 / n_part)
            model.syn1neg += (dsyn1neg / n_part)
            bc_model = sc.broadcast(model)
            old_params.unpersist()

        corpus.unpersist()
        doctag_locks.unpersist()
        bc_syn0_0.unpersist()
        bc_syn1neg_0.unpersist()

        self.doctag_syn0 = params.map(lambda (_a, _b, dvecs): dvecs)
            
        # kick start training
        self.doctag_syn0.count()
        print "**** Train passes: %d ****" % train_passes.value
        print "**** Train counts: %d ****" % trained_count.value
        corpus.unpersist()
        doctag_locks.unpersist()
        bc_model.unpersist()

    def train_sentences_only_cbow(self, corpus):
        '''
        Faster version, uses gensim's Cython training procedure
        But cannot learn weights for hidden layer (syn1neg)
        Therefore, requires a already trained Word2Vec model 
        (negative sampling, skip-gram settings)
        '''
        model = self.model
        alpha = self.alpha
        vector_size = model.vector_size
 
        if self.num_partitions:
            corpus = corpus.repartition(self.num_partitions)

        doctag_syn0 = self.init_doc_sims(corpus) 

        n_part = corpus.getNumPartitions()
        sc = corpus.context

        corpus = corpus.glom().cache()
        doctag_locks = corpus.map(lambda x: np.ones(dtype=REAL, shape=(len(x), ))).cache()

        bc_model = sc.broadcast(model)

        trained_count = sc.accumulator(0)
        train_passes = sc.accumulator(0)

        def mapPartitions(iterable):
            model = bc_model.value
            docvecs, sentences, lockf, k = iter(iterable).next()
            lookup = docvecs['lookup']
            doctag_syn0_part = docvecs['doctag_syn0']
            train_passes.add(1)
            for sent in sentences:
                i = lookup[sent.tags[0]]
                # training document modify doctag_syn0_part in-place
                train_document_dbow(model, sent.words,
                                    doctag_indexes=[i],
                                    alpha=alpha * 1.0 / sqrt(k+1),
                                    doctag_vectors=doctag_syn0_part,
                                    doctag_locks=lockf,
                                    learn_words=False,
                                    train_words=False,
                                    learn_hidden=False)
            trained_count.add(i+1)

            return [docvecs]

        def simplify(k, doctag_syn0, corpus, locks):
            dset = doctag_syn0.zip(corpus).zip(locks) \
                .map(lambda (pair, lockf): (pair[0], pair[1], lockf, k)) 
            return dset

        def reducer(dataset, k):
            new_doctag = dataset.mapPartitions(mapPartitions)
            return simplify(k, new_doctag, corpus, doctag_locks) 

        init_dataset = simplify(0, doctag_syn0, corpus, doctag_locks)
        dataset = reduce(reducer, xrange(1, self.num_iterations), init_dataset)

        self.doctag_syn0 = dataset.map(lambda (docvecs, _1, _2, _3): docvecs) 

    def train(self, corpus):
        if self.learn_words and self.learn_hidden:
            return self.train_sentences_cbow(corpus)
        else:
            return self.train_sentences_only_cbow(corpus)
