# zlogger
Zwift Data Logger and Results Generator

## Data Collection

### zlogger binary
Obtain the zlogger binary (Mac OSX only for the time being) from Jonathan Lemon.
This is needed to generate the data.

### Chalklines
The chalk.txt file contains a collection of chalklines to monitor.
The current code is arbitrarily limited to watching 4 chalklines, and auto-detection
of the correct world is not in place right now.  For the time being, comment/uncomment
lines in the chalk.txt file, or create separate richmond/watopia chalk files.

### Running
As root, run `./zlogger -c chalk.txt -w WORLD -i interface` in order to start the logger.
WORLD should start with 'r' or 'w', for Richmond or Watopia.
The monitored interface will default to en1 if left off.

Two files will be created:
  `debug.log` will contain debugging information.
  `race_database.sql3` contains position information.

Note that the database schema is subject to change without notice.


## Report Generation

### Configuration file

Races are described by a configuration file.  See `config/ZTR-w8topia.conf` for a 
commented description. 

### mkresults.py

This is the main result generation script.  It consumes a configuration file describing
the race, extracts the set of position records from the database, and creates the 
race results.  Sample usage: `./mkresults.py -ni config/KISS-richmond.conf`


# NOTE

All of this should be considered Early-Access Beta software, and is subject to
change without notice.
