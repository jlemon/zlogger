#!/usr/bin/env python
import sys, argparse
import json
import sqlite3
import os, time, stat
import re

# import requests
# import lxml.html

RICHMOND_LAP = 16 * 1000                # 1 lap of richmond = 16.09km

class rider():
    def __init__(self, id):
        self.id         = id
        self.pos        = []
        self.set_info(('Rider', str(id), None, 0, 0, None, None))

        self.finish     = []
        self.end_time   = None
        self.dq_time    = None
        self.dq_reason  = None
        self.distance   = None

    def __str__(self):
        return '%6d %-35.35s records: %d' % (
                self.id, self.name, len(self.pos))

    def set_info(self, v):
        if not v:
            return
        self.fname      = v[0]
        self.lname      = v[1]
        self.cat        = v[2] or 'X'
        self.weight     = v[3]
        self.height     = v[4]
        self.male       = True if v[5] else False
        self.power      = [ '?', '*', ' ', ' ' ][v[6] or 0]
        self.name       = (self.fname + ' ' + self.lname).encode('utf-8')

        cat = None
        #
        # Try autodetecting cat from name.
        #  Could filter riders by race tag also.
        #

        # NAME (X)
        #   match category in parenthesis at end of name.
        m = re.match('.*[(](.)[)]$', self.lname)
        cat = m.group(1).upper() if m else None

        # NAME X
        #    match single letter at end of name. 
        if cat is None:
            m = re.match('.*\s(.)$', self.lname)
            cat = m.group(1).upper() if m else None

        # NAME RACE-X
        #   match single letter following dash at end of name. 
        if cat is None:
            m = re.match('.*[-](.)$', self.lname)
            cat = m.group(1).upper() if m else None

        # NAME (RACE X)
        #   match single letter with trailing paren at end of name. 
        if cat is None:
            m = re.match('.*\s(.)[)]$', self.lname)
            cat = m.group(1).upper() if m else None

        # NAME RACE-X INFO
        # NAME RACE-X) INFO
        #   match single letter following dash in name.
        if cat is None:
            m = re.match('.*[-](.)[ )].*', self.lname)
            cat = m.group(1).upper() if m else None

        # NAME (X) INFO
        #   match category in parenthesis in name.
        if cat is None:
            m = re.match('.*[(](.)[)].*', self.lname)
            cat = m.group(1).upper() if m else None

        # NAME RACE X) INFO
        #   match single letter following space in name.
        if cat is None:
            m = re.match('.*\s(.)[)].*', self.lname)
            cat = m.group(1).upper() if m else None

        #
        # Sanity check cat - force to known categories.
        #
        if cat is not None:
            cat = cat if cat in 'ABCDW' else None
        if (cat is not None) and (cat != 'X'):
            self.cat = cat
        
        #
        # No Database or self-classification, report by start group.
        #
        if (args.no_cat):
            self.cat        = 'X'


    #
    # Rider is DQ'd at this time for the given reason.
    #  DQ is ignored if rider completes before the timepoint.
    #
    def set_dq(self, time_ms, reason):
        if (self.dq_time is None) or (time_ms < self.dq_time):
            self.dq_time = time_ms;
            self.dq_reason = reason


    def data(self):
        return {
            'id': self.id, 'fname': self.fname, 'lname': self.lname,
            'cat': self.cat, 'height': self.height / 10,
            'weight': float(self.weight) / 1000, 
            'power': self.power,
            'male': True if self.male else False }


#
# Observed position record, keyed by observation time.
#
class pos():
    def __init__(self, v):
        self.time_ms    = v[0]
        self.line_id    = v[1]
        self.forward    = v[2]
        self.meters     = v[3]
        self.mwh        = v[4]
        self.duration   = v[5]
        self.elevation  = v[6]
        self.speed      = float((v[7] or 0) / 1000)     # meters/hour
        self.hr         = v[8]

    def __str__(self):
        return ("time: %d  %s  line: %d %s  metres: %d" %
                (self.time_ms, time.ctime(self.time_ms / 1000), self.line_id,
                'FWD' if self.forward else 'REV', self.meters))

    def data(self):
        return {
            'time_ms': self.time_ms, 'mwh': self.mwh, 'line': self.line_id,
            'duration': self.duration, 'meters': self.meters,
            'hr': self.hr, 'speed': self.speed,
            'forward': True if self.forward else False }


#
# Get all position events within the specified timeframe.
#  Returns a list of riders, containing their position records.
#
def get_riders(begin_ms, end_ms):
    R = {}
    c = dbh.cursor()
    for data in c.execute('select rider_id, time_ms, line_id, forward,' +
            ' meters, mwh, duration, elevation, speed, hr from pos' +
            ' where time_ms between ? and ? order by time_ms asc',
            (begin_ms, end_ms)):
        id = data[0]
        if not id in R:
            R[id] = rider(id)
        R[id].pos.append(pos(data[1:]))
        if (args.debug):
            print id, R[id].pos[-1]
    return R


#
# Maps the chalkline name into a line_id.
#
def get_line(val):
    m = re.match('{\s+(.*)\s+}', val)
    if not m:
        sys.exit('Could not parse %s' % val)
    c = dbh.cursor()
    c.execute('select line_id from chalkline where name = ?',
            (m.group(1),))
    data = c.fetchone()
    if not data:
        sys.exit('Could not find line { %s }' % m.group(1))
    return (m.group(1), data[0])


def rider_info(r):
    c = dbh.cursor()
    c.execute('select fname, lname, cat, weight, height,' +
            ' male, zpower from rider' +
            ' where rider_id = ?', (r.id,))
    r.set_info(c.fetchone())


#
# XXX - sample for organized team-only rides.
#
def get_odz(R):
    ODZ = []
    c = dbh.cursor()
    for data in c.execute('select rider_id, team, cat from odz'):
        id = data[0]
        if not id in R:
            R[id] = rider(id)
        r.cat = r[2]
        r.team = r[1]
        ODZ.append(r)
    return ODZ

MSEC_PER_HOUR   = (60 * 60 * 1000)
MSEC_PER_MIN    = (60 * 1000)
MSEC_PER_SEC    = (1000)

class msec_time():
    def __init__(self, msec):
        msec = ((msec + 99) / 100) * 100                    # roundup
        self.hour = msec / MSEC_PER_HOUR
        msec = msec - (self.hour * MSEC_PER_HOUR)
        self.min = msec / MSEC_PER_MIN
        msec = msec - (self.min * MSEC_PER_MIN)
        self.sec = msec / MSEC_PER_SEC
        msec = msec - (self.sec * MSEC_PER_SEC)
        self.msec = msec / 100                              # to 1/10th sec


base_ms = 0
def make_timepos(prev_ms, start_ms, finish_ms):
    global base_ms
    mark = ' '

    if (prev_ms == 0):
        #
        # save winner's finish timetime - all diffs are from this
        #
        base_ms = finish_ms
        cur_ms = finish_ms - start_ms;
    elif ((finish_ms - prev_ms) < 200):
        return "--- ST ---"
    else:
        cur_ms = finish_ms - base_ms
        mark = '+'

    t = msec_time(cur_ms)

    if (t.hour != 0):
        timepos = "%2d:%02d:%02d.%d" % (t.hour, t.min, t.sec, t.msec)
    elif (t.min != 0):
        timepos = "%c  %2d:%02d.%d" % (mark, t.min, t.sec, t.msec)
    elif (t.sec != 0):
        timepos = "%c    :%02d.%d" % (mark, t.sec, t.msec)
    elif (t.msec != 0):
        timepos = "%c    :00.%d" % (mark, t.msec)
    else:
        # s.t. is transitive, return first one
        timepos = "--- ST ---";

    return timepos


def show_nf(tag, finish):
    h1 = '==== %s ' % (tag)
    h1 += '=' * (54 - len(h1))
    h1 += '  km'
    print '\n' + h1
    for r in finish:
        line = ("%-15.15s  %-35.35s  %5.1f" %
                (r.dq_reason or '',
                r.name,
                float(r.distance) / 1000))
        if (args.ident):
            line += "  ID %6d" % r.id
            line += '  [ ' + stamp(r.pos[0].time_ms) + ' - '
            if r.end:
                line += stamp(r.end.time_ms) + ' ]'
            if (args.debug):
                line += ' start m=' + str(r.pos[0].meters)
        print line


#
# Key is really just name.  may have "team results".
# finish records, start_time, start_lead, 
#   start group AB, but finish results in A and B.
#
# Assume all riders have same start group.
#  (otherwise the race doesn't make much sense...)
#
def show_results(F, tag):
    N = 28

    if not F:
        return
    grp = F[0].grp
    h0 = ' ' * (N + 36);
    h0 =  '== START @ %8.8s by %.22s' % (stamp(grp.start_ms),
            grp.starter.name if grp.starter else 'clock')
    h0 += ' ' + '=' * (N + 18 - len(h0))
    h0 += ' ' * 16
    h0 += ' est  ht  hrtrate'
    h1 =  '== RESULTS for %s ' % (tag)
    h1 += '=' * (N + 19 - len(h1))
    h1 += '  km  avgW  W/kg cat  cm  beg end'
    h1 += '  [ split times in km/hr ]' if args.split else ''
    h1 += '      ID [  start time  -  finish time ]' if args.ident else ''
    print '\n' + h0 + '\n' + h1

    c = dbh.cursor()
    pos = 0
    last_ms = 0
    for r in F:
        pos = pos + 1
        s = r.pos[0]
        e = r.end

        (last_ms, mwh, meters, watts, wkg, ecat, timepos) = \
                summarize_ride(r, last_ms)

        line = ("%2d. %s%c  %-*.*s  %5.1f  %3ld  %4.2f  %c  %3d  %3d %3d" % (
                pos, 
                timepos,
                r.power,
                N, N, r.name,
                float(meters) / 1000,
                watts, wkg, ecat, r.height / 10,
                s.hr, e.hr))

        if (args.split):
            l = s
            split = []
            end = r.pos.index(r.end)
            for p in r.pos[1 : end + 1]:
                dist = (p.meters - l.meters)
                msec = (p.time_ms - l.time_ms)
                pace = (float(dist) / float(msec)) * 3600
                split.append("%4.1f" % (pace))
                l = p
            dist = (l.meters - s.meters)
            msec = (l.time_ms - s.time_ms)
            pace = (float(dist) / float(msec)) * 3600
            split.append("= avg %4.1f" % (pace))
            line += '  [ %s ]' % ('  '.join(split))

        if (args.ident):
            line += '  %6d' % r.id
            line += ' [ ' + stamp(r.pos[0].time_ms) + ' - '
            line += stamp(r.end.time_ms) + ' ]'

        print line

        if (args.update_cat and (r.cat == 'X')):
            c.execute('update rider set cat = ? where rider_id = ?',
                (ecat, r.id))
    dbh.commit();


def results(tag, F):
    done = set()

    t = msec_time(-time.timezone * 1000)
    tzoff = 'UTC%+03d:%02d' % (t.hour, t.min)
    print '=' * 80
    print '=' * 10,
    print '%s   %s: %s' % (conf.date, conf.id, conf.name)
    print '=' * 10,
    print '    start: %s   cutoff: %s  %s' % (hms(conf.start_ms), hms(conf.finish_ms), tzoff)
    print '=' * 80

    #
    # create a sorted list of known rider categories
    #
    C = sorted(list(set([ r.cat for r in F ])))
    for cat in C:
        L = [ r for r in F if r.cat == cat ]
        dnf = set([ r for r in L if filter_dnf(r) ])
        dq = set([ r for r in L if filter_dq(r) ]).difference(dnf)
        finish = set(L).difference(dq).difference(dnf)
        finish = sorted(finish, key = lambda r: r.end_time)
        show_results(finish, 'CAT ' + cat)
        done = set(done).union(finish)

    #
    # Lump all DQ/dnf together...
    #
    dnf = set([ r for r in F if filter_dnf(r) ]).difference(done)
    dq = set([ r for r in F if filter_dq(r) ]).difference(dnf)
    if len(dq):
        finish = sorted(dq, key = lambda r: r.distance, reverse = True)
        finish = [ r for r in finish if r.distance > 0 ]
        show_nf('DQ, all', finish)
    if len(dnf):
        finish = sorted(dnf, key = lambda r: r.distance, reverse = True)
        finish = [ r for r in finish if r.distance > 0 ]
        show_nf('DNF, all', finish)

    if (True):
        return

    #
    # repeat - show DQ and DNF at end.
    #
    for cat in C:
        L = [ r for r in F if r.cat == cat ]
        dnf = set([ r for r in L if filter_dnf(r) ])
        dq = set([ r for r in L if filter_dq(r) ]).difference(dnf)
        
        dq = dq - done
        dnf = dnf - done

        if len(dq):
            finish = sorted(dq, key = lambda r: r.distance)
            finish = [ r for r in finish if r.distance > 0 ]
            show_nf('DQ, CAT ' + cat, finish)
        if len(dnf):
            finish = sorted(dnf, key = lambda r: r.distance)
            finish = [ r for r in finish if r.distance > 0 ]
            show_nf('DNF, CAT ' + cat, finish)


def summarize_ride(r, last_ms):
    s = r.pos[0]
    e = r.end

    mwh = e.mwh - s.mwh
    meters = e.meters - s.meters
    watts = 0
    if (e != s):
        watts = (float(mwh) * 3600) / (e.time_ms - s.time_ms)
    wkg = 0
    if r.weight:
        wkg = (watts * 1000) / r.weight

    if (wkg == 0):      ecat = 'X'
    elif (not r.male):  ecat = 'W'
    elif (wkg > 4):     ecat = 'A'
    elif (wkg > 3.2):   ecat = 'B'
    elif (wkg > 2.5):   ecat = 'C'
    else:               ecat = 'D'

    timepos = make_timepos(last_ms, s.time_ms, e.time_ms)
    return (e.time_ms, mwh, meters, watts, wkg, ecat, timepos)


def json_cat(F, key):
    pos = 0
    last_ms = 0
    cat_finish = []
    for r in F:
        pos = pos + 1
        s = r.pos[0]
        e = r.end

        (last_ms, mwh, meters, watts, wkg, ecat, timepos) = \
                summarize_ride(r, last_ms)

        finish = {
            'timepos': timepos, 'meters': meters,
            'mwh': mwh, 'duration': e.duration - s.duration,
            'start_msec': s.time_ms, 'end_msec': e.time_ms,
            'watts': int(watts), 'est_cat': ecat, 'pos': pos,
            'wkg': float(int(wkg * 100)) / 100,
            'beg_hr': s.hr, 'end_hr': e.hr }
        entry = { 'rider': r.data(), 'finish': finish }
        cat_finish.append(entry)

        if not args.split:
            continue

        cross = []
        end = r.pos.index(r.end)
        for p in r.pos[0 : end + 1]:
            cross.append(p.data())
        entry['cross'] = cross

    # distance, start_time

    return { 'name': key, 'results': cat_finish }


def dump_json(race_name, start_ms, F):
    result = []
    C = sorted(list(set([ r.cat for r in F ])))
    dq = set([ r for r in F if filter_dq(r) ])
    for cat in C:
        L = [ r for r in F if r.cat == cat ]
        dq = set([ r for r in L if filter_dq(r) ])
        dnf = set([ r for r in L if filter_dnf(r) ])
        finish = set(L).difference(dq).difference(dnf)
        finish = sorted(finish, key = lambda r: r.end_time)
        result.append(json_cat(finish, cat))
        if len(dq):
            finish = sorted(dq, key = lambda r: r.distance)
            finish = [ r for r in finish if r.distance > 0 ]

            # take last record as finish pos... ugh.
            for r in finish:
                r.end = r.pos[-1]
                r.end_time = r.end.time_ms
            
            result.append(json_cat(finish, 'DQ-' + cat))
        if len(dnf):
            finish = sorted(dnf, key = lambda r: r.distance)
            finish = [ r for r in finish if r.distance > 0 ]

            # take last record as finish pos... ugh.
            for r in finish:
                r.end = r.pos[-1]
                r.end_time = r.end.time_ms
            
            result.append(json_cat(finish, 'DNF-' + cat))
    race = { 'race': race_name, 'date': conf.date, 'group' : result }
    print json.dumps(race)


def min2ms(x):
    return x * 60 * 1000 


def hms(msec):
    t = time.localtime(msec / 1000)
    return time.strftime('%H:%M:%S', t)


def stamp(msec):
    return hms(msec) + ('.%03d' % (msec % 1000))



#
# Return only those riders which fall within the start window.
#   Trim the position record to the correct start.
#
# rider may have crossed start line, then gone back and restarted.
# yes - happened in KISS race.
#  find the _last_ correct line crossing in the start window.
#   (may be larger for longer, delaeyed neutrals.
#
def filter_start(r, window):
    start = None
    for idx, p in enumerate(r.pos):
        if (p.time_ms > (conf.start_ms + min2ms(window))):
            break
        if (p.line_id == conf.start_line_id) and \
                (p.forward == conf.start_forward):
            start = idx
    if start is None:
        return False
    del(r.pos[0:start])
    if (args.debug):
        print 'START', r.id, r.pos[0]
    #
    # Look back 30 seconds from start time, show why this rider was DQ'd.
    #
    if (r.pos[0].time_ms < (conf.start_ms - min2ms(0.5))):
        t = msec_time(conf.start_ms - r.pos[0].time_ms)
        r.set_dq(r.pos[0].time_ms, 'Early: -%2d:%02d' % (t.min, t.sec))
    return True


#
# Starting with the second position (start has already been validated)
#  check position records against course.
#  (currently just checks alternate finish line crossings for w8topia)
#
# This should trim and flag any rides which do not match the course.
#  distance and correct finish is validated later.
#
def trim_course(r):
    forward = conf.start_forward
    for idx, p in enumerate(r.pos[1:]):
        if (p.line_id != conf.finish_line_id):
            continue
        if conf.alternate is not None:
            forward = not forward
        if (p.forward != forward):
            # crossed finish line in wrong direction
            # trim the ride.  idx starts at 0, so add one.
            if (args.debug):
                print 'WRONG', r.id, '%s' % ('fwd' if forward else 'rev'), p
            r.set_dq(p.time_ms, "WRONG COURSE")
            del(r.pos[idx + 1:])
            break
    return True


#
# Trims position records and sets maximum distance.
#
def trim_crash(r):
    s = r.pos[0]
    l = s
    r.distance = 0
    for idx, p in enumerate(r.pos[1:]):
        d = p.meters - s.meters

        if (p.meters < l.meters):
            r.set_dq(p.time_ms, "----CRASHED---")
            r.distance = max(r.distance, p.meters)
            del(r.pos[idx + 1:])
            break

        r.distance = d                  # distance so far

        if (p.mwh < l.mwh):
            r.set_dq(p.time_ms, "----CRASHED---")
            del(r.pos[idx + 1:])
            break
        if (p.duration < l.duration):
            r.set_dq(p.time_ms, "----CRASHED---")
            del(r.pos[idx + 1:])
            break
    return True


#
# Better off just to have a set of results for each class.
# then results just pick the "ASSIGNED" class, or the best weighted one.
#
class grp_finish():
    def __init__(self, r, grp):
        self.grp        = grp
        self.pos        = None
        self.dq_time    = None
        self.dq_reason  = None

        r.finish.append(self)

        s = r.pos[0]
        for idx, p in enumerate(r.pos[1:]):
            if (p.meters - s.meters) >= grp.distance:
                self.pos = p
                break

        # if no end position, this is a DNF. (or crash)
        if self.pos is None:
            return

        if (r.pos[0].time_ms > grp.start_ms):
            return

        d = (grp.start_ms - r.pos[0].time_ms) / 1000

        # allow 5 second jump.
        if (d < 8):
            return

        # compute penalty if needed?
        t = msec_time(d * 1000)
        self.dq_time = grp.start_ms
        self.dq_reason = 'Early:  %2d:%02d' % (t.min, t.sec)


    #
    # Start with the time delta to this group start.
    # Straight DNF == 0
    # DQ without completing the required distance: -3
    # DQ after completing ride: 2
    # Successful ride: 10
    #
    def weight(self, r):
        weight = -abs(self.grp.start_ms - r.pos[0].time_ms) / 1000
        if self.dq_reason is not None:
            weight = weight - 3
        if self.pos is not None:
            weight = weight + 10
        return weight


#
# Select the appropriate finish group.
# Finish groups determine start time / dq / dnf.
#
def select_finish(r):
    finish = max(r.finish, key = lambda f: f.weight(r))
    if (r.cat == 'X') and args.no_cat:
        r.cat = finish.grp.name         # group all finishes together.
    else:
        #
        # match any groups which have the cat letter in their name.
        # if no match (group 'all', or cat 'W', select the best one.
        #
        F = [ f for f in r.finish if r.cat in f.grp.name ]
        finish = max(F, key = lambda f: f.weight(r)) if F else finish
    if finish.dq_reason and (r.dq_reason is None):
        r.set_dq(finish.dq_time, finish.dq_reason)
    r.grp = finish.grp
    r.end = finish.pos
    if r.end is not None:
        r.end_time = r.end.time_ms


#
# XXX notused
#
def cat_details(r, cat):
    s = r.pos[0]
    for idx, p in enumerate(r.pos[1:]):
        d = p.meters - s.meters
        if (d < cat.distance):
            continue
        r.end_idx = idx + 1
        r.end_time = p.time_ms
        print r.id, d, "FINISHED", cat.name, time.ctime(p.time_ms/1000)
        return True

#
# DNF = valid start, but distance < full distance.
#  DQ = valid distance, but something went wrong.
#
def filter_dq(r):
    if ((r.dq_time is not None) and \
            ((r.end_time is not None) and (r.dq_time < r.end_time))):
        return True
    return False


def filter_dnf(r):
    return r.end is None


def strT_to_sec(val):
    m = re.match('(\d+):(\d+)', val)
    if m:
        return (int(m.group(1)) * 60) + int(m.group(2))
    m = re.match('(\d+)', val)
    if m:
        return int(m.group(1))
    sys.exit('Could not parse time %s' % val)


#
# XXX
# fix -- this is really a start group, not a single cat.  
# cat (ABCDW) are determined by rider info.
#
class config_cat_group():
    def __init__(self, name, val):
        self.name       = name
        self.lead       = None
        self.starter    = None
        self.delay_ms   = None

        m = re.match('{\s+(.*)\s+}\s+(\w+)\s+(\w+)', val)
        if not m:
            sys.exit('Unable to parse category info "%s"' % val)
        i = iter(m.group(1).split())
        d = dict(zip(i, i))
        (km, dist) = (m.group(2), m.group(3))

        dist = long(dist)
        if km == 'mi':
            dist = dist * 1.60934
        elif km != 'km':
            sys.exit('Unknown distance specifier "%s" for cat %s' %
                    (km, self.name))
        self.distance = dist * 1000

        if 'id' in d:
            self.lead = int(d['id'])
        if 'delay' in d:
            self.delay_ms = strT_to_sec(d['delay']) * 1000


class config():
    def __init__(self, fname):
        self.id                 = None
        self.name               = None
        self.start_ms           = None
        self.finish_ms          = None
        self.start_forward      = None
        self.start_line         = None
        self.finish_forward     = None
        self.finish_line        = None
        self.pace_kmh           = None
        self.cutoff_ms          = None
        self.alternate          = None
        self.grp                = []        # category groups

        self.init_kw(config.__dict__)
        self.parse(fname)

    def init_kw(self, dict):
        self.kw = { f._kw : f for f in dict.values() if hasattr(f, '_kw') }

    def keyword(key):
        def wrapper(f):
            f._kw = key
            return f
        return wrapper

    @keyword('ID')
    def kw_id(self, val):
        self.id = val

    @keyword('NAME')
    def kw_name(self, val):
        self.name = val

    @keyword('ALTERNATE')
    def kw_alternate(self, val):
        self.alternate = True

    @keyword('START')
    def kw_start(self, val):
        (dir, val) = val.split(None, 1)
        self.start_forward = True if dir == 'fwd' else False
        (self.start_line_name, self.start_line_id) = get_line(val)

    @keyword('FINISH')
    def kw_finish(self, val):
        (dir, val) = val.split(None, 1)
        self.finish_forward = True if dir == 'fwd' else False
        (self.finish_line_name, self.finish_line_id) = get_line(val)

    @keyword('BEGIN')
    def kw_begin(self, val):
        i = iter(val.split())
        d = dict(zip(i, i))
        tm = time.localtime()
        if not 'time' in d:
            sys.exit('Must specify start time')
        t_sec = time.strptime(d['time'], '%H:%M')
        if 'date' in d:
            t_day = time.strptime(d['date'], '%Y-%m-%d')
        else:
            t_day = tm
        off = 0
        dst = tm.tm_isdst
        if 'zone' in d:
            if d['zone'] == 'zulu':
                off = int(time.time() - time.mktime(time.gmtime())) / 60
                off = off * 60
                dst = 0
            elif d['zone'] != 'local':
                m = re.match('([+-]?)(\d{2}):?(\d{2})?', d['zone'])
                if not m:
                    sys.exit('Invalid timezone syntax')
                off = int(m.group(2)) * 3600 + int(m.group(3) or 0) * 60
                off = off * -1 if m.group(1) == '-' else off
        t = time.struct_time((t_day.tm_year, t_day.tm_mon, t_day.tm_mday,
                t_sec.tm_hour, t_sec.tm_min, t_sec.tm_sec,
                0, 0, dst))
        self.start_ms = (int(time.mktime(t)) - off) * 1000
        self.date = time.strftime('%Y-%m-%d',
                time.localtime(self.start_ms / 1000))

    @keyword('CUTOFF')
    def kw_cutoff(self, val):
        i = iter(val.split())
        d = dict(zip(i, i))
        if 'pace' in d:
            self.pace_kmh = long(d['pace'])
        if 'time' in d:
            self.cutoff_ms = strT_to_sec(d['time']) * 60 * 1000

    @keyword('CAT')
    def kw_cat(self, val):
        (name, val) = val.split(None, 1)
        grp = config_cat_group(name, val)
        self.grp.append(grp)

    def parse(self, fname):
        f = open(fname, "r");
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            (key, val) = line.split(None, 1)
            if key not in self.kw:
                continue
            self.kw[key](self, val)
        #
        # Parsing of all keywords complete.
        #   Calculate interdependent variables.
        #
        if self.cutoff_ms:
            self.finish_ms = self.start_ms + self.cutoff_ms
        elif self.pace_kmh:
            m = max(self.grp, key = lambda c : c.distance)
            self.finish_ms = self.start_ms + \
                    ((m.distance * 36) / (self.pace_kmh * 10)) * 1000
        else:
            self.finish_ms = self.start_ms + ((2 * 3600) * 1000)


global args
global conf
global dbh

def main(argv):
    global args
    global conf
    global dbh

    parser = argparse.ArgumentParser(description = 'Race Result Generator')
    parser.add_argument('-j', '--json', action='store_true',
            help='JSON output')
    parser.add_argument('-s', '--split', action='store_true',
            help='Generate split results')
    parser.add_argument('-I', '--idlist', action='store_true',
            help='List of IDs that need names')
    parser.add_argument('-d', '--debug', action='store_true',
            help='Debug things')
    parser.add_argument('-i', '--ident', action='store_true',
            help='Show Zwift identifiers')
    parser.add_argument('-u', '--update_cat', action='store_true',
            help='Update rider database with their estimated ride category')
    parser.add_argument('-r', '--result_file', action='store_true',
            help='Write results into correctly named file')
    parser.add_argument('-n', '--no_cat', action='store_true',
            help='Do not perform automatic category assignemnts from names')
    parser.add_argument('config_file', help='Configuration file for race.')
    args = parser.parse_args()

    #
    # config needs to read the chalkline id's from the database.
    #  XXX fix this so alternate database may be specified.
    #
    dbh = sqlite3.connect('race_database.sql3')
    conf = config(args.config_file)

    if (args.debug):
        print "START", 'fwd' if conf.start_forward else 'rev', \
                conf.start_line_id, conf.start_line_name
        print "FINISH", 'fwd' if conf.finish_forward else 'rev', \
                conf.finish_line_id, conf.finish_line_name

#    c = dbh.cursor()
#    c.execute('select max(time_ms) from event where event = ?', ('STARTUP',));
#    s = c.fetchone();

    if (args.debug):
        print('time: %s .. %s' %
                (time.ctime(conf.start_ms / 1000),
                time.ctime(conf.finish_ms / 1000)))
        print('time: [%d .. %d]' % (conf.start_ms, conf.finish_ms))

    #
    # Look back 2 minutes just to get riders who cross over the start line
    # really early.
    #
    R = get_riders(conf.start_ms - min2ms(2.0), conf.finish_ms)
    if (args.debug):
        print 'Selected %d riders' % len(R)

    START_WINDOW = 10.0         # from offical race start time.

    #
    # Cut rider list down to only those who crossed the start line
    # in the correct direction from the time the race started.
    #
    F = R.values()
    F = [ r for r in F if filter_start(r, START_WINDOW) ]

    # pull names from the database.
    [ rider_info(r) for r in F ]

    #
    # dump list of riders needing their names fetched.
    # this is fed into an external tool, which pulls the records from
    # Zwift and writes them into the database.
    #
    if (args.idlist):
#        L = [ r.id for r in F if r.fname == 'Rider' ]
        L = [ r.id for r in F ]
        print '\n'.join(map(str, L))
        return

    #
    # Trim position records.
    #
    [ trim_course(r) for r in F ]
    [ trim_crash(r) for r in F ]

    #
    # Create cat result records.  Riders have records for every cat group.
    #   If the rider's cat is known, the correct record is used.
    #   When autotecting cat, the highest weighted finish record is used.
    #
    for grp in conf.grp:
        if (grp.lead is not None) and (grp.lead in R):
            grp.starter = R[grp.lead]
            grp.start_ms = grp.starter.pos[0].time_ms
        elif grp.delay_ms is not None:
            grp.start_ms = conf.start_ms + grp.delay_ms
        else:
            grp.start_ms = conf.start_ms

        [ grp_finish(r, grp) for r in F ]

    #
    # Set rider cat here, in order to select the correct finish record.
    #  Cat 'X' == unknown, which autoselects the best record.
    #

    #
    # Now, select the matching finish record (or best weighted one)
    #
    [ select_finish(r) for r in F ]

    if (args.result_file):
        fname = conf.id + '.' + conf.date
        fname += '.json' if args.json else '.txt'
        print "Writing results to %s" % fname
        sys.stdout = open(fname, 'w')

    if (args.json):
        dump_json(conf.id, conf.start_ms, F)
    else:
        results(conf.id, F)

    dbh.close()

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
    except SystemExit, se:
        print "ERROR:", se
