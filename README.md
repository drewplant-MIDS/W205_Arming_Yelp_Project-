# W205_Arming_Yelp_Project-
Final Project for W205 - Yiran Sheng, Vamsi Sakhamuri, Drew Plant

## Serving Layer

We use Flask to host api servers and connect to a web app frontend to allow user to input queries and recieve results. 

* API server 1 communicates with Yelp Api for live results, and join response from Yelp with `SFData` dataset hosted in `postgresql`
* API server 2 communicates with ElasticSearch for business queries on Yelp Acadamic dataset, and returns business documents in JSON format
* API server 3 accepts inputs (business_ids) from previous query results, as well user input for positive and negative key words, looks up vector embeddings from local `redis` instance, performs LSH search for most similar businesses

