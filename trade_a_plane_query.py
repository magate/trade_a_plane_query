#!/usr/bin/env python
'''Create an HTML parser to query trade-a-plane based on how much money to spend per year
   and how many hours to fly per year.'''
import argparse
from bs4 import BeautifulSoup
import csv
import numpy as np  # TODO: Update this to numpy-financial instead.
import re
import requests
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument( "-m"
                   , "--make"
                   , help="Specify aircraft make as all capital string."
                   , type=str
                   , required=True)
parser.add_argument( "-mg"
                   , "--model_group"
                   , help="Specify aircraft model group, for example, '+35+BONANZA+SERIES'."
                   , type=str
                   , required=True)
parser.add_argument( "-mt"
                   , "--model_type"
                   , help="Specify a model subtype, all capital string, for example V35 or V35A."
                   , type=str
                   , required=True) 
parser.add_argument( "-dpp"
                   , "--down_payment_percent"
                   , default=0.15
                   , help="Enter downpayment percentage as a decimal."
                   , type=float)
parser.add_argument( "-eoc"
                   , "--engine_overhaul_cost"
                   , default=30000
                   , help="Enter the cost of an engine overhaul as an integer, no symbols or commas."
                   , type=int)
parser.add_argument( "-etbo"
                   , "--engine_time_between_overhauls"
                   , default=1700
                   , help="Enter engine time between overhauls as an integer, no symbols or commas."
                   , type=int)
parser.add_argument( "-gc"
                   , "--gas_cost"
                   , default=5.00
                   , help="Enter the cost of gas as a float, no symbols or commas."
                   , type=float)
parser.add_argument( "-gph"
                   , "--gallons_per_hour"
                   , default=15.0
                   , help="Enter the average gallons per hour as a float."
                   , type=float)
parser.add_argument( "-han"
                   , "--hangar"
                   , default=230
                   , help="Enter the monthly hangar cost as an integer, no symbols are commas."
                   , type=int)
parser.add_argument( "-ins"
                   , "--insurance"
                   , default=2000
                   , help="Enter the yearly insurance cost as an integer, no symbols or commas."
                   , type=int)
parser.add_argument( "-ll"
                   , "--loan_length"
                   , default=20
                   , help="Enter the length of the loan in years."
                   , type=int)
parser.add_argument( "-lp"
                   , "--loan_percent"
                   , default=0.07
                   , help="Enter the loan percentage as a decimal."
                   , type=float)
parser.add_argument( "-maint"
                   , "--maintenance"
                   , default=3000
                   , help="Enter the yearly maintenance cost as an integer, no symbols or commas."
                   , type=int)
parser.add_argument( "-mh"
                   , "--min_hours"
                   , default=125
                   , help="Enter the minimum hours you want to fly per year as an integer."
                   , type=int)
parser.add_argument( "-o"
                   , "--output_file"
                   , default="out.csv"
                   , help="Specify outoutfile."
                   , type=str)
parser.add_argument( "-occ"
                   , "--oil_change_cost"
                   , default=125
                   , help="Enter the oil change cost per 50 hours as an integer, no symbols or commas."
                   , type=int)
parser.add_argument( "-och"
                   , "--oil_cost_per_hour"
                   , default=2.0
                   , help="Enter the oil cost per hour as a float, no symbols or commas."
                   , type=float)
parser.add_argument( "-poc"
                   , "--prop_overhaul_cost"
                   , default=8000
                   , help="Enter the cost of a prop overhaul as an integer, no symbols or commas."
                   , type=int)
parser.add_argument( "-ptbo"
                   , "--prop_time_between_overhauls"
                   , default=2000
                   , help="Enter prop time between overhauls as an integer, no symbols or commas."
                   , type=int)
parser.add_argument( "-ts"
                   , "--total_to_spend"
                   , default=25000
                   , help="Enter the total amount to spend per year in dollars without symbols or commas."
                   , type=int)

args=parser.parse_args()

# Constants
DOWN_PAYMENT_PERCENT = args.down_payment_percent  # %
ENGINE_OVERHAUL_COST = args.engine_overhaul_cost  # $
ENGINE_OVERHAUL_TIME = args.engine_time_between_overhauls  # hours
GAS_PER_GALLON = args.gas_cost  # $
GALLONS_PER_HOUR = args.gallons_per_hour  # gallons
LOAN_LENGTH = args.loan_length  # years
LOAN_PERC = args.loan_percent  # %
MAKE = args.make  # str
MIN_HOURS = args.min_hours  # hours
MODEL_GROUP = args.model_group  # str
MODEL_TYPE = args.model_type  # str
NUM_LINKS = 3  # Each table result has 3 links per aircraft. Remove duplication. TODO use unique.
OIL_CHANGE_COST_PER_50_HOURS = args.oil_change_cost  # $
OIL_COST_PER_HOUR = args.oil_cost_per_hour  # $
OUT_FILE = args.output_file  # str
PROP_OVERHAUL_COST = args.prop_overhaul_cost  # $
PROP_OVERHAUL_TIME = args.prop_time_between_overhauls  # hours
YEARLY_HANGAR = args.hangar * 12 # $
YEARLY_INSURANCE = args.insurance  # $
YEARLY_MAINENANCE = args.maintenance  # $
YEARLY_TOTAL_TO_SPEND = args.total_to_spend  # $

# This is needed to avoid the 429 from trade-a-plane.
# I was not able to find what the time-out is but 90 seconds works well.
TIME_BETWEEN_REQUESTS = 90  # seconds

# Trade-a-plane single line advanced search.
BASE_URL = 'https://www.trade-a-plane.com/'
SEARCH_URL = ( BASE_URL 
    + f'search?s-type=aircraft&s-advanced=yes&sale_status=For+Sale&category_level1=Single+Engine+Piston&make={MAKE}&model_group=BEECHCRAFT{MODEL_GROUP}&user_distance=1000000&s-custom_style=oneline&s-page_size=96')
page = requests.get(SEARCH_URL)

# Look for links in the results.
soup = BeautifulSoup(page.content, 'html.parser')
search_results = soup.find_all('a', class_="log_listing_click")

# Find specified model in the results.
aircraft_list = [result for result in search_results if MODEL_TYPE in str(result)]

url_to_checkout = []
hours_per_year = []

# Print how long it will take with the 90 second wait.
print(f'Approximate run time is {int(len(aircraft_list)/3*90/60)} minutes.\n')

# Loop through results.
for i in range(0, len(aircraft_list), NUM_LINKS):
    aircraft = aircraft_list[i]
    # Parse aircraft string for url.
    s = str(aircraft)
    start = s.find('href="') + len('href=""')
    end = s.find('type=aircraft"') + len('type=aircraft')
    aircraft_url = s[start:end]
    
    # Don't send too many requests.
    time.sleep(TIME_BETWEEN_REQUESTS)

    # Find the aircraft page.
    aircraft_page = requests.get(BASE_URL + aircraft_url)
    aircraft_soup = BeautifulSoup(aircraft_page.content, 'html.parser')
    
    # TODO: Throw an error if too many requests. This can be handled more gracefully.
    while '429 Too Many Requests' in str(aircraft_soup):
        print(aircraft_soup)
        sys.exit(0)

    # Keep the user updated on progress.
    print(f'Request {i/NUM_LINKS+1} of {int(len(aircraft_list)/NUM_LINKS)} successful.')
    
    # TODO: Parse GPS string as input.
    # Only considering Garmin GPS.
    if 'GARMIN' or 'GNS' or 'G430' or 'G530' in str(aircraft_soup):
        aircraft_soup.find('p', class_="price")
        s = str(aircraft_soup)
        start = s.find('> $') + len('> $')
        end = s.find(' <span itemprop="priceCurrency"')
        price = int(s[start:end].replace(',',''))
        
        # Parse information.
        total_time = aircraft_soup.find("label", text='Total Time:')
        engine_time = aircraft_soup.find("label", text='Engine 1 Time:')
        prop_time = aircraft_soup.find("label", text='Prop 1 Time:')
        if total_time and engine_time and prop_time:
            # Strip into a string.
            total_time = total_time.next_sibling.strip()
            engine_time = int(re.findall(r"\d+", engine_time.next_sibling.strip())[0])
            prop_time = int(re.findall(r"\d+", prop_time.next_sibling.strip())[0])
            
            # Calculate loan based on listed price and down payment percentage.
            loan_after_downpayment = price * (1.0-DOWN_PAYMENT_PERCENT)

            # Calculate loan payments.
            loan = -np.pmt(LOAN_PERC/12, LOAN_LENGTH*12, loan_after_downpayment)
            
            # Total fixed costs yearly.
            total_fixed = loan + YEARLY_HANGAR + YEARLY_INSURANCE + YEARLY_MAINENANCE
            
            # Total variable costs per hour.
            variable_hourly = (  GAS_PER_GALLON * GALLONS_PER_HOUR
                               + OIL_COST_PER_HOUR
                               + OIL_CHANGE_COST_PER_50_HOURS/50.0
                               + ENGINE_OVERHAUL_COST/(ENGINE_OVERHAUL_TIME - engine_time)
                               + PROP_OVERHAUL_COST/(PROP_OVERHAUL_TIME - prop_time)
                              )
            
            # Based on amount willing to spend per year, how many hours are remaining to fly.
            yearly_hours = int((YEARLY_TOTAL_TO_SPEND - total_fixed)/variable_hourly)
            
            # Make sure hours remaining to fly are meaningful.
            if yearly_hours > MIN_HOURS:
                url_to_checkout.append(aircraft_url)
                hours_per_year.append(yearly_hours)

# Print to terminal and create a csv with results.
# Order by most hours able to fly.
# List hours able to fly per year and link to the aircraft.
if hours_per_year and url_to_checkout:
    hours_per_year, url_to_checkout = (list(t) for t in zip(*sorted(zip(hours_per_year, url_to_checkout), reverse=True)))
                                   
    with open(OUT_FILE, mode='w') as f:
        writer = csv.writer(f)
        for i in range(0, len(hours_per_year)):
            print(str(hours_per_year[i]) + ',' + str(BASE_URL) + str(url_to_checkout[i]))
            print('\n')
            writer.writerow([str(hours_per_year[i]), str(BASE_URL) + str(url_to_checkout[i])])   
# Let the user know if there are no results for the given criteria.
else:
    print(f'No results for ${YEARLY_TOTAL_TO_SPEND} yearly and minimum {MIN_HOURS} hours per year.')
