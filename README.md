# Profile Service
The profile service consists of two components.  The first is a web app that serves as a REST API for adding, updating and querying profile data.  The second is a background task worker used for fetching data from the Clearbit API.

The application is written in Python using the Flask microframework.  The background worker uses Celery with Redis as the message broker.  Given the mostly schema-less nature of the data as well as the ability to run ad-hoc queries, MongoDB was chosen for the data storage backend.

### Requirements
This service depends on MongoDB and Redis.

### Configuration
The service config file is located in the root of the project and is named `config.py`

Configuration is loaded from the environment and the following variables are expected:
* REDISTOGO_URL - Redis connection string in the format `redis://localhost:6379/0`
* MONGOLAB_URI - MongoDB connection string in the format `mongodb://localhost:27017/`
* CLEARBIT_KEY - Dev/Prod API key for Clearbit
* DEBUG - Defaults to False

The `REDISTOGO_URL` and `MONGOLAB_URI` environment variables may need to be updated to run on Heroku depending on the add-on's used to provide those services.

### Running Locally
To run locally you will need to create a Python virtual environment and install the project requirements from the requirements.txt file.

* Inside the project directory run: `virtualenv --no-site-packages venv` to create a virtual environment.
* Activate the virtual environment by running: `source venv/bin/activate`
* Install the project requirements with: `pip install -r requirements.txt`
* Run the API server with: `DEBUG=1 CLEARBIT_KEY=[CLEARBIT_API_KEY] REDISTOGO_URL=[REDIS_CONNECTION_STRING] MONGOLAB_URI=[MONGODB_CONNECTION_STRING] python app.py`
* Run the background task worker with: `CLEARBIT_KEY=[CLEARBIT_API_KEY] REDISTOGO_URL=[REDIS_CONNECTION_STRING] MONGOLAB_URI=[MONGODB_CONNECTION_STRING] celery worker -A app.celery --loglevel=info`

The API will be available at `http://localhost:5000/profileservice`

### Running on Heroku
The included Procfile should be sufficient to run on Heroku.  Ensure that you have added the Clearbit API key to the environment and that the MongoDB and Redis configuration variables are set correctly for the values provided by the chosen Heroku add-on's.

There is both a webapp and a worker so two dyno's will be necessary.

### Testing API Credentials
For the purposes of this demo, API credentials have been hard-coded into the application.  In a production setting this service would expect to validate these credentials in the core application database or via another service.

The following API key's and UUID's are available.  The UUID's would be the customer account UUID that all accounts have.
```
    {
        'api_key': 'ec6ec81fbe444730ac64c94ec2d24bc0',
        'uuid': '7493d768db0549ea8b593368db237349',
    },
    {
        'api_key': '888b4fedb76448b5a279a559985f4d3b',
        'uuid': 'ab15621b38844b5091c3f2eb8c511fbf',
    },
    {
        'api_key': 'e4a1e97da8f34ff888fdbf4e9f3ee3f4',
        'uuid': 'f8423b394ba447ff80b6cdad00435d07',
    }
```

### Using the API
There are 4 API endpoints available:

#### Get a Profile
* HTTP Method: GET
* Endpoint: profileservice/[UUID/EMAIL/DOMAIN]?API_KEY=[CUSTOMER_API_KEY]
* CURL Example: `curl http://localhost:5000/profileservice/joel@weirau.ch?API_KEY=e4a1e97da8f34ff888fdbf4e9f3ee3f4`

This endpoint is expecting one of the following parameters:
* UUID for a person or company object (returned via the create endpoint)
* Email address for the person eg. joel@weirau.ch
* Email domain for a company eg. google.com

If a profile is found the response will look like:
```
{
    "message": null,
    "data": {
        "person": {
            "last_updated": "2015-04-15T00:51:13.668000",
            "uuid": "771d887870ff4b42bbcf2e6f8d72b95b",
            "name": {
                "fullName": "",
                "givenName": null,
                "familyName": null
            },
            "_id": "552db54b6900da2d0f1c11f1",
            "email": "joel@weirau.ch"
        },
        "company": {
            "domain": "weirau.ch",
            "_id": "552db54b6900da2d0f1c11f2",
            "last_updated": "2015-04-15T00:51:14.209000",
            "uuid": "d0cadd9ce5bc496fbf57f18cdbca086b"
        }
    },
    "success": true
}
```

If no profile is found the response will look like:
```
{
    "message": "No Profile Found",
    "data": null,
    "success": false
}
```

#### Create a Profile
* HTTP Method: POST
* Endpoint: profileservice/[EMAIL]?API_KEY=[CUSTOMER_API_KEY]&fname=[FIRST_NAME]&lname=[LAST_NAME]
* `fname` and `lname` are optional and will override any values provided by Clearbit for **this customer only**
* CURL Example: `curl -X POST http://localhost:5000/profileservice/joel@weirau.ch?API_KEY=e4a1e97da8f34ff888fdbf4e9f3ee3f4&fname=Joel&lname=Weirauch`

This endpoint is expecting an email address and optionally a first/last name

A successful registration response will look like:
```
{
    "message": null,
    "data": {
        "person_uuid": "771d887870ff4b42bbcf2e6f8d72b95b",
        "company_uuid": "d0cadd9ce5bc496fbf57f18cdbca086b"
    },
    "success": true
}
```

#### Update a Profile
* HTTP Method: POST
* Endpoint: profileservice/[UUID/EMAIL/DOMAIN]?API_KEY=[CUSTOMER_API_KEY]&data=[Base64 encoded JSON]
* `data` is a Base64 encoded JSON object of key/value pairs
* `data` overrides data from Clearbit for **this customer only**
* CURL Example: `curl -X PUT 'http://localhost:5000/profileservice/joel@weirau.ch?API_KEY=e4a1e97da8f34ff888fdbf4e9f3ee3f4&data=ew0KICAgIm5hbWUiOiB7DQoiZnVsbE5hbWUiOiAiSm9lbCBXZWlyYXVjaCIsDQoiZ2l2ZW5OYW1lIjogIkpvZWwiLA0KImZhbWlseU5hbWUiOiAiV2VpcmF1Y2giDQp9DQp9'`

The above CURL example will update the profile for `joel@weirau.ch` for given customer with the following data:
```
{
    "name": {
        "fullName": "Joel Weirauch",
        "givenName": "Joel",
        "familyName": "Weirauch"
    }
}
```

A successful response will look like:
```
{
    "message": "Profile Updated",
    "data": null,
    "success": true
}
```

#### Ad-hoc Queries
* HTTP Method: GET
* Endpoint: profileservice/query?API_KEY=[CUSTOMER_API_KEY]&q=[URL Encoded Query String]&get_before/get_after=[CURSOR]
* `get_before` and `get_after` are used to page results and signal which direction to page
* `q` is a URL encoded string representing the conditions you wish to query for
* CURL Example: `curl 'http://localhost:5000/profileservice/query?API_KEY=e4a1e97da8f34ff888fdbf4e9f3ee3f4&q=occupation=Software%20Engineer,salary=gte=80000&get_after=552d67da6900da212167aa23'`

The above CURL example will search for any person with an occupation of Software Engineer AND a salary greater than or equal to 80000 and will fetch the page of records after the record with the ID `552d67da6900da212167aa23`.

The query system uses a cursor mechanism for paging by using the `_id` field returned in records with `get_before` or `get_after` specifying which direction to page.

The query system has the following features:
* Query using equality operators: equal, greater than `gt`, greater than or equal `gte`, less than `lt`, less than or equal `lte`.  An equality condition would look like `foo=bar` (field = value) while all other conditions will look like `foo=gt=500` (field = operator = value)
* Query for nested values with `.` syntax eg. `name.givenName=Joel`
