#!.env/bin/python
# -*- coding: utf-8 -*-

import csv
from db import db_session
from sqlalchemy import exc
from models import IPData
from datetime import datetime


def write_row(rec):
    """
    Write the record to the database
    :param rec:
    :return: none
    """
    try:
        data = IPData(
            created_date=datetime.now(),
            ip=rec[2],
            user_agent='',
            country_name=rec[4],
            geo_city=rec[5],
            time_zone=rec[6],
            latitude=rec[7],
            longitude=rec[8],
            metro_code=rec[9],
            country_code=rec[10],
            country_code3=rec[11],
            dma_code=rec[12],
            area_code=rec[13],
            postal_code=rec[14],
            region=rec[15],
            region_name=rec[16],
            first_name=rec[17],
            last_name=rec[18],
            email=rec[19],
            home_phone=rec[20],
            cell_phone=rec[21],
            address1=rec[22],
            address2=rec[23],
            city=rec[24],
            state=rec[25],
            zip_code=rec[26],
            credit_range=rec[27],
            car_year=rec[28] or 0,
            car_make=rec[29],
            car_model=rec[30],
            ppm_type=rec[31],
            ppm_indicator=rec[32],
            ppm_segment=rec[33],
            auto_trans_date=rec[34],
            last_seen=rec[35],
            birth_year=rec[36] or 0,
            income_range=rec[37],
            home_owner_renter=rec[38],
            auto_purchase_type=rec[39]
        )

        db_session.add(data)
        db_session.commit()
        print('Saved {} to database'.format(str(rec[2])))

    except exc.SQLAlchemyError as db_err:
        print('Database error: {}'.format(str(db_err)))


def read_file(filepath):
    """
    Read the csv file from the local filepath
    :param filepath:
    :return:
    """
    counter = 0

    try:
        with open(filepath, 'r') as f1:
            reader = csv.reader(f1, delimiter=',')
            # [next(reader) for _ in range(57085)]
            for row in reader:
                write_row(row)
                counter += 1

    except IOError as io_err:
        print('Error accessing the CSV file: {}'.format(str(io_err)))

    # return the row count
    return counter


def main():
    """
    Program entry point
    :return:
    """
    filepath = '/home/craigderington/Downloads/IPData.csv'

    try:
        print('Imported {} records successfully'.format(read_file(filepath)))

    except IOError as io_err:
        print('Error accessing the import file: {}'.format(str(io_err)))


if __name__ == '__main__':
    print('Starting up the data import engine...')
    main()
