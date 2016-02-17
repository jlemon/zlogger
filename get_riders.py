#!/usr/bin/env python
import sys, argparse, getpass
import requests
import json
import sqlite3
import os, time, stat
import mkresults
from collections import namedtuple

global args
global dbh

def post_credentials(session, username, password):
    # Credentials POSTing and tokens retrieval
    # POST https://secure.zwift.com/auth/realms/zwift/tokens/access/codes

    try:
        response = session.post(
            url="https://secure.zwift.com/auth/realms/zwift/tokens/access/codes",
            headers={
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "secure.zwift.com",
                "User-Agent": "Zwift/1.5 (iPhone; iOS 9.0.2; Scale/2.00)",
                "Accept-Language": "en-US;q=1",
            },
            data={
                "client_id": "Zwift_Mobile_Link",
                "username": username,
                "password": password,
                "grant_type": "password",
            },
            allow_redirects = False,
            verify = args.verifyCert,
        )

        if args.verbose:
            print('Response HTTP Status Code: {status_code}'.format(
                status_code=response.status_code))
            print('Response HTTP Response Body: {content}'.format(
                content=response.content))

        json_dict = json.loads(response.content)

        return (json_dict["access_token"], json_dict["refresh_token"], json_dict["expires_in"])

    except requests.exceptions.RequestException, e:
        print('HTTP Request failed: %s' % e)

def query_player_profile(session, access_token, player_id):
    # Query Player Profile
    # GET https://us-or-rly101.zwift.com/api/profiles/<player_id>
    try:
        response = session.get(
            url="https://us-or-rly101.zwift.com/api/profiles/%s" % player_id,
            headers={
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
                "Connection": "keep-alive",
                "Host": "us-or-rly101.zwift.com",
                "User-Agent": "Zwift/115 CFNetwork/758.0.2 Darwin/15.0.0",
                "Authorization": "Bearer %s" % access_token,
                "Accept-Language": "en-us",
            },
            verify = args.verifyCert,
        )

        if args.verbose:
            print('Response HTTP Status Code: {status_code}'.format(
                status_code=response.status_code))
            print('Response HTTP Response Body: {content}'.format(
                content=response.content))

        json_dict = json.loads(response.content)
        
        return json_dict

    except requests.exceptions.RequestException, e:
        print('HTTP Request failed: %s' % e)

def logout(session, refresh_token):
    # Logout
    # POST https://secure.zwift.com/auth/realms/zwift/tokens/logout
    try:
        response = session.post(
            url="https://secure.zwift.com/auth/realms/zwift/tokens/logout",
            headers={
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "secure.zwift.com",
                "User-Agent": "Zwift/1.5 (iPhone; iOS 9.0.2; Scale/2.00)",
                "Accept-Language": "en-US;q=1",
            },
            data={
                "client_id": "Zwift_Mobile_Link",
                "refresh_token": refresh_token,
            },
            verify = args.verifyCert,
        )
        if args.verbose:
            print('Response HTTP Status Code: {status_code}'.format(
                status_code=response.status_code))
            print('Response HTTP Response Body: {content}'.format(
                content=response.content))
    except requests.exceptions.RequestException, e:
        print('HTTP Request failed: %s' % e)

def login(session, user, password):
    access_token, refresh_token, expired_in = post_credentials(session, user, password)
    return access_token, refresh_token

def updateRider(session, access_token, user):
    # Query Player Profile
    json_dict = query_player_profile(session, access_token, user)
    if args.verbose:
        print ("\n")
        print (json_dict)
    male = 1 if json_dict["male"] else 0
    # Power Meter, Smart Trainer, zPower
    if (json_dict["powerSourceModel"] == "zPower"):
        power = 1
    elif (json_dict["powerSourceModel"] == "Smart Trainer"):
        power = 2
    else:
        power = 3
    fname = json_dict["firstName"].strip()
    lname = json_dict["lastName"].strip()
    print ("id=%s wt=%s m=%s [%s] <%s %s>\n" %
        (json_dict["id"], json_dict["weight"], json_dict["male"],
         json_dict["powerSourceModel"], fname.encode('ascii', 'ignore'), lname.encode('ascii', 'ignore')))
    c = dbh.cursor()
    try:
        c.execute("insert into rider " +
            "(rider_id, fname, lname, age, weight, height, male, zpower," +
            " fetched_at) " +
            "values (?,?,?,?,?,?,?,?,date('now'))",
             (json_dict["id"], fname, lname, json_dict["age"],
             json_dict["weight"], json_dict["height"], male, power))
    except sqlite3.IntegrityError:
        c.execute("update rider " +
            "set fname = ?, lname = ?, age = ?, weight = ?, height = ?," +
            " male = ?, zpower = ?, fetched_at = date('now')" +
            " where rider_id = ?",
             (fname, lname, json_dict["age"],
             json_dict["weight"], json_dict["height"], male, power,
             json_dict["id"]))


def get_rider_list():
    mkresults.dbh = sqlite3.connect('race_database.sql3')
    conf = mkresults.config(args.config)
    mkresults.conf = conf
    mkresults.args = namedtuple('Args', 'no_cat debug')(no_cat=False, debug=args.verbose)

    startTime = conf.start_ms / 1000
    retrievalTime = startTime + conf.start_window_ms / 1000
    sleepTime = retrievalTime - time.time()
    while sleepTime > 0:
        print "Sleeping %s seconds" % sleepTime
        time.sleep(sleepTime)
        sleepTime = retrievalTime - time.time()
    conf.load_chalklines()
    grace_ms = max(mkresults.min2ms(2.0), conf.grace_ms)
    if args.verbose:
        print "Grace period (ms): %s" % grace_ms
    R, all_pos = mkresults.get_riders(conf.start_ms - grace_ms, conf.finish_ms)
    return [ r.id for r in R.values() if mkresults.filter_start(r) ]

def main(argv):
    global args
    global dbh

    access_token = None
    cookies = None

    parser = argparse.ArgumentParser(description = 'Zwift Name Fetcher')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='Verbose output')
    parser.add_argument('--dont-check-certificates', action='store_false',
            dest='verifyCert', default=True)
    parser.add_argument('-c', '--config', help='Use config file')
    parser.add_argument('-u', '--user', help='Zwift user name')
    parser.add_argument('idlist', metavar='rider_id', type=int, nargs='*',
            help='rider ids to fetch')
    args = parser.parse_args()

    if args.user:
        password = getpass.getpass("Password for %s? " % args.user)
    else:
        file = os.environ['HOME'] + '/.zwift_cred.json'
        with open(file) as f:
            try:
                cred = json.load(f)
            except ValueError, se:
                sys.exit('"%s": %s' % (args.output, se))
        f.close
        args.user = cred['user']
        password = cred['pass']

    session = requests.session()

    # test the credentials - token will expire, so we'll log in again after sleeping
    access_token, refresh_token = login(session, args.user, password)
    logout(session, refresh_token)

    if args.config:
        L = get_rider_list()
    elif args.idlist:
        L = args.idlist
    else:
        L = [ int(line) for line in sys.stdin ]

    if args.verbose:
        print 'Selected %d riders' % len(L)

    access_token, refresh_token = login(session, args.user, password)

    dbh = sqlite3.connect('rider_names.sql3')
    for id in L:
        updateRider(session, access_token, id)
    dbh.commit()
    dbh.close()

    logout(session, refresh_token)

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
    except SystemExit, se:
        print "ERROR:",se
