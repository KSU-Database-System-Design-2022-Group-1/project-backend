# Backend for our Project!!!

## Download and Running Instructions

### Download and Setup

1. Ensure that you have [the latest version of **Python 3**](https://www.python.org/downloads/), as well as [**Git**](https://git-scm.com/downloads).
1. Also ensure you have... maybe **version 10.6 of MariaDB**, since it's in long-term support.
	- If you use Windows, [this link](https://mariadb.org/download/?t=mariadb&p=mariadb&r=10.6.10&os=windows&cpu=x86_64&pkg=zip) will work. It downloads the 
	- If you use Linux, I've attempted to write `./runDatabase.sh` such that it will detect whatever [MariaDB install](https://mariadb.org/download/) you have.
1. Clone this repository by using `git clone`.
	- Ensure that you're using the account that is part of our team's organization, and that you have [all that fancy SSH stuff set up](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) and that you're pushing/pulling with SSH and stuff for this project in particular.
1. Open up a terminal window, making sure you're in the repository's root directory.
1. **Install the Python dependencies** for the local server using `python -m pip install -r requirements.txt`. Once you do this once, you won't have to do it again until the `requirements.txt` file is changed.
1. **Run `python generate.py` to generate the store catalog creation script.** This will also generate the `images` folder needed for the backend to serve images.
	- The script is generated from the `items.csv` and `variants.csv` tables.
	- This will need to be run any time the CSV tables are updated.
	- If the script can't find an image, it will simply ignore it... but it will also give you a warning about the missing image including its filename!

### Running

1. In a terminal, **run the command `./runDatabase.sh`**. This will initialize and run the MySQL server for as long as the window is open.
	- It might also ask for some additional setup before running! Watch for green text and non-zero exits.
	- You might need to copy the path of the `bin/` subfolder from where you downloaded MariaDB to, and paste it into the `.mariadb_path` file.
	- If everything goes well, the script will print `Running MySQL Server at port <PORT>! Press Ctrl+C in terminal to stop.` and it will start listening for connections.
1. **In another terminal, run `python main.py`**. This will communicate with MySQL and (eventually) run a server that listens for HTTP requests.
1. That's it, that's the backend.

(Also, note that MySQL and MariaDB are basically interchangable -- MariaDB is an open-source reimplementation of MySQL.)
