# zlogger
Zwift Data Logger and Results Generator

## Data Collection

### zlogger binary
Obtain the zlogger binary from Jonathan Lemon.
This is needed to generate the data.

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

Two files will be created:  

 * `debug.log` will contain debugging information.
 * `race_database.sql3` contains position information.

Note that the database schema is subject to change without notice.


#### Mac version
Run zlogger as `root`.  The first interface will likely default to en0.

#### Windows version
win10pcap is required -- obtain and install from the web.
The pcap drivers are compatible with windows 7 and windows 10.

On windows, interface names are specified via their UUIDs, which look like "{...}".
A list of valid interface names is printed in the debug.log fiile on startup.


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
