#!/usr/bin/env python
import argparse
from bs4 import BeautifulSoup
import csv
import numpy as np
import re
import requests
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("-ts", "--total_to_spend", default=25000, help="Enter the total amount you are willing to spend per year in dollars without symbols or commas.", type=int)
parser.add_argument("-mh", "--min_hours", default=125, help="Enter the minimum hours you want to fly per year as an integer.", type=int)
parser.add_argument("-lp", "--loan_percent", default=0.07, help="Enter the loan percentage as a decimal.", type=float)
parser.add_argument("-ll", "--loan_length", default=20, help="Enter the length of the loan in years.", type=int)
parser.add_argument("-eoc", "--engine_overhaul_cost", default=30000, help="Enter the cost of an engine overhaul as an integer, no symbols or commas.", type=int)
parser.add_argument("-etbo", "--engine_time_between_overhauls", default=1700, help="Enter engine time between overhauls as an integer, no symbols or commas.", type=int)
parser.add_argument("-poc", "--prop_overhaul_cost", default=8000, help="Enter the cost of a prop overhaul as an integer, no symbols or commas.", type=int)
parser.add_argument("-ptbo", "--prop_time_between_overhauls", default=2000, help="Enter prop time between overhauls as an integer, no symbols or commas.", type=int)
parser.add_argument("-occ", "--oil_change_cost", default=125, help="Enter the oil change cost per 50 hours as an integer, no symbols or commas.", type=int)
parser.add_argument("-gc", "--gas_cost", default=5.00, help="Enter the cost of gas as a float, no symbols or commas.", type=float)
parser.add_argument("-gph", "--gallons_per_hour", default=15.0, help="Enter the average gallons per hour as a float.", type=float)
parser.add_argument("-ins", "--insurance", default=2000, help="Enter the yearly insurance cost as an integer, no symbols or commas.", type=int)
parser.add_argument("-maint", "--maintenance", default=3000, help="Enter the yearly maintenance cost as an integer, no symbols or commas.", type=int)
parser.add_argument("-han", "--hangar", default=230, help="Enter the monthly hangar cost as an integer, no symbols are commas.", type=int)
parser.add_argument("-och", "--oil_cost_per_hour", default=2.0, help="Enter the oil cost per hour as a float, no symbols or commas.", type=float)
parser.add_argument("-o", "--output_file", default="out.csv", help="Specify outoutfile.", type=str)
parser.add_argument("-m", "--make", default='BEECHCRAFT', help="Specify aircraft make as all capital string.", type=str)
parser.add_argument("-mg", "--model_group", default="+35+BONANZA+SERIES", help="Specify aircraft model group, for example, '+35+BONANZA+SERIES'.", type=str)
parser.add_argument("-mt", "--model_type", default="V35", help="Specify a model subtype as all capital string, can leave of specific, for example V35 or V35A.", type=str) 
parser.add_argument("-dpp", "--down_payment_percent", default=0.15, help="Enter downpayment percentage as a decimal.", type=float)

args=parser.parse_args()

# Constants
YEARLY_TOTAL_TO_SPEND = args.total_to_spend  # $
MIN_HOURS = args.min_hours  # hours

YEARLY_INSURANCE = args.insurance  # $
YEARLY_MAINENANCE = args.maintenance  # $
YEARLY_HANGAR = args.hangar * 12 # $
LOAN_PERC = args.loan_percent  # %
LOAN_LENGTH = args.loan_length  # years

ENGINE_OVERHAUL_COST = args.engine_overhaul_cost  # $
ENGINE_OVERHAUL_TIME = args.engine_time_between_overhauls  # hours

PROP_OVERHAUL_COST = args.prop_overhaul_cost  # $
PROP_OVERHAUL_TIME = args.prop_time_between_overhauls  # hours

OIL_CHANGE_COST_PER_50_HOURS = args.oil_change_cost  # $

GAS_PER_GALLON = args.gas_cost  # $
GAS_PER_HOUR = args.gallons_per_hour  # gallons

OIL_COST_PER_HOUR = args.oil_cost_per_hour  # $

OUT_FILE = args.output_file

TIME_BETWEEN_REQUESTS = 90  # seconds


BASE_URL = 'https://www.trade-a-plane.com/'
SEARCH_URL = BASE_URL + f'search?s-type=aircraft&s-advanced=yes&sale_status=For+Sale&category_level1=Single+Engine+Piston&make={args.make}&model_group=BEECHCRAFT{args.model_group}&user_distance=1000000&s-custom_style=oneline&s-page_size=96'
page = requests.get(SEARCH_URL)

soup = BeautifulSoup(page.content, 'html.parser')
search_results = soup.find_all('a', class_="log_listing_click")

v35_list = [result for result in search_results if args.model_type in str(result)]

url_to_checkout = []
hours_per_year = []

print(f'Approximate run time is {int(len(v35_list)/3*90/60)} minutes.\n')

for i in range(0, len(v35_list), 3):
    v35 = v35_list[i]
    s = str(v35)
    start = s.find('href="') + len('href=""')
    end = s.find('type=aircraft"') + len('type=aircraft')
    v35_url = s[start:end]
    
    time.sleep(TIME_BETWEEN_REQUESTS)
    v35_page = requests.get(BASE_URL + v35_url)
    v35_soup = BeautifulSoup(v35_page.content, 'html.parser')
    
    while '429 Too Many Requests' in str(v35_soup):
        print(v35_soup)
        sys.exit(0)

    print(f'Request {i/3+1} of {int(len(v35_list)/3)} successful.')
    
    v35_soup.find('p', class_="price")
    s = str(v35_soup)
    start = s.find('> $') + len('> $')
    end = s.find(' <span itemprop="priceCurrency"')
    price = int(s[start:end].replace(',',''))
    
    total_time = v35_soup.find("label", text='Total Time:')
    engine_time = v35_soup.find("label", text='Engine 1 Time:')
    prop_time = v35_soup.find("label", text='Prop 1 Time:')
    if total_time and engine_time and prop_time:
        total_time = total_time.next_sibling.strip()
        engine_time = int(re.findall("\d+", engine_time.next_sibling.strip())[0])
        prop_time = int(re.findall("\d+", prop_time.next_sibling.strip())[0])
    
        loan_after_downpayment = price * (1.0-args.down_payment_percent)
        loan = -np.pmt(LOAN_PEC/12, LOAN_LENGTH*12, loan_after_downpayment)

        total_fixed = loan + YEARLY_HANGAR + YEARLY_INSURANCE + YEARLY_MAINENANCE

        variable_hourly = (  GAS_PER_GALLON * GAS_PER_HOUR
                       + OIL_COST_PER_HOUR
                       + OIL_CHANGE_COST_PER_50_HOURS/50.0
                       + ENGINE_OVERHAUL_COST/(ENGINE_OVERHAUL_TIME - engine_time)
                       + PROP_OVERHAUL_COST/(PROP_OVERHAUL_TIME - prop_time)
                      )
    
        yearly_hours = int((YEARLY_TOTAL_TO_SPEND - total_fixed)/variable_hourly)
    
        if yearly_hours > MIN_HOURS:
            url_to_checkout.append(v35_url)
            hours_per_year.append(low_yearly_hours)

if hours_per_year and url_to_checkout:
    hours_per_year, url_to_checkout = (list(t) for t in zip(*sorted(zip(hours_per_year, url_to_checkout), reverse=True)))
                                   
    with open(output_file, mode='w') as f:
        writer = csv.writer(f)
        for i in range(0, len(hours_per_year)):
            print(str(hours_per_year[i]) + ',' + str(BASE_URL) + str(url_to_checkout[i]))
            print('\n')
            writer.writerow([str(hours_per_year[i]), str(BASE_URL) + str(url_to_checkout[i])])   
else:
    print(f'No results for ${YEARLY_TOTAL_TO_SPEND} yearly and minimum {MIN_HOURS} hours per year.')
