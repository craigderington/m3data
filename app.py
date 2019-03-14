from flask import Flask, Response, abort, request, jsonify, g, url_for, render_template, flash
from flask_mail import Mail, Message
from flask_sslify import SSLify
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPTokenAuth
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy import exc, and_, desc
from celery import Celery
from datetime import datetime
from db import db_session
from models import User, IPData, APILog
from twilio.rest import Client
import config
import json
import random
import ipaddress
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import hashlib
import hmac
import time


# debug
debug = config.DEBUG

# app config
app = Flask(__name__)
# sslify = SSLify(app)
app.config['SECRET_KEY'] = config.SECRET_KEY
token_serializer = Serializer(app.config['SECRET_KEY'], expires_in=3600)

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
auth = HTTPTokenAuth('Bearer')

# mailgun_api_key
mailgun_api_key = config.MAILGUN_API_KEY


@auth.verify_token
def verify_token(token):
    g.user = None
    try:
        data = token_serializer.loads(token)
    except Exception:
        return False
    if 'username' in data:
        g.user = data['username']
        g.user_id = data['user_id']
        return True
    return False


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


@celery.task(serializer='pickle')
def multiply():
    """
    Multiply two numbers and return the result
    :param x:
    :param y:
    :return:
    """
    x, y = None, None

    try:
        x = random.randint(12000, 75000)
        y = random.randint(100000, 1000000)
    except ValueError as err:
        print('Value Error: {}'.format(str(err)))

    return x * y


'''
******************************
********* Web Pages **********
******************************
'''


@app.route('/', methods=['GET'])
def home():
    """
    Marketing Data Intelligence Homepage
    :return: template
    """

    return render_template(
        'home.html',
        today=get_date()
    )


@app.route('/markets', methods=['GET'])
def markets():
    """
    MDI Markets
    :return: template
    """

    return render_template(
        'markets.html',
        today=get_date()
    )


@app.route('/appending', methods=['GET'])
def appending():
    """
    Data Appending page
    :return: template
    """

    return render_template(
        'appending.html',
        today=get_date()
    )


@app.route('/sms', methods=['GET'])
def sms():
    """
    SMS page
    :return: template
    """

    return render_template(
        'sms.html',
        today=get_date()
    )


@app.route('/pricing', methods=['GET'])
def pricing():
    """
    M3 Pricing page
    :return: template
    """

    return render_template(
        'pricing.html',
        today=get_date()
    )


@app.route('/api/docs', methods=['GET'])
def api_docs():
    """
    Swagger UI API Docs
    :return: swagger UI
    """

    return render_template(
        'api_docs.html',
        today=get_date()
    )


@app.route('/contact', methods=['GET'])
def contact():
    """
    M3 Contact Page
    :return: template
    """

    return render_template(
        'contact.html',
        today=get_date()
    )


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Template for Login page
    :return:
    """
    return render_template(
        'register.html',
        today=get_date()
    )


@app.route('/status', methods=['GET'])
def status():
    """
    Template for Status page
    :return:
    """
    return render_template(
        'status.html',
        today=get_date()
    )


'''
******************************
********* API ****************
******************************
'''


@app.route('/api', methods=['GET'])
@app.route('/api/v1.0', methods=['GET'])
@app.route('/api/v1.0/index', methods=['GET'])
@auth.login_required
def index():
    """
    The default API view.  List routes:
    :return: dict
    """
    api_routes = dict()
    api_routes['login'] = '/api/v1.0/auth/login'
    api_routes['ipaddr'] = '/api/v1.0/ipaddr/<string:ip_addr>'
    api_routes['sms'] = '/api/v1.0/sms/<string:sms_number>'
    api_routes['addr'] = '/api/v1.0/addr/<string:addr>'
    api_routes['latlng'] = '/api/v1.0/lat/<string:lat>/lng/<string:lng>'
    api_routes['name'] = '/api/v1.0/name/first/<string:f_name>/last/<string:l_name>'
    api_routes['zipcode'] = '/api/v1.0/zipcode/<string:zip_code>'
    api_routes['city'] = '/api/v1.0/city/<string:city_name>/limit/<int:limit>'

    # return the response
    return render_template(
        'index.html',
        api_routes=api_routes,
        today=get_date(),
        title="M3 Data Appending API"
    )


@app.route('/api/v1.0/ipaddr/<string:ip_addr>', methods=['GET'])
@auth.login_required
def get_ip_data(ip_addr):
    """
    Append data to IP Address
    Return the Person obj by IP Address
    :return: obj(Person), type(json)
    """

    if request.method == 'GET':

        try:
            ip_address = ipaddress.IPv4Address(ip_addr)

            try:
                data = db_session.query(IPData).filter(IPData.ip == ip_address).first()

                if data:

                    # write the access log
                    try:
                        write_log(g.user_id, 'ipdata')
                    except Exception as e:
                        print('Error writing log...')

                    # return a successful response
                    return jsonify({
                        'created_date': data.created_date,
                        'last_seen': data.last_seen,
                        'ip': data.ip,
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


@app.route('/api/v1.0/sms/<string:phone_number>', methods=['GET'])
@auth.login_required
def get_sms_data(phone_number):
    """
    Append data to Mobile Number
    Return the Person obj by cell phone number
    :param: string: phone_number
    :return: obj(Person), type(json)
    """
    geo, carrier, time_zone, city_geocode = range(4)

    try:
        phone = phonenumbers.parse('+1' + phone_number, None)

        if phone:

            # check the phone number geocoder
            geo = geocode_phone_number(str(phone.national_number))

            if geo:
                carrier = geo['carrier']
                time_zone = geo['timezone']
                city_geocode = geo['geocode']

            try:
                data = db_session.query(IPData).filter(
                    IPData.cell_phone == phone.national_number
                ).first()

                if data:

                    # write the access log
                    try:
                        write_log(g.user_id, 'sms')
                    except Exception as e:
                        print('Error writing log...')

                    # return a successful response
                    return jsonify({
                        'created_date': data.created_date,
                        'sms_match': '+1' + str(data.cell_phone),
                        'verified': True,
                        'last_seen': data.last_seen,
                        'ip': data.ip,
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
                        'phone_network': {
                            'number': '+1' + str(phone.national_number),
                            'carrier': carrier,
                            'timezone': time_zone,
                            'city': city_geocode
                        }
                    }), 200

                # phone number not found
                else:
                    resp = {"Number Not Found": '+1' + str(phone.national_number), 'GeoData': geo}
                    data = json.dumps(resp)
                    return Response(data, status=200, mimetype='application/json')

            except exc.SQLAlchemyError as db_err:
                resp = {"Database Error": str(db_err)}
                data = json.dumps(resp)
                return Response(data, status=500, mimetype='application/json')

        # phone number parser returned False
        else:
            resp = {"Unidentifiable Phone Number:": str(phone_number)}
            data = json.dumps(resp)
            return Response(data, status=406, mimetype='application/json')

    except phonenumbers.NumberParseException as npe:
        resp = {"Invalid Phone Number Format": str(npe)}
        data = json.dumps(resp)
        return Response(data, status=400, mimetype='application/json')


@app.route('/api/v1.0/lat/<string:lat>/lng/<string:lng>', methods=['GET'])
@auth.login_required
def get_location_data(lat, lng):
    """
    Append data to latitude and longitude
    Return the Person obj by latitude and longitude
    :param: string: lat (float), lng (float)
    :return: obj(Person), type(json)
    """

    persons = []

    try:
        lat = float(lat)
        lng = float(lng)

        try:
            location = db_session.query(IPData).filter(
                IPData.latitude == lat,
                IPData.longitude == lng
            ).all()

            if location:

                for rec in location:
                    persons.append(rec)

                resp = {"Data found for location": persons}
                data = json.dumps(resp, default=convert_datetime_object)
                return Response(data, status=200, mimetype='application/json')

            else:
                resp = {"No data matching": "Lat: {} Lng: {}".format(str(lat), str(lng))}
                data = json.dumps(resp)
                return Response(data, status=200, mimetype='application/json')

        except exc.SQLAlchemyError as err:
            resp = {"Database Error": str(err)}
            data = json.dump(resp)
            return Response(data, status=500, mimetype='application/json')

    except TypeError as type_err:
        resp = {"Error": str(type_err)}
        data = json.dumps(resp)
        return Response(data, status=400, mimetype='application/json')


@app.route('/api/v1.0/first/<string:f_name>/last/<string:l_name>', methods=['GET'])
@auth.login_required
def get_name_data(f_name, l_name):
    """
    Append data to Person first_name and last_name
    Return the Person obj by first name and last name
    :param: string: f_name (string), l_name (string>
    :return: obj(Person), type(json)
    """

    try:
        first = str(f_name)
        last = str(l_name)

        try:
            data = db_session.query(IPData).filter(
                IPData.first_name == first,
                IPData.last_name == last
            ).first()

            if data:
                # return a successful response
                return jsonify({
                    'created_date': data.created_date,
                    'last_seen': data.last_seen,
                    'ip': data.ip,
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
                    }
                }), 200

            else:
                resp = {"No data found": str(f_name) + ' ' + str(l_name)}
                data = json.dumps(resp)
                return Response(data, status=200, mimetype='application/json')

        except exc.SQLAlchemyError as db_err:
            resp = {"Database Error": str(db_err)}
            data = json.dumps(resp, default=convert_datetime_object)
            return Response(data, status=500, mimetype='application/json')

    except TypeError as e:
        return Response(e, status=400, mimetype='application/json')


'''
******************************
***** Utility Functions *****
******************************
'''


@app.before_first_request
def create_user_tokens():
    # write the user tokens to the appropriate db fields
    counter = 0

    try:
        users = db_session.query(User).filter(
            User.active == 1
        ).all()

        for user in users:
            token = token_serializer.dumps({'username': user.username, 'user_id': user.id}).decode('utf-8')
            user.token = token
            user.token_last_update = datetime.now()
            db_session.commit()
            db_session.flush()
            print('*** token for {} ***: {}\n'.format(user.username, token))
            counter += 1

        print('Updated {} tokens.'.format(str(counter)))

    except exc.SQLAlchemyError as err:
        print('Database error updating tokens: {}'.format(str(err)))


def write_log(user_id, resource):
    """
    Write the resource user access log to
    the database table for analytics and reporting
    :param user_id:
    :param resource:
    :return: none
    """
    id = None
    res = None

    try:
        id = int(user_id)
        res = str(resource)

        try:
            _log = APILog(
                user_id=id,
                resource=res
            )

            db_session.add(_log)
            db_session.commit()
            db_session.flush()
            print('Log write for: {} on: {}'.format(str(id), res))

        except exc.SQLAlchemyError as db_err:
            print('Error writing access log data: {}'.format(str(db_err)))

    except TypeError as error:
        print('Invalid data type {} in write_log function.'.format(str(error)))

    return id, res


def check_phone_number(phone_number):
    """
    Parse the sms phone number using the phone numbers library and return true or false
    :param phone_number:
    :return: bool
    """
    try:
        phone = phonenumbers.parse('+1' + phone_number, None)
        if phone:
            return True
    except phonenumbers.NumberParseException:
        return False


def geocode_phone_number(phone_number):
    """
    Geocode the phone number to include in the Response
    :param phone_number:
    :return: type(json)
    """
    resp = dict()

    try:
        phone = phonenumbers.parse('+1' + phone_number, None)
        if phone:
            resp['geocode'] = geocoder.description_for_number(phone, "en")
            resp['carrier'] = carrier.name_for_number(phone, "en")
            resp['timezone'] = timezone.time_zones_for_number(phone)
    except phonenumbers.NumberParseException as npe:
        resp['error'] = '{}'.format(str(npe))

    return resp


def convert_datetime_object(o):
    if isinstance(o, datetime):
        return o.__str__()


def get_date():
    # set the current date time for each page
    today = datetime.now().strftime('%c')
    return '{}'.format(today)


def verify(api_key, token, timestamp, signature):
    hmac_digest = hmac.new(key=mailgun_api_key,
                           msg='{}{}'.format(timestamp, token).encode('utf-8'),
                           digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, hmac_digest)


'''
******************************
****** Mail Functions ********
******************************
'''


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


'''
******************************
******** Error Pages *********
******************************
'''


@app.errorhandler(404)
def page_not_found(err):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(err):
    return render_template('500.html'), 500


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))


if __name__ == '__main__':
    port = 5880

    # start the application
    app.run(
        debug=debug,
        port=port
    )
