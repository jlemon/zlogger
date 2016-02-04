#!/usr/bin/env python
import sys, getopt, getpass
import requests
import json
import lxml.html
import re
import sqlite3
import os, time, stat
import mkresults
from collections import namedtuple

g_verbose = False
g_verifyCert = True

def get_logon_form(session):
    # Get Initial Form Logon Code
    # GET https://secure.zwift.com/auth/realms/zwift/tokens/login
    try:
        response = session.get(
            url="https://secure.zwift.com/auth/realms/zwift/tokens/login",
            params={
                "client_id": "Zwift Scheme",
                "redirect_uri": "zwift://localhost/",
                "login": "true",
            },
            headers={
                "Accept-Encoding": "gzip, deflate",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "keep-alive",
                "Host": "secure.zwift.com",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 9_0_2 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13A452",
                "Accept-Language": "en-us",
            },
            verify = g_verifyCert,
        )
        
        if g_verbose:
            print('Response HTTP Status Code: {status_code}'.format(
                status_code=response.status_code))
            print('Response HTTP Response Body: {content}'.format(
                content=response.content))

        # locate form action
        doc = lxml.html.fromstring(response.content)
        form = doc.forms[0]
        if g_verbose:
            print('Form Action: {keys}'.format(keys=form.action))

        # extract logon "code" from form action
        p = re.compile(ur'code=(.*)$')
        match = re.search(p, form.action)
        code = match.group(1)
        
        return code
    except requests.exceptions.RequestException, e:
        print('HTTP Request failed: %s', e)

def post_credentials(session, code, username, password):
    # Credentials POST
    # POST https://secure.zwift.com/auth/realms/zwift/login-actions/request/login
    try:
        response = session.post(
            url="https://secure.zwift.com/auth/realms/zwift/login-actions/request/login",
            params={
                "code": code,
            },
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Origin": "https://secure.zwift.com",
                "Connection": "keep-alive",
                "Referer": "https://secure.zwift.com/auth/realms/zwift/tokens/login?client_id=Zwift+Scheme&redirect_uri=zwift%3A%2F%2Flocalhost%2F&login=true",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "secure.zwift.com",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 9_0_2 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13A452",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-us",
            },
            data={
                "login": "Log in",
                "username": username,
                "password": password,
            },
            allow_redirects = False,
            verify = g_verifyCert,
        )

        if g_verbose:
            print('Response HTTP Status Code: {status_code}'.format(
                status_code=response.status_code))
            print('Response HTTP Response Body: {content}'.format(
                content=response.content))
            print('Response HTTP Response Location Header: {location}'.format(
                location=response.headers["Location"]))

        # extract logon "code" from Location header
        p = re.compile(ur'code=(.*)$')
        match = re.search(p, response.headers["Location"])
        code = match.group(1)

        return code
    except requests.exceptions.RequestException, e:
        print('HTTP Request failed: %s' % e)

def query_tokens(session, code):
    # Query Access and Refresh Tokens
    # POST https://secure.zwift.com/auth/realms/zwift/tokens/access/codes
    try:
        response = session.post(
            url="https://secure.zwift.com/auth/realms/zwift/tokens/access/codes",
            headers={
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "secure.zwift.com",
                "Content-Length": "108",
                "User-Agent": "Zwift/115 CFNetwork/758.0.2 Darwin/15.0.0",
                "Accept-Language": "en-us",
            },
            data={
                "client_id": "Zwift Scheme",
                "code": code,
            },
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
        print('HTTP Request failed: %s', e)

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
    # Get Logon Form
    code = get_logon_form(session)
    if code is None or len(code) == 0:
        sys.stderr.write("Unable to retrieve code from logon form.\n")
        sys.exit(1)

    code = post_credentials(session, code, user, password)

    # Query tokens
    access_token, refresh_token, expired_in = query_tokens(session, code)
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
    login(requests.session(), user, password)

    for opt,val in opts:
        if opt == '--verbose':
            g_verbose = True
        elif opt == '--dont-check-certificates':
            g_verifyCert = False

    startTime = conf.start_ms/1000
    retrievalTime = startTime + 600 #10 minute window hardcoded for now
    sleepTime = retrievalTime - time.time()
    if sleepTime > 0:
        if g_verbose:
            print "Sleeping %s seconds" % sleepTime
        time.sleep(sleepTime)
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
