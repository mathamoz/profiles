import uuid

from service import mongo
from pymongo import ReturnDocument
from service.utils.helpers import is_email, is_domain, get_domain, get_account_profile
from service.utils.query import build_query


def __generate_uuid():
    """
    Generate a unique id

    :return: String
    """
    count = 0
    while count < 100:
        t = uuid.uuid4().hex
        if not mongo.db.profiles.find_one({'uuid': t}):
            return t
        count += 1

    raise Exception("Unable to generate unique ID")


def get_person_by_email(email):
    """
    Return the global person record for a given email

    :param email:
    :return: Dictionary
    """

    return mongo.profiles.find_one({'email': email})


def get_company_by_domain(domain):
    """
    Return the company record for a given domain

    :param domain:
    :return: Dictionary
    """

    return mongo.profiles.find_one({'domain': domain})


def create_profile(email, fname=None, lname=None, account_uuid=None):
    """
    Create a profile for the person with the given email.
    If a global person profile already exists and fname/lname are provided a new account specific
    profile will be created for the given person

    :param email:
    :param fname:
    :param lname:
    :param account_uuid:
    :return: Dictionary
    """

    # Check to see if a profile already exists for this email
    person_profile = get_person_by_email(email)

    # If we aren't overriding the first or last name we will return the existing profile
    if person_profile and not (fname or lname):
        company_profile = get_company_by_domain(email.split("@")[1])

        profiles = {
            'person': person_profile,
            'company': company_profile,
            'is_new': False,
        }

        return profiles

    domain = get_domain(email)

    # There are no records for this person yet, create them
    if not person_profile:
        try:
            person_uuid = __generate_uuid()
            company_uuid = __generate_uuid()
        except Exception as e:
            return e.message

        person = {
            'email': email,
            'uuid': person_uuid
        }

        company = {
            'domain': domain,
            'uuid': company_uuid
        }

        mongo.profiles.insert_one(person)

        # Check to make sure there isn't already a profile for this company/domain before creating another one
        company_profile = get_company_by_domain(get_domain(email))
        if not company_profile:
            mongo.profiles.insert_one(company)
            company_profile = get_company_by_domain(get_domain(email))  # Fetch the new company profile

        person_profile = get_person_by_email(email)

        is_new = True
    else:
        company_profile = get_company_by_domain(get_domain(email))
        is_new = False

    # Create the account level person override with the given first and last name
    if fname or lname:
        account_person = {
            'account_uuid': account_uuid,
            'name': {
                'fullName': ("%s %s" % (fname or '', lname or '')).strip(),
                'givenName': fname,
                'familyName': lname,
            }
        }

        mongo.profiles.find_one_and_update(
            {'uuid': person_profile.get('uuid')},
            {'$push': {'account_profiles': account_person}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    return {
        'person': person_profile,
        'company': company_profile,
        'is_new': is_new,
    }


def get_profile(identifier, account_uuid):
    """
    Fetch a profile for the given identifier.
    If the identifier is for a company only the company profile will be returned.
    If it is for a person a combined person and company profile will be returned

    :param identifier: UUID, email or domain
    :param account_uuid: UUID for the account requesting the profile
    :return: dictionary
    """

    if is_email(identifier):
        profile = mongo.profiles.find_one({'email': identifier})
    elif is_domain(identifier):
        profile = mongo.profiles.find_one({'domain': identifier})

        result = {
            'person': None,
            'company': profile
        }

        return result
    else:
        profile = mongo.profiles.find_one({'uuid': identifier})

        # Check to see if the UUID was for a company and if so return the company profile
        if profile and profile.get('domain'):
            result = {
                'person': None,
                'company': profile
            }

            return result

    if not profile:
        return None

    combined_person = profile.copy()

    # Get rid of all of the account_profiles so we can merge only the fields for this account
    combined_person.pop('account_profiles', None)

    account_profile = get_account_profile(profile, account_uuid)

    if account_profile:
        combined_person.update(account_profile)

    combined_person.pop('account_uuid', None)

    # Fetch the company profile
    combined_company = get_combined_company_profile(profile, account_uuid)
    """company_profile = mongo.profiles.find_one({'domain': get_domain(profile.get('email'))})

    combined_company = company_profile.copy()

    # Get rid of all of the account_profiles so we can merge only the fields for this account
    combined_company.pop('account_profiles', None)

    account_profile = get_account_profile(company_profile, account_uuid)

    if account_profile:
        combined_company.update(account_profile)

    combined_company.pop('account_uuid', None)"""

    result = {
        'person': combined_person,
        'company': combined_company
    }

    return result


def get_combined_company_profile(person_profile, account_uuid):
    company_profile = mongo.profiles.find_one({'domain': get_domain(person_profile.get('email'))})

    combined_company = company_profile.copy()

    # Get rid of all of the account_profiles so we can merge only the fields for this account
    combined_company.pop('account_profiles', None)

    account_profile = get_account_profile(company_profile, account_uuid)

    if account_profile:
        combined_company.update(account_profile)

    combined_company.pop('account_uuid', None)

    return combined_company


def update_profile(identifier, data, account_uuid=None):
    if is_email(identifier):
        # Find the person profile for this email
        profile = mongo.profiles.find_one({'email': identifier})
    elif is_domain(identifier):
        # Find the global company profile for this domain
        profile = mongo.profiles.find_one({'domain': identifier})
    else:
        profile = mongo.profiles.find_one({'uuid': identifier})

    # Update (or insert) the global or account record for the given identifier
    # Insert should only happen if this is an account record
    if profile and account_uuid:
        existing_profile = mongo.profiles.find_one({'uuid': profile.get('uuid')})

        # Check to see if there is already a profile for this account
        existing_account_profile = None
        if existing_profile and 'account_profiles' in existing_profile:
            for account_profile in existing_profile['account_profiles']:
                if account_profile.get('account_uuid', None) == account_uuid:
                    existing_account_profile = account_profile
                    break

        if existing_account_profile:
            # We need to remove the existing embedded document so we can push the updated data
            mongo.profiles.update(
                {'uuid': profile.get('uuid')},
                {
                    '$pull': {
                        'account_profiles': {
                            'account_uuid': account_uuid
                        }
                    }
                }
            )

            # Merge the new data into the existing data
            existing_account_profile.update(data)
        else:
            data.update({'account_uuid': account_uuid})

        return mongo.profiles.find_one_and_update(
            {'uuid': profile.get('uuid')},
            {'$push': {'account_profiles': existing_account_profile or data}},
            upsert=True,
            return_document=ReturnDocument.AFTER)
    elif profile and not account_uuid:
        return mongo.profiles.find_one_and_update(
            {'uuid': profile.get('uuid')},
            {'$set': data},
            upsert=True,
            return_document=ReturnDocument.AFTER)

    # If we get here we failed to find a match for the identifier
    return None


def run_query(query, account_uuid, cursor, sort_order=1):
    """
    Execute a user query on the database

    :param query: String
    :param account_uuid: String
    :param cursor: Dictionary or None
    :return: MongoDB Result Cursor
    """

    try:
        compiled_query = build_query(query, account_uuid)

        if cursor:
            compiled_query.update(cursor)

        return mongo.profiles.find(compiled_query).sort('_id', sort_order).limit(25)
    except Exception:
        return None