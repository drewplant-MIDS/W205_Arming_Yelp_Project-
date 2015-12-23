# Redis Server

This app uploads trained document vectors to `redis`, and fires up a Flask server to server client request for similar businesses. 

## Install Dependencies

```
pip install numpy gensim redis NearPy flask
```

## Other Requirements

`gensim` model output for document vectors, produced in `training`.

`ids.json` a json file of array of busines ids, which matches document vector indices.

This file can be exported from `gensim` model:

```
ids = [id for id in model.docvecs.doctags]
```

## Upload Scripts

`upload.py` uploads from on disk `npy` file to redis, computes LSH bucket keys as well (using `NearPy`).

`upload_business.py` uploads business jsons from Yelp Acadamic dataset to redis. 
