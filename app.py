from flask import Flask, Response, abort, request, jsonify, g, url_for, render_template, flash
from flask_mail import Mail, Message
from flask_sslify import SSLify
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import exc, and_, desc
from celery import Celery
from datetime import datetime
from db import db_session
from models import User, IPData
from twilio.rest import Client
import config
import json
import random
import ipaddress
import hashlib
import hmac
import time


# debug
debug = config.DEBUG

# app config
app = Flask(__name__)
sslify = SSLify(app)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = config.MAIL_DEFAULT_SENDER

# SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
db = SQLAlchemy(app)

# disable strict slashes
app.url_map.strict_slashes = False

# Celery config
app.config['CELERY_BROKER_URL'] = config.CELERY_BROKER_URL
app.config['CELERY_RESULT_BACKEND'] = config.CELERY_RESULT_BACKEND
app.config['CELERY_ACCEPT_CONTENT'] = config.CELERY_ACCEPT_CONTENT
app.config.update(accept_content=['json', 'pickle'])

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Config mail
mail = Mail(app)

# auth
auth = HTTPBasicAuth()

# mailgun_api_key
mailgun_api_key = config.MAILGUN_API_KEY


# clear all db sessions at the end of each request
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


# tasks sections, for async functions, etc...
@celery.task(serializer='pickle')
def send_async_email(msg):
    """Background task to send an email with Flask-Mail."""
    with app.app_context():
        mail.send(msg)


# default routes
@app.route('/', methods=['GET'])
def site_root():
    """
    Server a nicely formatted M3 API webpage
    :return: template
    """

    # page vars
    today = datetime.now()
    title = 'M3 Real Time Data Appending API'

    return render_template(
        'home.html',
        today=get_date(),
        title=title
    )


@app.route('/api', methods=['GET'])
@app.route('/api/v1.0', methods=['GET'])
@app.route('/api/v1.0/index', methods=['GET'])
def index():
    """
    The default API view.  List routes:
    :return: dict
    """
    api_routes = {}
    api_routes['login'] = '/api/v1.0/auth/login'
    api_routes['ipaddr'] = '/api/v1.0/ipaddr/<string:ip_addr>'

    # return the response
    return jsonify(api_routes), 200


@app.route('/api/v1.0/ipaddr/<string:ip_addr>', methods=['GET'])
def get_ip_data(ip_addr):
    """
    Append data to IP Address
    :return: json
    """

    if request.method == 'GET':

        try:
            ip_address = ipaddress.IPv4Address(ip_addr)

            try:
                data = db_session.query(IPData).filter(IPData.ip == ip_address).first()

                if data:

                    # return a successful response
                    return jsonify({
                        'created_date': data.created_date,
                        'last_seen': data.last_seen,
                        'ip': data.ip,
                        'user-agent': data.user_agent,
                        'person': {
                            'first_name': data.first_name,
                            'last_name': data.last_name,
                            'address1': data.address1,
                            'address2': data.address2,
                            'city': data.city,
                            'state': data.state.upper(),
                            'zip_code': data.zip_code,
                            'home_phone': data.home_phone,
                            'cell_phone': data.cell_phone,
                            'birth_year': data.birth_year,
                            'credit_range': data.credit_range,
                            'income_range': data.income_range,
                            'home_owner_renter': data.home_owner_renter
                        },
                        'geo': {
                            'latitude': data.latitude,
                            'longitude': data.longitude,
                            'time_zone': data.time_zone,
                            'metro_code': data.metro_code,
                            'country_name': data.country_name,
                            'country_code': data.country_code,
                            'country_code3': data.country_code3,
                            'dma_code': data.dma_code,
                            'area_code': data.area_code,
                            'region': data.region,
                            'region_name': data.region_name
                        },
                        'auto': {
                            'car_year': data.car_year,
                            'car_make': data.car_make,
                            'car_model': data.car_model,
                            'ppm_type': data.ppm_type,
                            'ppm_indicator': data.ppm_indicator,
                            'ppm_segment': data.ppm_segment,
                            'auto_trans_date': data.auto_trans_date,
                            'auto_purchase_type': data.auto_purchase_type
                        },
                        'network': {
                            'ip_address': ip_address.exploded,
                            'ip_version': ip_address.version,
                            'compressed': ip_address.compressed,
                            'exploded': ip_address.exploded,
                            'reverse': ip_address.reverse_pointer,
                            'multicast': ip_address.is_multicast,
                            'private': ip_address.is_private,
                            'global': ip_address.is_global,
                            'loopback': ip_address.is_loopback,

                        }
                    }), 200

                # return no data found for IP
                else:
                    resp = {"Response": "No data found for IP: {}".format(str(ip_address.exploded))}
                    data = json.dumps(resp)
                    return Response(data, status=200, mimetype='application/json')

            # database exception
            except exc.SQLAlchemyError as err:
                resp = {"Database Error": str(err)}
                data = json.dumps(resp)
                return Response(data, status=500, mimetype='application/json')

        # catch ip address formatting error
        except ipaddress.AddressValueError as address_error:
            resp = {"Invalid IP Address Format": str(address_error)}
            data = json.dumps(resp)
            return Response(data, status=201, mimetype='application/json')

    # request method not allowed
    else:
        resp = {"Message": "Method Not Allowed"}
        data = json.dumps(resp)
        return Response(data, status=405, mimetype='application/json')


@app.route('/api/v1.0/auth/login', methods=['GET', 'POST'])
def login():
    """
    Template for Login page
    :return:
    """
    return render_template(
        'login.html',
        today=get_date()
    )


def send_alerts():
    """
    Send SMS alerts
    :return: twilio sid
    """
    admins = config.ADMINS
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

    for admin in admins:
        msg = client.messages.create(
            to=admin,
            from_="",
            body="")

        # return the message sid
        return msg.sid


def send_alert(cellnumber, firstname):
    """
    Send text message alert to recipient cell number
    :return: twilio sid
    """
    cleaned_number = cellnumber.replace("-", "")
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    body_text = ""
    msg = client.messages.create(
        to=cleaned_number,
        from_="",
        body="{}, {}".format(firstname, body_text))

    # return the message sid
    return msg.sid


def compare_(a, b):
    return a == b

"""
@app.errorhandler(404)
def page_not_found(err):
    return render_template('error-404.html'), 404


@app.errorhandler(500)
def internal_server_error(err):
    return render_template('error-500.html'), 500


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))
"""


def send_email(to, subject, msg_body, **kwargs):
    """
    Send Mail function
    :param to:
    :param subject:
    :param template:
    :param kwargs:
    :return: celery async task id
    """
    msg = Message(
        subject,
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[to, ]
    )
    msg.body = "M3Data API v1.0"
    msg.html = msg_body
    send_async_email.delay(msg)


def get_date():
    # set the current date time for each page
    today = datetime.now().strftime('%c')
    return '{}'.format(today)


def verify(api_key, token, timestamp, signature):
    hmac_digest = hmac.new(key=mailgun_api_key,
                           msg='{}{}'.format(timestamp, token).encode('utf-8'),
                           digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, hmac_digest)


if __name__ == '__main__':
    port = 5880

    # start the application
    app.run(
        debug=debug,
        port=port
    )
