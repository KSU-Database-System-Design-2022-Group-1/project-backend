#Login
#Registration
#
import main
from flask import Flask, render_template, request, redirect, url_for, session

from mariadb import mariadb, Cursor, Connection
from flask import Flask, request

import actions

app = Flask(__name__)
app.route("/login", methods=['POST']
def login(cur, username, password):
         cur.execute('SELECT * FROM accounts WHERE username = ? AND password = ?', (email, password,))
         if len(cur.fetchall()) == 0
                return False
            return True


# Check if there is 
def registration
    
