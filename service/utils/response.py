import json

from flask import Response
from bson import ObjectId


def __convert_objects(obj):
    """
    Convert target objects into strings that JSON can serialize

    :param obj: Object
    :return: Object
    """

    if isinstance(obj, ObjectId):
        return str(obj)

    if hasattr(obj, 'isoformat'):
        return obj.isoformat()

    return obj


def json_response(status=200, message=None, data=None):
    """
    Return a Response object for the view to return

    :param status: HTTP Status code
    :param message: A string indicating the reason for the response code
    :param data: Optional data object
    :return: Response
    """

    response = {
        'success': False,
        'message': message,
        'data': data,
    }

    # A status code in the 2xx range is considered a successful response
    if status >= 200 and status < 300:
        response['success'] = True

    return Response(response=json.dumps(response, default=__convert_objects), status=status, content_type='application/json')