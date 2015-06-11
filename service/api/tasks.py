from service import celery

from service.utils.clearbit import query_clearbit


@celery.task
def fetch_from_clearbit(person=None, company=None, retries=0):
    """
    Fetch information for a person, company or both from Clearbit.
    If we hit an API rate limit we will queue up a retry for, at the earliest, 60 seconds from now based on the Clearbit
    documentation. The Python client doesn't support accessing the rate limit headers so we can only rely on the 400
    error that Clearbit throws when the rate limit is exceeded (unless we fell back to curl and wrote our own client)

    :param person: A person object
    :param company: A company object
    :return: void
    """

    try:
        query_clearbit(person, company)
    except Exception as exc:
        # This should do something useful with exceptions, like log to OpBeat or a similar service
        print "Got exception querying Clearbit %s" % exc.message

        if 'rate_limit' in exc.message:
            retries += 1
            if retries < 10:
                if person and company:
                    print "Queueing retry #%d for Person %s, Company %s" % (retries, person.get('uuid'), company.get('uuid'))
                elif person:
                    print "Queueing retry #%d for Person %s" % (retries, person.get('uuid'))
                elif company:
                    print "Queueing retry #%d for Company %s" % (retries, company.get('uuid'))

                fetch_from_clearbit.apply_async([person, company, retries], countdown=60)  # Retry again in a minute (Clearbit API rate limit window)
            else:
                # Toss a simple log message out that we are giving up fetching for this person/company
                # NB: It would probably be best to monitor the frequency of this condition as it would likely indicate
                #     that the Clearbit plan should be upgraded
                if person and company:
                    print "Aborting Fetch for Person %s, Company %s" % (person.get('uuid'), company.get('uuid'))
                elif person:
                    print "Aborting fetch for Person %s" % person.get('uuid')
                elif company:
                    print "Aborting fetch for Company %s" % company.get('uuid')