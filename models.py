from db import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Float
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Define application Bases


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(256), nullable=False)
    active = Column(Boolean, default=1)
    email = Column(String(120), unique=True, nullable=True)
    last_login = Column(DateTime)
    login_count = Column(Integer)
    fail_login_count = Column(Integer)
    created_on = Column(DateTime, default=datetime.now, nullable=True)
    changed_on = Column(DateTime, default=datetime.now, nullable=True)
    created_by_fk = Column(Integer)
    changed_by_fk = Column(Integer)
    api_key = Column(String(255))
    token = Column(String(1024), nullable=True, unique=True)
    token_last_update = Column(DateTime, nullable=True)

    def __init__(self, username, password, first_name, last_name, email):
        self.username = username
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.api_key = uuid.uuid4()

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return int(self.id)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        if self.id and self.username:
            return '{}'.format(
                self.username
            )


class IPData(Base):
    __tablename__ = 'ipdata'
    id = Column(Integer, primary_key=True)
    created_date = Column(DateTime, onupdate=datetime.now)
    ip = Column(String(15), index=True)
    user_agent = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    email = Column(String(255))
    home_phone = Column(String(15))
    cell_phone = Column(String(15))
    address1 = Column(String(255))
    address2 = Column(String(255))
    city = Column(String(255))
    state = Column(String(2))
    zip_code = Column(String(5))
    zip_4 = Column(Integer)
    country_name = Column(String(255))
    country_code = Column(String(2))
    country_code3 = Column(String(3))
    time_zone = Column(String(50))
    latitude = Column(Float(50))
    longitude = Column(Float(50))
    metro_code = Column(String(10))
    dma_code = Column(String(3))
    area_code = Column(String(3))
    geo_city = Column(String(255))
    postal_code = Column(String(50))
    region = Column(String(50))
    region_name = Column(String(255))
    credit_range = Column(String(50))
    car_year = Column(Integer)
    car_make = Column(String(255))
    car_model = Column(String(255))
    ppm_type = Column(String(10))
    ppm_indicator = Column(String(10))
    ppm_segment = Column(String(50))
    auto_trans_date = Column(String(50))
    last_seen = Column(String(50))
    birth_year = Column(Integer)
    income_range = Column(String(50))
    home_owner_renter = Column(String(50))
    auto_purchase_type = Column(String(100))
    processed = Column(Boolean, default=False)
    validated = Column(Boolean, default=False)

    def __repr__(self):
        return 'Visitor from {} on {}'.format(
            self.ip,
            self.created_date
        )

    def person_name(self):
        if self.first_name and self.last_name:
            return '{} {}'.format(
                self.first_name,
                self.last_name
            )

    def person_location(self):
        if self.address1:
            return '{} {} {} {} {}'.format(
                self.address1,
                self.address2,
                self.city, self.state, self.zip_code
            )

    def contact_info(self):
        if self.home_phone or self.cell_phone:
            return '{} {}'.format(
                self.home_phone,
                self.cell_phone
            )

    def auto_data(self):
        if self.car_year and self.car_model:
            return '{} {} {}'.format(
                self.car_year,
                self.car_make,
                self.car_model
            )

    def buyer(self):
        if self.auto_trans_date:
            return '{} {} {}'.format(
                self.auto_trans_date,
                self.credit_range,
                self.auto_purchase_type
            )

    def purchase(self):
        if self.ppm_type and self.ppm_segment:
            return '{} {} {}'.format(
                self.ppm_type,
                self.ppm_segment,
                self.ppm_indicator
            )

    def geo_data(self):
        return '{} {} {} {} {} {} {} {} {} {} {}'.format(
            self.latitude,
            self.longitude,
            self.time_zone,
            self.geo_city,
            self.region,
            self.postal_code,
            self.country_name,
            self.country_code,
            self.country_code3,
            self.metro_code,
            self.dma_code
        )


class APILog(Base):
    """
    The API access log
    """
    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    username = relationship('User')
    log_date = Column(DateTime, default=datetime.now())
    resource = Column(String(64), default='ipdata')

    def _repr__(self):
        if self.id and self.log_date:
            return 'ID: {}, Date: {}, User: {}, Resource: {}'.format(
                self.id,
                self.log_date,
                self.username,
                self.resource
            )
