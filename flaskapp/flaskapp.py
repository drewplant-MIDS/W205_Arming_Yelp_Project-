from flask import Flask
from sqlalchemy import create_engine, Column, MetaData, Table
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import mapper, sessionmaker

app = Flask(__name__)

class Business(object):
    pass

#----------------------------------------------------------------------
def loadSession():
    """"""
    engine = create_engine('postgresql://postgres@localhost:5432/inspections', echo=True)
    
    metadata = MetaData(engine)
    business  = Table('business', metadata, autoload=True)
    mapper(Business,business)
    Session = sessionmaker()
    session = Session(bind=engine)
    return session

from views import *

if __name__ == '__main__':
    # app.run()
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True, use_reloader=False)
