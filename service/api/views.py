import json

from flask import Blueprint, request
from base64 import b64decode
from bson import ObjectId
from service.utils.auth import authenticate, get_account
from service.utils.response import json_response
from service.utils.helpers import is_email, days_ago, get_account_profile
from service.utils.clearbit import query_clearbit
from service.api.tasks import fetch_from_clearbit
from service import model


api_endpoints = Blueprint('api_endpoints', __name__)
api = api_endpoints


@api.route('/query', methods=['GET'])
@authenticate
def query_profiles():
    """
    Search for profiles matching a given query

    NB: Stale data won't be fetched when doing a query. I think this would have the potential to block for too long.
        A better course of action might be for the calling program to check the last_modified of the records returned
        and do a fetch of just that record if it is stale, but it would probably be worth looking into doing it here.

    :param API_KEY: Required account API key
    :param q: String
    :param get_before: Optional cursor and sorting direction
    :param get_after: Optional cursor and sorting direction
    :return: JSON object
    """

    account_uuid = get_account(request.args.get('API_KEY'))
    query = request.args.get('q')

    cursor = None
    sort_order = 1

    if 'get_before' in request.args:
        cursor = {
            '_id': {
                '$lt': ObjectId(request.args.get('get_before'))
            }
        }

        sort_order = -1
    elif 'get_after' in request.args:
        cursor = {
            '_id': {
                '$gt': ObjectId(request.args.get('get_after'))
            }
        }

    if query:
        data = []
        results = model.run_query(query, account_uuid, cursor, sort_order)

        if not results:
            return json_response(status=400, message="Invalid Query")
        
        for result in results:
            company_profile = None

            # If this is a person we need to fetch their company profile
            if not 'domain' in result:
                company_profile = model.get_combined_company_profile(result, account_uuid)

            # Remove the account_profiles key so we can merge in relevant data
            combined_result = result.copy()

            combined_result.pop('account_profiles', None)

            account_profile = get_account_profile(result, account_uuid)

            if account_profile:
                combined_result.update(account_profile)

            data.append({
                'person': combined_result,
                'company': company_profile
            })

        return json_response(data=data)

    return json_response(status=400, message="No query provided")


@api.route('/<string:email>', methods=['POST'])
@authenticate
def register(email):
    """
    Register a new customer by their email address

    :param email: Email address for the customer
    :param API_KEY: Required account API key
    :param fname: Optional first name
    :param lname: Optional last name
    :return: JSON object
    """

    if not is_email(email):
        return json_response(status=400, message="Invalid Email Address")

    fname = request.args.get('fname', None)
    lname = request.args.get('lname', None)
    account_uuid = get_account(request.args.get('API_KEY'))

    result = model.create_profile(email, fname, lname, account_uuid)

    if type(result) is dict:
        if result.get('is_new'):
            fetch_from_clearbit.delay(result.get('person'), result.get('company'))

        response = {
            'person_uuid': result.get('person').get('uuid'),
            'company_uuid': result.get('company').get('uuid'),
        }

        return json_response(data=response)

    return json_response(status=500, message=result)


@api.route('/<string:profile_identifier>', methods=['GET'])
@authenticate
def get_profile(profile_identifier):
    """
    Return all profile information for the requested email or company

    :param profile_identifier: UUID, email or domain to fetch a profile for
    :param API_KEY: Required account API key
    :return: JSON object
    """

    account_uuid = get_account(request.args.get('API_KEY'))
    profile = model.get_profile(profile_identifier, account_uuid)

    if not profile:
        return json_response(status=404, message="No Profile Found")

    # Check to see if either the person or company profiles are stale and update them if necessary
    person = profile.get('person')
    company = profile.get('company')

    profile_updated = False

    if person:
        if not 'last_updated' in person or person.get('last_updated') < days_ago(30):
            try:
                if query_clearbit(person=person):
                    profile_updated = True
            except Exception:
                # Something went wrong, return whatever we already have
                pass

    if company:
        if not 'last_updated' in company or company.get('last_updated') < days_ago(30):
            try:
                if query_clearbit(company=company):
                    profile_updated = True
            except Exception:
                # Something went wrong, return whatever we already have
                pass

    if profile_updated:
        profile = model.get_profile(profile_identifier, account_uuid)  # Fetch the updated profile info to return

    return json_response(status=200, data=profile)


@api.route('/<string:profile_identifier>', methods=['PUT'])
@authenticate
def update_profile(profile_identifier):
    """
    Add or update a profile with the given information

    :param profile_identifier: UUID, email or domain for the profile to update
    :param API_KEY: Required account API key
    :param data: Required data hash to save to the profile
    :return: HTTP Status Code
    """

    account_uuid = get_account(request.args.get('API_KEY'))
    encoded_data = request.args.get('data', None)

    if encoded_data:
        # The data should be a base64 encoded JSON string
        data = json.loads(b64decode(encoded_data))

        model.update_profile(profile_identifier, data, account_uuid)
        return json_response(message="Profile Updated")

    return json_response(status=400, message="No data provided")