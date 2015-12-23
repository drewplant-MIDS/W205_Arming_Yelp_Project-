from pyspark import SparkContext, SparkConf
from pyspark import SparkFiles
from pyspark.sql import SQLContext, Row
from pyspark.sql.types import *

import json
from datetime import datetime as dt


yelp_home = "file:///data/yelp"

def review_json2row(d):
    review_id, user_id, business_id = \
        d["review_id"], d["user_id"], d["business_id"]
    text = d.get("text")
    star = int(d["stars"]) if "stars" in d else 0
    date = dt.strptime(d["date"], "%Y-%m-%d").date() if "date" in d else None 
    votes = d.get("votes")
    if votes is not None:
        votes_useful = int(votes["useful"]) if "useful" in votes else 0
        votes_funny = int(votes["funny"]) if "funny" in votes else 0
        votes_cool = int(votes["cool"]) if "cool" in votes else 0
    else:
        votes_useful = 0
        votes_funny = 0
        votes_cool = 0

    return [review_id, user_id, business_id, text, star, date, \
            votes_useful, votes_funny, votes_cool]

def load_reviews(sc, sqlContext, jsonfile=None, yelp_home=yelp_home):
    if not jsonfile:
        jsonfile = "%s/yelp_academic_dataset_review.json" % yelp_home

    reviews = sc.textFile(jsonfile) \
                .map(lambda txt: json.loads(txt)) \
                .map(review_json2row) 

    review_fields = [
        StructField("review_id", StringType(), False),
        StructField("user_id", StringType(), False),
        StructField("business_id", StringType(), False),
        StructField("text", StringType(), True),
        StructField("stars", IntegerType(), True),
        StructField("date", DateType(), True),
        StructField("votes_useful", IntegerType(), True),
        StructField("votes_funny", IntegerType(), True),
        StructField("votes_cool", IntegerType(), True)
    ]

    review_schema = StructType(review_fields)
    return sqlContext.createDataFrame(reviews, review_schema)

if __name__ == "__main__":
    conf = SparkConf()
    sc = SparkContext(conf=conf)
    # jsonfile = "%s/yelp_academic_dataset_review.json" % yelp_home
    # sc.addFile(jsonfile)
    sqlContext = SQLContext(sc) 
    load_reviews(sc, sqlContext) \
        .write.parquet("hdfs:///yelp/reviews.parquet")
