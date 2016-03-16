# zlogger
Zwift Data Logger and Results Generator

## Data Collection

### zlogger binary
Obtain the zlogger binary from Jonathan Lemon.
This is needed to generate the data.  This is a terminal application,
The current binary is located in a [Dropbox][dropbox] folder - `zlogger` is
the Mac version, while `zlogger.zip` is the Windows version.

### Chalklines
The chalk.txt file contains a collection of chalklines to monitor.
The current code is arbitrarily limited to watching 8 chalklines, and
selects the correct set of chalklines for the world being monitored.

Comment/uncomment lines in the chalk.txt file to taste.

### Running
As run `zlogger -c chalk.txt -w WORLD` in order to start the logger.
`WORLD` should start with 'r' or 'w', for Richmond or Watopia.

The monitored interface will default to the first interface if omitted.
Alternate interfaces may be selected with `-i interface`

Three files will be created:

 * `debug.log` will contain debugging information.
 * `chat.log` will contain the message log.
 * `race_database.sql3` contains position information.

Note that the database schema is subject to change without notice.


#### Mac version
Obtain zlogger from the link above, place in a folder on your desktop.
Change permissions to runnable: `chmod 755 zlogger`
Run zlogger as `root`.  The first interface will likely default to en0.

#### Windows version
win10pcap is required -- obtain and install from the web.
The pcap drivers are compatible with windows 7 and windows 10.

On windows, interface names are specified via their UUIDs, which look
like "{...}" - the curly brackets are part of the interface name and must
be included.
A list of valid interface names is printed in the debug.log file on startup.


## Report Generation

### get_riders.py

This uses your Zwift login in order to pull rider information from Zwift.

### mkresults.py

This is the main result generation script.  It consumes a configuration file
describing the race, extracts the set of position records from the database,
and creates the race results.
 Sample usage: `./mkresults.py -ni config/KISS-richmond.conf`

The result script has many options and settings.  Interested readers should
consult the source for definitive listings.

### mkresults Configuration file

Races are described by a configuration file.  See `config/ZTR-w8topia.conf`
for a commented description.

#### Configuration Options

##### ID _name_
Identifier used in report generation.

##### NAME _string_
Name of the race, used in report generation.

##### REQUIRED_TAG _tag_
Only riders which have _tag_ in their name will be included in the results.

##### START _dir_ { _chalkline_ }
The start of the race is designated by crossing _chalkline_ in the specified
_dir_.  _chalkline_ is a name from the `chalk.txt` file.

##### FINISH _dir_ { _chalkline_ }
The end of the race is designated by crossing _chalkline_ in the specified
_dir_.  _chalkline_ is a name from the `chalk.txt` file.

##### BEGIN date _date_ time _time_ zone _zone_
The race starts at the specified time.  _date_, _time_, _zone_ are specified
in RFC 3339 style format, _zone_ may be `local` for local timezone, `zulu`
for UTC time, or an RFC-compliant timezone offset such as `-800`.

##### CUTOFF time _time_  or   pace _pace_
The race ends after the specified time, or after (_distance_ * _pace_) time.

##### CAT _cat_ { _start_ } [km | mi] _distance_
Specifies the minimum _distance_ needed in order to complete the race.
Multiple _cat_ entries are allowed.  For example:
```
CAT AB { delay 0 } km 56
CAT CD { delay 2:00 } km 27
```
Will set up 2 categories for different distances, with the second group
starting 2 minues after the first one.

##### GRACE min _min_
Allows riders to start _min_ before the official start without being DQd.

##### LOOKBACK min _min_
Looks back _min_ from start time, including those riders in the DQ/DNF results.

##### WINDOW min _min_  or  time _time_
Only riders crossing the start line between (start + window) are considered
as participating in the race.  Also known as the starting cutoff time.

##### CORRAL _dir_ { _chalkline_ }
Riders must be within the corral at the start (or move through the corral
slowly during the start).  The intent is to flag and DQ riders which are
performing flying starts.

##### POINTS
##### POINTS_FINAL
Point scoring system.



# NOTE

All of this should be considered Early-Access Beta software, and is subject to
change without notice.
[dropbox]: https://www.dropbox.com/sh/uboejm07pawjcnl/AABvHG9v1Vi24XOmtEwSqJ3Za?dl=0 "Dropbox"
