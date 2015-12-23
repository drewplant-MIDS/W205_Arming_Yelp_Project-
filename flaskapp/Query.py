#!/usr/bin/python
# Function for Flask script to query yelp and postgres table for business name
# ...and return a json object...
import json  # For importing json files
import numpy as np
import re # For regular expression filtering of categories
import matplotlib.pyplot as plt
import argparse # For parsing arguments to main()
import urllib # For formatting url's
import urllib2 # 
import oauth2 # For authenticating business and search requests 
import pprint # 
import codecs # For converting unicode to ascii for print output...
import sys # For setting up stdout...

# Extra import for postgres queries
import psycopg2

# Setup default search parameters
API_HOST = 'api.yelp.com'
DEFAULT_TERM = 'dinner'
DEFAULT_LOCATION = 'San Francisco, CA'
SEARCH_LIMIT = 3
SEARCH_PATH = '/v2/search/'
BUSINESS_PATH = '/v2/business/'

# Setup authentication credentials
CONSUMER_KEY = 'zEwi4U932n3N8kCMzlIb4A'
CONSUMER_SECRET = '-h3eLUBxVslZBvEJjQSIrxAm9Q0'
TOKEN = 'k_2Ed8_BrxYuvKO6AL5V1A7mwH95WLd2'
TOKEN_SECRET = 'Y3In1CMXvPsVd6xELSqjj8D3Niw'

def request(host, path, url_params=None): 
    """Prepares OAuth authentication and sends the request to the API.
    Args: 
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        urllib2.HTTPError: An error occurs from the HTTP request.
    """ 
    url_params = url_params or {}
    url = 'https://{0}{1}?'.format(host, urllib.quote(path.encode('utf8')))

    consumer = oauth2.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
    oauth_request = oauth2.Request(
                    method="GET", url=url, parameters=url_params) 
    oauth_request.update(
        {
            'oauth_nonce': oauth2.generate_nonce(),
            'oauth_timestamp': oauth2.generate_timestamp(),
            'oauth_token': TOKEN,
            'oauth_consumer_key': CONSUMER_KEY
        }
    )
    token = oauth2.Token(TOKEN, TOKEN_SECRET)
    oauth_request.sign_request( 
            oauth2.SignatureMethod_HMAC_SHA1(), consumer, token) 
    signed_url = oauth_request.to_url()

    # print u'Querying {0} ...'.format(url)

    urlconn = urllib2.urlopen(signed_url, None)
    try: 
        response = json.loads(urlconn.read())
    finally: 
        urlconn.close()

    return response


def search(term, location):
        """Query the Search API by a search term and location.  
        Args: 
            term (str): The search term passed to the API.
            location (str): The search location passed to the API.  
        Returns:
             dict: The JSON response from the request.  
        """ 
        url_params = { 
                'term': term.replace(' ', '+'), 
                'location': location.replace(' ', '+'), 
                'limit': SEARCH_LIMIT 
                }
        return request(API_HOST, SEARCH_PATH, url_params=url_params)


def get_business(business_id): 
    """Query the Business API by a business ID.
    Args:
        business_id (str): The ID of the business to query.
    Returns:
        dict: The JSON response from the request.
    """ 
    business_path = BUSINESS_PATH + business_id 
    return request(API_HOST, business_path)

def query_api(term, location):
    """Queries the API by the input values from the user.
    Args:
        term (str): The search term to query.
        location (str): The location of the business to query.
    """
    response = search(term, location)

    businesses = response.get('businesses')
    # print "Keys of businesses[0] hash = %s"  %((businesses[0]).keys())

    if not businesses: 
        print u'No businesses for {0} in {1} found.'.format(term, location)
        return

    business_id = businesses[0]['id']

    # print u'{0} businesses found, querying business info ' \
    'for the top result "{1}" ...'.format(len(businesses), business_id) 
    response = get_business(business_id)

    # print u'Result for business "{0}" found:'.format(business_id)
    # pprint.pprint(response, indent=2)
    # Return top business result...
    return response

def query(query_term):

    try: 
        Business = query_api(query_term, "San Francisco, CA")
        BusName = Business['name']
        # query_api(Term, Location)
        if len(Business) > 0: 
            print "Business name: %s" %(Business['name']) 
            print "         Address: %s" %(Business['location']['address']) 
            print "         Review: %s" %(Business['rating']) 
            print "         Review Count: %s" %(Business['review_count'])
        
    except urllib2.HTTPError as error: 
        sys.exit('Encountered HTTP error {0}. Abort program.'.format(error.code)) 
    # Search for the same term in postgres table
    ## Setup a connection
    if len(Business) > 0: 
        psycoconn = psycopg2.connect(database = "inspections", user="postgres", password="", host="localhost", port="5432") 
        ## Setup a cursor 
        psycocur = psycoconn.cursor() 
        ## Query table to check if business exists...
        psycocur.execute("SELECT bus.busname,vio.violationid,vio.risk,vio.description, vio.ispectdate FROM business bus INNER JOIN violations vio ON (bus.busid = vio.busid AND bus.busname ILIKE %s ) ORDER BY vio.ispectdate DESC LIMIT 3;", ("%"+BusName+"%",))
        ReadRecords = psycocur.fetchall()
        return ReadRecords
    return None
    
