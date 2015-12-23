from gensim.models.word2vec import Word2Vec
from gensim.models.doc2vec import TaggedDocument,Doc2Vec

from pyspark import SparkContext, SparkConf
from pyspark.sql import SQLContext

from pyspark.mllib.regression import LabeledPoint, LinearRegressionWithSGD, LinearRegressionModel

from parse import parse
from ddoc2vecf import DistDoc2VecFast

from itertools import islice

import numpy as np
from numpy import ceil

glove_path = "/root/doc2vec/word2vec_model/glove_model.txt"

def build_vocab(model, rdd):
    model.build_vocab(rdd.toLocalIterator())
    return model

def extract(sqlContext):
    df = sqlContext.read.load("hdfs:///yelp/reviews.parquet", format="parquet")
    data = parse(df) \
           .map(lambda (id, s): TaggedDocument(words=s, tags=[id]))
    return data

def train_pv_dm(corpus, alpha=0.025, batch_size=long(1e5)):
    dm = Doc2Vec(size=100, alpha=alpha) 
    corpus.cache()
    build_vocab(dm, corpus)
    dm.intersect_word2vec_format(glove_path)
    n = corpus.count()
    print "** training sample size: %d **" % n
    n_batch = int(ceil(n / float(batch_size)))
    corpus_local = corpus.toLocalIterator()
    min_alpha = dm.min_alpha
    alpha0 = alpha
    for k in xrange(n_batch):
        print "** Training batch (%d/%d) **" % (k+1,n_batch) 
        progress = 1.0 * (k+1) / n_batch
        dm.alpha = alpha
        alpha = alpha0 - (alpha0 - min_alpha) * progress
        dm.min_alpha = alpha
        print "** learning rate: %f, min learning rate: %f **" % (dm.alpha, dm.min_alpha)
        dm.train(islice(corpus_local, 0, batch_size), total_examples=batch_size)

    corpus.unpersist()

    return dm

def train_pv_dbow(corpus, alpha=0.025):
    model = Word2Vec(size=100, alpha=alpha, hs=0, negative=8) 
    dd2v = DistDoc2VecFast(model, alpha=alpha, num_iterations=1, learn_words=True, learn_hidden=True) 
    dd2v.build_vocab_from_rdd(corpus.map(lambda d: d.words))
    print "** done building vocab of size %d **" % len(model.vocab)
    corpus_kv = corpus.map(lambda d: (d.tags[0], d.words)) 
    # repartition corpus, make sure documents with same tag is grouped into the same partition
    corpus_repartitioned = corpus_kv.partitionBy(5) \
                                    .map(lambda (k,v): TaggedDocument(tags=[k], words=v)) 
    dd2v.train_sentences_cbow(corpus_repartitioned)
    return dd2v

def train(sqlContext, model_save_path="/data/yelp-models"):
    corpus = extract(sqlContext)
    model = train_pv_dm(corpus)
    model.save("%s/dm" % model_save_path)
    return model

def regression_prep(sqlContext, dd2v):
    df = sqlContext.read.load("hdfs:///yelp/reviews.parquet", format="parquet")
    df = df.limit(15000)
    avgstars = df.map(lambda row: (row.business_id, (1, row.stars if row.stars else 0))) \
                   .reduceByKey(lambda tp1, tp2: (tp1[0] + tp2[0], tp1[1] + tp2[1])) \
                   .map(lambda (k,tp): (k, float(tp[1]) / tp[0]))  

    def extract_docvec(d):
        lookup = d['lookup']
        docvecs = d['doctag_syn0']
        return [(id, docvecs[i]) for id,i in lookup.iteritems()]

    docvecs = dd2v.doctag_syn0 \
                  .flatMap(extract_docvec) 
    
    data = avgstars.join(docvecs) \
               .map(lambda (k, tp): LabeledPoint(tp[0], tp[1]))
    return data

def regression(reg_data):
    reg_data = reg_data.cache()
    print "** logistic regression on %d data points **" % reg_data.count()
    (trainingData, testData) = reg_data.randomSplit([0.7, 0.3])
    lrmodel = LinearRegressionWithSGD.train(trainingData)
    labelsAndPreds = testData.map(lambda p: (p.label, lrmodel.predict(p.features)))

    MSE = labelsAndPreds.map(lambda (v, p): (v - p)**2).reduce(lambda x, y: x + y) / labelsAndPreds.count()

    print "*** MSE: %f ***" % MSE
    reg_data.unpersist()
 
if __name__ == "__main__":
    conf = (SparkConf() \
        .set("spark.driver.maxResultSize", "4g"))

    sc = SparkContext(conf=conf)
    sqlContext = SQLContext(sc)
    if False:
        # train model PV-DM sequantially
        mod = train(sqlContext)
    else:
        # train PV-DBOW in paralle
        corpus = extract(sqlContext)
        dd2v = train_pv_dbow(corpus)
        # sanity check
        # print dd2v.doctag_syn0.collect()
        print dd2v.model.most_similar("bread")
        # dd2v.saveAsPickleFile("hdfs:///yelp/docvecs")
        reg_data = regression_prep(sqlContext, dd2v)
        regression(reg_data)
   


