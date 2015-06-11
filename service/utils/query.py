def __value_is_number(value):
    """
    Check if a given string value is an integer

    :param value: String
    :return: boolean
    """

    try:
        int(value)
    except ValueError:
        return False

    return True


def __value_is_float(value):
    """
    Check if a given string value is a float

    :param value: String
    :return: boolean
    """

    try:
        float(value)
    except ValueError:
        return False

    return True


def __parse_value(value):
    """
    Convert a given string value into a non-string value if it is one

    :param value: String
    :return:
    """

    if __value_is_number(value):
        return int(value)

    if __value_is_float(value):
        return float(value)

    return value


def __get_operator(value):
    """
    Check if a given value is a valid MongoDB operator and if so return the MongoDB query format of the operator

    :param value: String
    :return: String or None
    """

    operators = ['lt', 'gt', 'lte', 'gte']

    if value.lower() in operators:
        return '$%s' % value.lower()
    return None


def build_query(query, account_uuid):
    """
    Quick and dirty function to build a MongoDB query from a query string for a given account
    NB: This probably has some security flaws given it's more or less running what it's given...

    TODO: Add the ability for custom OR conditions

    :param query: String
    :param account_uuid: String
    :return: Dictionary
    """

    # The query will look something like ?q=foo=bar,baz=lt=5
    conditions = query.split(',')

    global_query = {}
    account_query = {'account_profiles.account_uuid': account_uuid}

    for condition in conditions:
        parts = condition.split('=')

        if len(parts) == 2:
            # Simple equality condition
            value = __parse_value(parts[1])
            global_query[parts[0]] = value
            account_query["account_profiles.%s" % parts[0]] = value
        elif len(parts) == 3: 
            # gt, lt, gte, lte condition
            operator = __get_operator(parts[1])
            if operator:
                value = __parse_value(parts[2])
                global_query[parts[0]] = {operator: value}
                account_query["account_profiles.%s" % parts[0]] = {operator: value}
            else:
                raise Exception("Invalid Query")

    return {
        '$or': [
            global_query,
            account_query
        ]
    }


#print build_query("foo=bar,baz=lt=5,bazinga=gte=500", "f8423b394ba447ff80b6cdad00435d07")
#print build_query("occupation=Software Engineer,salary=gte=80000", "f8423b394ba447ff80b6cdad00435d07")
