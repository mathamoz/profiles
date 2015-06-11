from datetime import datetime, timedelta


def is_email(identifier):
    """
    Simple check to see if the given identifier is an email based on there being an @ sign

    :param identifier: String to check
    :return: Boolean
    """

    if '@' in identifier:
        return True
    return False


def is_domain(identifier):
    """
    Simple check to see if the given identifier is a domain based on there being a period but no @ sign

    :param identifier: String to check
    :return: Boolean
    """

    if '.' in identifier and not is_email(identifier):
        return True
    return False


def get_domain(email):
    """
    Return the domain for an email or None if an error

    :param email:
    :return: String
    """

    try:
        return email.split("@")[1]
    except ValueError:
        return None


def days_ago(days):
    """
    Return a DateTime X days in the past

    :param days: Int
    :return: DateTime
    """

    return datetime.utcnow() - timedelta(days=days)


def get_account_profile(profile, account_uuid):
    """
    Quick helper function to get the account profile

    :param profile: Dictionary
    :param account_uuid: String
    :return: Dictionary or None
    """
    if profile and 'account_profiles' in profile:
        for account_profile in profile['account_profiles']:
            if account_profile.get('account_uuid', None) == account_uuid:
                return account_profile

    return None