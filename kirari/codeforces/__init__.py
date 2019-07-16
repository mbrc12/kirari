import sys
import json
import logging

from urllib.request import Request, urlopen

api_base = "http://codeforces.com/api/"

logger = logging.getLogger(__name__)

def make_url(method, **kwargs):
    call = api_base + method + "?"
    if kwargs == {}:
        return call

    for key in kwargs:
        call += "%s=%s&" % (key, kwargs[key])

    return call[:-1]

def get_data(method, **kwargs):
    call = make_url(method, **kwargs)
    data = ""
    
    req = Request(call)

    try:
        data = urlopen(req).read()
    except Exception:
        logger.error("Fetching [%s] resulted in error." % call)
        return {}

    return json.loads(data)

def user_exists(user):
    data = get_data("user.rating", handle = user)
    try:
        if (data["status"] == "OK"):
            return True
        else:
            return False
    except Exception:
        return False

def user_accepted_ratings(user):
    
    if not user_exists(user):
        return []

    data = get_data("user.status", handle = user, first = 1, count = 10 ** 8)

    ratings = []
    already_seen = set([])
    for submission in data["result"]:
        try:
            if submission["verdict"] == "OK":
                problem = submission["problem"]
                pid = str(problem["contestId"]) + str(problem["index"])
                if pid in already_seen:
                    continue
                already_seen.add(pid)
                rating = problem["rating"]
                ratings.append(int(rating))
            else:
                continue
        except:
            pass
    return ratings

def user_coins(user):
    return sum(user_accepted_ratings(user))


