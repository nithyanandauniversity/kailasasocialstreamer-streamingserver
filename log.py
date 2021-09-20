from datetime import datetime
import pytz
import logging

logging.basicConfig(filename='monitor.log', level=logging.INFO)

# Set local timezone to IST
tz = pytz.timezone('Asia/Kolkata')


def infolog(text):
    logging.info(
        f" {datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S')}  {text}")


def errorlog(text):
    logging.warning(
        f" {datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S')}  {text}")
