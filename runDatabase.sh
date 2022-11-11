#! /bin/bash
set -euo pipefail

# Colorful message writer thing.
function sayThing {
	printf "\033[32m%s\033[0m\n" "$1"
}

# Check if this environment has a command.
function hasCommand {
	command -v "$1" >/dev/null 2>&1
}

# Check if a process is running.
function isRunning {
	if hasCommand pgrep; then
		pgrep -f "$1" >/dev/null 2>&1
	else
		ps | grep "$1" >/dev/null 2>&1
	fi
}

# Only run if in root of Git repository.
if [ ! -d .git ]; then
	sayThing "\
Hey! Just covering my bases, as this script can get a little disruptive.
Run this script in our project's root."
	exit 1
fi

if [ -s .mariadb_path ]; then # Is there a path override file?
	# Read only the first line and trim its newline and trailing slash if present.
	MARIADB_PATH=$(head -n 1 .mariadb_path | sed 's/\n$//; s/\/$//')
	
	# Oh my god why did I go down this rabbit hole
	if hasCommand cygpath; then
		case $MARIADB_PATH in '~'*)
			MARIADB_PATH="$HOME"$(echo "$MARIADB_PATH" | sed 's/~//') ;;
		esac
		MARIADB_PATH=$(cygpath -a "$MARIADB_PATH")
		sayThing "Read MariaDB path from .mariadb_path file, and converted it."
	else
		sayThing "Read MariaDB path from .mariadb_path file."
	fi
	# Shell creators really do make up syntax every day
	
	# Print path after possibly reformatting.
	sayThing "  $MARIADB_PATH"
elif hasCommand mysql; then  # Is it in the system's PATH variable?
	MARIADB_PATH=$(command -v mysql | sed 's/\/mysql$//')
	echo "$MARIADB_PATH" > .mariadb_path
	sayThing "\
Automatically found this possible MySQL/MariaDB installation:
  $MARIADB_PATH
Is that cool? If so, run this script again.
If not, edit the .mariadb_path file that has been automatically created,
 replacing the path with the correct MySQL/MariaDB install path. Thanks!
If you're on Windows, it should point to the /bin subfolder specifically."
	exit 1
	# Not bothering with any yes/no prompts.
else # Otherwise, make the path override file.
	sayThing "\
Hey! Sorry, I couldn't find your MySQL/MariaDB installation automatically.
I've created a .mariadb_path file to put the path to your MariaDB install in.
If you're on Windows, it should point to the /bin subfolder specifically."
	touch .mariadb_path
	exit 1
fi

# I guess you can customize the port.
# I don't know anything about this. Thanks.
MARIADB_PORT=3306

# Works on both Windows and Linux, probably!!!
THE_DATABASE_PATH=$(pwd -W 2>/dev/null || pwd)
# Technical Detailz:
	# I call pwd with the -W flag to return Windows-style paths from Git Bash.
	# If this fails because you're on A Real Linux Install, it falls back to
	# regular old pwd -- and I have to redirect the error message from the
	# first command into the void, so it doesn't clog up the fallback command.
	# It's 1 AM and I'm convinced I'm a genius. (I'm not.)
#

if [ ! -f ./database/data/my.ini ]; then
	sayThing "Database doesn't seem to exist! Creating folder and config file..."
	
	# Make the place for the database.
	mkdir -p ./database/data/
	
	# Make the config file.
	cat <<-THE_CONFIG_FILE > ./my.ini
		[client]
		port=$MARIADB_PORT
		
		[server]
		port=$MARIADB_PORT
		
		[mysqld]
		
		basedir=$THE_DATABASE_PATH/database/
		datadir=$THE_DATABASE_PATH/database/data
		
		character_set_server=utf8mb4
		collation_server=utf8mb4_general_ci
		
		# skip_innodb
		innodb_buffer_pool_size=32M
		innodb_log_file_size=24M
		innodb_log_buffer_size=8M
		# default_storage_engine=Aria
	THE_CONFIG_FILE
	# (I made the redo log and etc. smaller, because those are
	# massive! And I figure we're not doing anything fancy just yet. Maybe
	# in the future we can figure out if this is a good thing to remove.)
	# (Either way, this makes the local database 0.1GB instead of 1GB.)
	
	# Make the database, without registering a Windows service.
	sayThing "Installing database to folders inside this project..."
	"$MARIADB_PATH"/mysql_install_db -D -c my.ini
	# (It says "starting mysqld as process PID" but that's just temporary,
	# probably for initializing. We'll still need to launch a proper daemon.)
	
	# MariaDB copies the config file we gave it,
	# so we can safely delete the one we generated.
	rm ./my.ini
	
	sayThing "Done setting this up! You shouldn't see this again, unless you delete the /database/ folder."
fi

# Run the definition script if kstores isn't present 
if [ ! -d ./database/data/kstores ]; then
	sayThing "KStores database doesn't seem to exist! Creating from definition script..."
	
	if isRunning "/mysqld"; then
		sayThing "An unrelated MySQL server appears to be running.
	Check 'ps' (Linux) or Windows Task Manager's 'Details' tab."
		exit 1
	fi
	
	# Launch the server in the background,
	"$MARIADB_PATH"/mysqld --basedir=./database/ --datadir=./database/data/ >/dev/null &
	
	# Connect to it, and then run the definition script on it.
	"$MARIADB_PATH"/mysql -u root -h localhost -P $MARIADB_PORT --show-warnings < ddl.sql
	THE_SETUP_RESULT=$?
	
	# Once the definition script is done,
	kill -s SIGINT $! # kill the server process.
	wait # and wait for it to finish up, so it releases its file locks.
	
	# (i have to kill with SIGINT, otherwise server won't terminate gracefully
	#  and it might not even execute what we asked in the first place.)
	# (is this a race condition? if so, it won't be a problem thanks to the
	#  whole atomic transaction thing in place in the definition script.)
	
	if [ $THE_SETUP_RESULT -eq 0 ]; then
		sayThing "Done setting up the 'kstores' database!"
	else
		sayThing "Oh, something bad happened while running the definition script."
		exit 1
	fi
	# Seeing the server start up 3 times in a row for 3 different steps of initialization
	# feels slightly bad. But if it works and it only does it once, that's probably fine.
	
	if [ ! -d ./database/data/kstores ]; then
		sayThing "Hmm. MySQL exited fine, but I'm not seeing the 'kstores' database anywhere."
		exit 1
	fi
fi

if [ "$#" -gt 0 ] && [ "$1" = "monitor" ]; then
	# Only attempt to run monitor if MySQL is running locally.
	if isRunning "/mysqld"; then
		# Launch the monitor.
		sayThing "Connecting to MySQL Server at port $MARIADB_PORT. To exit, type 'quit'."
		"$MARIADB_PATH"/mysql -u root -h localhost -P $MARIADB_PORT -D kstores --show-warnings
	else
		sayThing "No MySQL server is running."
		exit 1
	fi
else
	# Launch the database server, without registering a Windows service.
	sayThing "Running MySQL Server at port $MARIADB_PORT! Press Ctrl+C in terminal to stop."
	"$MARIADB_PATH"/mysqld --basedir=./database/ --datadir=./database/data/ --console
	
	# Just staying vigilant.
	if isRunning "/mysqld"; then
		sayThing "Warning: somewhere on your computer, MySQL is still running.
	Check 'ps' (Linux) or Windows Task Manager's 'Details' tab."
	fi
fi
