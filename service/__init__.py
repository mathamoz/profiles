import clearbit

from flask import Flask
from pymongo import MongoClient
from pymongo.errors import InvalidName
from celery import Celery
from urlparse import urlparse


app = Flask(__name__)
app.config.from_object('config')

client = MongoClient(app.config['MONGO_URL'])

mongo_uri = urlparse(app.config['MONGO_URL'])

try:
    dbname = mongo_uri.path.split('/')[1]

    mongo = client[dbname]
except InvalidName:
    mongo = client.profile_collection


# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

clearbit.key = app.config['CLEARBIT_KEY']

from service.api.views import api_endpoints

app.register_blueprint(api_endpoints, url_prefix='/profileservice')
