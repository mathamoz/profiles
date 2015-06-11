import os


DEBUG = os.environ.get('DEBUG', False)
CELERY_BROKER_URL = os.environ.get('REDISTOGO_URL', 'redis://localhost:6379/0')
MONGO_URL = os.environ.get('MONGOLAB_URI', 'mongodb://localhost:27017/')
CLEARBIT_KEY = os.environ.get('CLEARBIT_KEY', '')