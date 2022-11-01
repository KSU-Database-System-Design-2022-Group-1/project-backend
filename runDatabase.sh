set -eu

# Colorful message writer thing.
function sayThing {
	printf "\033[32m%s\033[0m\n" "$1"
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
	sayThing "\
Read MariaDB path from .mariadb_path file.
$MARIADB_PATH"
elif command -v mariadb >/dev/null 2>&1; then  # Is it in the system's PATH variable?
	MARIADB_PATH=$(command -v mariadb | sed 's/\/mariadb$//')
	echo "$MARIADB_PATH" > .mariadb_path
	sayThing "\
Automatically found this possible MariaDB installation:
$MARIADB_PATH
Is that cool? If so, run this script again.
If not, edit the .mariadb_path file that has been automatically created,
 replacing the path with the correct MariaDB install path. Thanks!
If you're on Windows, it should point to the /bin subfolder specifically."
	exit 1
	# Not bothering with any yes/no prompts.
else # Otherwise, make the path override file.
	sayThing "\
Hey! Sorry, I couldn't find your MariaDB installation automatically.
I've created a .mariadb_path that you should put the path to your MariaDB install in.
If you're on Windows, it should point to the /bin subfolder specifically."
	touch .mariadb_path
	exit 1
fi

# Oh my god why did I go down this rabbit hole
if command -v cygpath >/dev/null 2>&1; then
	case $MARIADB_PATH in '~'*)
		MARIADB_PATH="$HOME"$(echo "$MARIADB_PATH" | sed 's/~//') ;;
	esac
	MARIADB_PATH=$(cygpath -a "$MARIADB_PATH")
	
	sayThing "\
Reformatted path.
$MARIADB_PATH"
fi
# Shell creators really do make up syntax every day

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
		[client-server]
		
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
	# (I made the redo log and  smaller, because those are
	# massive! And I figure we're not doing anything fancy just yet. Maybe
	# in the future we can figure out if this is a good thing to remove.)
	# (Either way, this makes the local database 0.1GB instead of 1GB.)
	
	# Make the database, without registering a Windows service.
	sayThing "Installing database to folders inside this project..."
	$MARIADB_PATH/mysql_install_db -D -c my.ini
	# (It says "starting mysqld as process PID" but that's just temporary,
	# probably for initializing. We'll still need to launch a proper daemon.)
	
	# MariaDB copies the config file we gave it,
	# so we can safely delete the one we generated.
	rm ./my.ini
	
	sayThing "Done setting this up! You shouldn't see this again, unless you delete the /database/ folder."
fi

# Launch the database server, without registering a Windows service.
sayThing "Running MySQL Server at port $MARIADB_PORT! Press Ctrl+C in terminal to stop."
$MARIADB_PATH/mysqld --basedir=./database/ --datadir=./database/data/ --console

# # Launch the monitor.
# sayThing "Connecting to MySQL Server at port $MARIADB_PORT. To exit, type 'quit'."
# $MARIADB_PATH/bin/mysql -u root -h localhost -P $MARIADB_PORT