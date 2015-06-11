import json

from functools import wraps
from flask import request, Response

from .response import json_response


# A few mock accounts
accounts = [
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
    },
]


def get_account(api_key):
    """
    Mock function to return the UUID for an account based on API key.
    This would query a database or make an API call in production

    :param api_key: Account specific API key
    :return: Account UUID or None
    """

    for account in accounts:
        if account['api_key'] == api_key:
            return account['uuid']

    return None


def authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        """
        Validate a request by account API key from the URL
        """

        api_key = request.args.get('API_KEY', None)
        account = get_account(api_key)

        if not account:
            # No account found, abort the request with a 401 unauthorized
            return json_response(401, 'Invalid API Key')
        return f(*args, **kwargs)
    return decorated