from pyspark import SparkContext, SparkConf
from pyspark.sql import SQLContext

import re

def parse(df):
    raw = df.select("business_id", "text") \
             .map(lambda row: (row.business_id, row.text))

    # parsing text
    contractions = re.compile(r"'|-|\"")
    # all non alphanumeric
    symbols = re.compile(r'(\W+)', re.U)
    # single character removal
    singles = re.compile(r'(\s\S\s)', re.I|re.U)
    # separators (any whitespace)
    seps = re.compile(r'\s+')

    def clean(text): 
        text = text.lower()
        text = contractions.sub('', text)
        text = symbols.sub(r' \1 ', text)
        text = singles.sub(' ', text)
        text = seps.sub(' ', text)
        return text

    alteos = re.compile(r'([!\?])')
    def sentences(l):
        l = alteos.sub(r' \1 .', l).rstrip("(\.)*\n")
        return l.split(".")

    # RDD of (star, sentence) pairs
    data = raw.flatMap(lambda (business_id, text): [(business_id, clean(s).split()) for s in sentences(text)]) 
    return data


if __name__ == '__main__':
    df = sqlContext.read.load("hdfs:///yelp/reviews.parquet", format="parquet")
    print parse(df).takeSample(False, 10)





