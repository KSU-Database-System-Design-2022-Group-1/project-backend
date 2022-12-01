#Login
#Registration

import main
from flask import Flask, render_template, request, redirect, url_for, session

from mariadb import mariadb, Cursor, Connection
from flask import Flask, request

import actions

# ACTION.PY

def login(cur, email, password) :
     cur.execute('SELECT * FROM accounts WHERE email = ? AND password = ?', (email, password,))
     if len(cur.fetchall()) == 0:
        return False
     return True


# MAIN.PY

app = Flask(__name__)
@app.route("/login", methods=['POST'])
def login() :
    res = actions.login(request.form['email'], request.form['password'])
    return {"success": res}


# ACTION.PY
def create_address(cur, street_number, street_name, street_apt, city, state, zip) :
    cur.execute('SELECT * FROM address WHERE street_number = ?, street_name = ?, street_apt = ?, city = ?, state = ?, zip = ?', (street_number,
    street_name, street_apt, city, state, zip,))
    if len(cur.fetchall()) != 0:
        return -1
    
    cur.execute('INSERT INTO address VALUES (?,?,?,?,?,?)', (street_number, street_name, street_apt, city, state, zip))

    address_id = cur.lastrowid

    return address_id

# Check if there is 
def registration(cur, first_name, middle_name, last_name, shipping_id, billing_id, email, password, phone_number) :
    cur.execute('SELECT * FROM customer WHERE email = ?', (email,))
    if len(cur.fetchall()) != 0:
        return -1
    
    cur.execute('INSERT INTO customer VALUES (?,?,?,?,?,?,?,?)', (first_name, middle_name, last_name, shipping_id, billing_id, email, password, phone_number))

    account_id = cur.lastrowid

    return account_id

# MAIN.PY

app = Flask(__name__)
@app.route("/login", methods=['POST'])
def registration() :
    shipping_id = actions.create_address(cur, request.form['shipping_street_number'], request.form['shipping_street_name'], request.form['shipping_street_apt'],
    request.form['shipping_city'], request.form['shipping_state'], request.form['shipping_zip'])
    
    billing_id = actions.create_address(cur, request.form['billing_street_number'], request.form['billing_street_name'], request.form['billing_street_apt'],
    request.form['billing_city'], request.form['billing_state'], request.form['billing_zip'])

    customer = actions.registration(cur, request.form['first_name'], request.form['middle_name'], request.form['last_name'], shipping_id, billing_id,
    request.form['email'], request.form['password'], request.form['phone_number'])

    if customer == -1 :
        return {"success": False}
    return {"success": True}







