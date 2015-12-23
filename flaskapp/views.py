from flaskapp import app,Business,loadSession
from flask import render_template,request,jsonify,abort,make_response, current_app, Response
from models import inspections,Violation,db
import json

from Query import query

from datetime import timedelta
from functools import update_wrapper
from functools import wraps

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

session = loadSession()

@app.route('/querydb')
def list_all():
    return render_template(
    'list.html',
    category = session.query(Business).all())                                            

# Define a route for the default URL, which loads the form                                          
@app.route('/')
def form():   
    return render_template('form_submit.html')                                                  
               
#Define a route for the action of the form, for example '/hello/'                                  
# We are also defining which type of requests this route is                                         
# accepting: POST requests in this case                                                             
@app.route('/results/', methods=['POST'])
def hello():      
    name=request.form['yourname']
    email=request.form['youremail']
    return render_template('form_action.html', name=name, email=email)  

@app.route('/app', methods=['GET'])
def webapp():      
    return app.send_static_file('app.html')

@app.route('/api/query', methods=['GET', 'OPTIONS'])
@crossdomain(origin="*")
def query_business():      
    input = json.loads(request.args.get("data"))
    print input
    if 'term' not in input:
        abort(400)

    term = input['term']
    results = query(term)
    print results
    print type(results)

    return jsonify({ 'data': results })


