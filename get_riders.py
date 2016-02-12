#!/usr/bin/env python
import sys, getopt, getpass
import requests
import json
import sqlite3
import os, time, stat
import mkresults
from collections import namedtuple

g_verbose = False
g_verifyCert = True

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
            verify = g_verifyCert,
        )

        if g_verbose:
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
            verify = g_verifyCert,
        )

        if g_verbose:
            print('Response HTTP Status Code: {status_code}'.format(
                status_code=response.status_code))
            print('Response HTTP Response Body: {content}'.format(
                content=response.content))

        json_dict = json.loads(response.content)
        
        return json_dict

    except requests.exceptions.RequestException, e:
        print('HTTP Request failed: %s' % e)

def login(session, user, password):
    access_token, refresh_token, expired_in = post_credentials(session, user, password)
    return access_token

def updateRider(session, access_token, user):
    # Query Player Profile
    json_dict = query_player_profile(session, access_token, user)
    if g_verbose:
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
#     zpower = 1 if (json_dict["powerSourceModel"] == "Power Meter") else 0
    fname = json_dict["firstName"].strip()
    lname = json_dict["lastName"].strip()
    print ("id=%s wt=%s m=%s [%s] <%s %s>\n" %
        (json_dict["id"], json_dict["weight"], json_dict["male"],
         json_dict["powerSourceModel"], fname.encode('ascii', 'ignore'), lname.encode('ascii', 'ignore')))
    c = dbh.cursor()
    try:
        c.execute("insert into rider " +
            "(rider_id, fname, lname, weight, height, male, zpower," +
            " fetched_at) " +
            "values (?,?,?,?,?,?,?,date('now'))",
             (json_dict["id"], fname, lname,
             json_dict["weight"], json_dict["height"], male, power))
    except sqlite3.IntegrityError:
        c.execute("update rider " +
            "set fname = ?, lname = ?, weight = ?, height = ?, male = ?," +
            " zpower = ?, fetched_at = date('now') where rider_id = ?",
             (fname, lname,
             json_dict["weight"], json_dict["height"], male, power,
             json_dict["id"]))

def usage(exename, s):
    print >>s, "Usage: %s [--verbose] [--dont-check-certificates] zwift_username conf_file" % exename

def main(argv):
    global g_verbose
    global g_verifyCert
    global conf
    global dbh

    access_token = None
    cookies = None

    try:
        opts,args=getopt.getopt(argv[1:], "", ['verbose', 'dont-check-certificates'])
    except getopt.GetoptError, e:
        sys.stderr.write("Unknown option: %s\n" % e.opt)
        usage(argv[0], sys.stderr)
        sys.exit(1)

    if len(args) != 2:
        usage(argv[0], sys.stderr)
        sys.exit(1)

    dbh = sqlite3.connect('race_database.sql3')
    mkresults.dbh = dbh
    conf = mkresults.config(args[1])
    mkresults.conf = conf
    mkresults.args = namedtuple('Args', 'no_cat debug')(no_cat=False, debug=g_verbose)
    user = args[0]

    g_verbose = False
    g_verifyCert = True

    # Post Credentials
    password = getpass.getpass("Password for %s? " % user)
    #test the credentials - token will expire, so we'll log in again after sleeping
    access_token = login(requests.session(), user, password)

    for opt,val in opts:
        if opt == '--verbose':
            g_verbose = True
        elif opt == '--dont-check-certificates':
            g_verifyCert = False

    startTime = conf.start_ms/1000
    retrievalTime = startTime + 600 #10 minute window hardcoded for now
    sleepTime = retrievalTime - time.time()
    while sleepTime > 0:
	print "Sleeping %s seconds" % sleepTime
        time.sleep(sleepTime)
        sleepTime = retrievalTime - time.time()
    conf.load_chalklines()
    R = mkresults.get_riders(conf.start_ms - mkresults.min2ms(2.0), conf.finish_ms)
    START_WINDOW = 10.0
    F = [ r for r in R.values() if mkresults.filter_start(r, START_WINDOW) ]
    if g_verbose:
        print 'Selected %d riders' % len(R)
    session = requests.session()
    access_token = login(session, user, password)

    for u in F:
        updateRider(session, access_token, u.id)
    dbh.commit()
    dbh.close()


if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
    except SystemExit, se:
        print "ERROR:",se
