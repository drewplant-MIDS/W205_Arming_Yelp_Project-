from flask import Flask
#import psycopg2
#from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Column, MetaData, Table
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import mapper, sessionmaker

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI']='postgresql://postgres@localhost:5432/inspections'

#engine = create_engine('postgresql://postgres@localhost:5432/inspections', echo=True)

class Business(object):
    pass

#----------------------------------------------------------------------
def loadSession():
    """"""
    engine = create_engine('postgresql://postgres@localhost:5432/inspections', echo=True)
    
    metadata = MetaData(engine)
    #violations = Table('violations',metadata,
    #                    Column('id',Integer,primary_key=True),
    #                    Column('busid',Integer),
    #                    Column('ispectdate',Text),
    #                    Column('violationid',Text),
    #                    Column('risk',Text),
    #                    Column('description',Text))
    business  = Table('business', metadata, autoload=True)
    #violations = Table('violations', metadata, 
    #                       Column("id", Integer, primary_key=True),
    #                       autoload=True)
    mapper(Business,business)
    #Session = sessionmaker(bind=engine)
    #session = Session()
    Session = sessionmaker()
    session = Session(bind=engine)
    return session
#import create_db

from views import *

#app.config['SQLALCHEMY_DATABASE_URI']='postgresql+psycopg2://postgres:pass@localhost:5432/test_app'

if __name__ == '__main__':
    # app.run()
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True, use_reloader=False)
