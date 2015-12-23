from flask import Flask, request, jsonify, abort, make_response, current_app, Response

import json

from datetime import timedelta
from functools import update_wrapper
from functools import wraps

from elasticsearch import Elasticsearch

es = Elasticsearch()


app = Flask(__name__)

def check_auth(auth):
    return auth == "secret_key_not_really"

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not check_auth(auth):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            print resp
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


def build_query(terms):
    query = {
        'bool' : { 'should': [
            { "match": { 
              "name":  {
                "query": terms,
                "boost": 3
            }}},
            { "match": { 
              "categories":  {
                "query": terms,
                "boost": 1
            }}},
            { "match": { 
              "full_address":  {
                "query": terms,
                "boost": 1
            }}},
        ]}
    }
    return query

@app.route('/')
def index():
    return "Hello."

@app.route('/api/search', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*', headers="Content-Type, Authorization")
@requires_auth
def search():
    input = json.loads(request.data)
    terms = input["q"]
    query = build_query(terms)
    results = es.search(index="yelp", doc_type="business", body={ 'query': query }) 
    return jsonify(results)

app.run(host='0.0.0.0', debug=True, threaded=True, use_reloader=False)
