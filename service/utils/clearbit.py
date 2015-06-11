from datetime import datetime
from requests.exceptions import HTTPError

from service import clearbit, model


def __update_record(uuid, data):
    """
    Add an updated timestamp to the data and save it

    :param uuid: UUID of the record to update
    :param data: Dict of data to update
    :return: Updated record
    """

    last_updated = datetime.utcnow()

    if data:
        data['last_updated'] = last_updated
    else:
        data = {'last_updated': last_updated}  # No profile data was returned from Clearbit, we need a last_updated though

    return model.update_profile(uuid, data)


def query_clearbit(person=None, company=None):
    try:
        if person and company:
            result = clearbit.PersonCompany.find(email=person.get('email'), stream=True)

            person_info = []
            company_info = []

            if result:
                person_info = result['person']
                company_info = result['company']

            __update_record(person.get('uuid'), person_info)
            __update_record(company.get('uuid'), company_info)
        elif person:
            result = clearbit.Person.find(email=person.get('email'), stream=True)

            __update_record(person.get('uuid'), result)
        elif company:
            result = clearbit.Company.find(domain=company.get('domain'), stream=True)

            __update_record(company.get('uuid'), result)

        return True
    except HTTPError as exc:
        if exc.response.status_code == 400 and 'rate_limit' in exc.response.message:
            raise Exception('rate_limit')
        return False
    except Exception as exc:
        # Something went really wrong
        # TODO: Figure out what went wrong and what, if anything, can be done about it
        return False
