#!/usr/bin/env python
from bs4 import BeautifulSoup
import csv
import numpy as np
import re
import requests
import sys
import time

# Constants
YEARLY_TOTAL_TO_SPEND = 20000  # $
MIN_HOURS = 100  # hours

YEARLY_INSURANCE = 2000  # $
YEARLY_MAINENANCE = 3000  # $
YEARLY_HANGAR = 230 * 12  # $
LOW_LOAN = 0.04  # %
HIGH_LOAN = 0.07  # %
SHORT_LOAN = 10  # years
LONG_LOAN = 20  # years

ENGINE_OVERHAUL_COST = 30000  # $
ENGINE_OVERHAUL_TIME = 1700  # hours

PROP_OVERHAUL_COST = 8000  # $
PROP_OVERHAUL_TIME = 2000  # hours

OIL_CHANGE_COST_PER_50_HOURS = 125  # $

GAS_PER_GALLON = 5  # $
GAS_PER_HOUR = 15  # gallons

OIL_COST_PER_HOUR = 2  # $

TIME_BETWEEN_REQUESTS = 90  # seconds

OUT_FILE = 'Desktop/out.csv'


BASE_URL = 'https://www.trade-a-plane.com/'
SEARCH_URL = BASE_URL + 'search?s-type=aircraft&s-advanced=yes&sale_status=For+Sale&category_level1=Single+Engine+Piston&make=BEECHCRAFT&model_group=BEECHCRAFT+35+BONANZA+SERIES&user_distance=1000000&s-custom_style=oneline&s-page_size=96'
page = requests.get(SEARCH_URL)

soup = BeautifulSoup(page.content, 'html.parser')
search_results = soup.find_all('a', class_="log_listing_click")

v35_list = [result for result in search_results if 'V35' in str(result)]

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
    
        loan_after_downpayment = price * 0.85
        highest_loan = -np.pmt(HIGH_LOAN/12, SHORT_LOAN*12, loan_after_downpayment)
        lowest_loan = -np.pmt(LOW_LOAN/12, LONG_LOAN*12, loan_after_downpayment)

        total_fixed_high = highest_loan + YEARLY_HANGAR + YEARLY_INSURANCE + YEARLY_MAINENANCE
        total_fixed_low = lowest_loan + YEARLY_HANGAR + YEARLY_INSURANCE + YEARLY_MAINENANCE

        variable_hourly = (  GAS_PER_GALLON * GAS_PER_HOUR
                       + OIL_COST_PER_HOUR
                       + OIL_CHANGE_COST_PER_50_HOURS/50.0
                       + ENGINE_OVERHAUL_COST/(ENGINE_OVERHAUL_TIME - engine_time)
                       + PROP_OVERHAUL_COST/(PROP_OVERHAUL_TIME - prop_time)
                      )
    
        low_yearly_hours = int((YEARLY_TOTAL_TO_SPEND - total_fixed_high)/variable_hourly)
    
        if low_yearly_hours > MIN_HOURS:
            url_to_checkout.append(v35_url)
            hours_per_year.append(low_yearly_hours)

if hours_per_year and url_to_checkout:
    hours_per_year, url_to_checkout = (list(t) for t in zip(*sorted(zip(hours_per_year, url_to_checkout), reverse=True)))
                                   
    with open(OUT_FILE, mode='w') as f:
        writer = csv.writer(f)
        for i in range(0, len(hours_per_year)):
            print(str(hours_per_year[i]) + ',' + str(BASE_URL) + str(url_to_checkout[i]))
            print('\n')
            writer.writerow([str(hours_per_year[i]), str(BASE_URL) + str(url_to_checkout[i])])   
else:
    print(f'No results for ${YEARLY_TOTAL_TO_SPEND} yearly and minimum {MIN_HOURS} hours per year.')
