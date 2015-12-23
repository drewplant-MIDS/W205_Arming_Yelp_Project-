# W205 Arming Yelp Project

Final Project for W205 - Yiran Sheng, Vamsi Sakhamuri, Drew Plant

## Serving Layer

We use Flask to host api servers and connect to a web app frontend to allow user to input queries and recieve results. 

![](https://raw.githubusercontent.com/drewplant-MIDS/W205_Arming_Yelp_Project-/master/Application1.png)
![](https://raw.githubusercontent.com/drewplant-MIDS/W205_Arming_Yelp_Project-/master/Application2.png)


* API server 1 communicates with Yelp Api for live results, and join response from Yelp with `SFData` dataset hosted in `postgresql`
* API server 2 communicates with `ElasticSearch` for business queries on Yelp Acadamic dataset, and returns business documents in JSON format
* API server 3 accepts inputs (business_ids) from previous query results, as well user input for positive and negative key words, looks up vector embeddings from local `redis` instance, performs LSH search for most similar businesses

The web app frontend communicates with all three servers and present results in UI. 

## Offline Training

Yelp reviews from academic dataset is uploaded to a Hadoop cluster, and stored on HDFS. We use Spark to process and train Doc2Vec models for each business in the dataset based on review texts, and export resulting document vectors, later to be stored in `redis`. Currently the transfer from HDFS to `redis` is a manual process through scp/rsync. 

Two versions for `Doc2Vec` model training are implemented using Spark and gensim:

1. A serial version training `PV-DM` model usnig Spark's `toLocalIterator` api feeding into gensim `Doc2Vec` model, with appropriate learning rate adjustments. 
2. A paralle version using only gensim's internal Cython procedures, and parallelized with Spark's RDD apis (broadcast, mapPartitions). This version is only capable of training `PV-DBOW` models. 
