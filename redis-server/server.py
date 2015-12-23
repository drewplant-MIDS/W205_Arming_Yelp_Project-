from flask import Flask, request, jsonify, abort, make_response, current_app, Response

import json
import numpy as np

from redis import StrictRedis

from ne import create_engine
from model import ModelLoader

from datetime import timedelta
from functools import update_wrapper
from functools import wraps


app = Flask(__name__)

def check_auth(auth):
    return auth == "secret_key"

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

@app.route('/')
def index():
    return "Hello."

@app.route('/api/words-similar', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*', headers="Content-Type")
@requires_auth
def most_sim_words():
    input = json.loads(request.data) 
    if 'positive' not in input:
        abort(400)
    positive=input.get('positive') or []
    negative=input.get('negative') or []
    if len(positive) == 0:
        abort(400)

    results = model.most_similar(positive=positive, negative=negative)
    print results
    return jsonify({ "data" : results })


@app.route('/api/similar', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*', headers="Content-Type")
@requires_auth
def most_sim():
    input = json.loads(request.data) 

    sentence=input.get('sentence')
    business_id = input.get('business_id')
    positive=input.get('positive') or []
    negative=input.get('negative') or []

    if not sentence and not business_id:
       abort(400)

    vec = None
    if business_id in model.docvecs:
        vec = model.docvecs[business_id]
    elif sentence is not None:
        vec = model.infer_vector(sentence)

    if vec is None:
        abort(400)

    for w in positive:
        if w not in model:
            continue
        v = model[w]
        if v is not None:
            vec += v
    for w in negative:
        if w not in model:
            continue
        v = model[w]
        if v is not None:
            vec -= v
    results = engine.neighbours(vec)
    print len(results)
    results = [{"vector":r[0].tolist(), "sim": 1.0 - r[2], "id": r[1], "business": json.loads(redis_client.get(str(r[1])))} \
         for r in results]
    return jsonify({ "data" : results })

with ModelLoader("dm") as model:
    engine = create_engine()
    redis_client = StrictRedis(host='localhost', port=6379, db=0)
    app.run(host='0.0.0.0', debug=True, threaded=True, use_reloader=False)
