import json
from elasticsearch import Elasticsearch


es = Elasticsearch()

with open('yelp_academic_dataset_business.json', 'r') as f:
    for line in f:
        line = line.strip()
        doc = json.loads(line)
        try:
            res = es.index(index="yelp", doc_type='business', id=doc['business_id'], body=doc)
        except Exception:
            print "Failed: "
            print doc

