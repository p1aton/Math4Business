from selenium import webdriver
import numpy as np
import glob
import os
import time
import datetime
import pandas as pd
import re
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import requests
import json

def parse_bitinfocharts():
    d = webdriver.PhantomJS()
    d.set_page_load_timeout(5)
    try:
        d.get("https://bitinfocharts.com/")
    except:
        pass
    table = d.find_element_by_id('main_body').find_element_by_tag_name('tbody').get_attribute('innerHTML')
    bs = BeautifulSoup(table, "lxml")
    d.quit()
    df = pd.DataFrame()
    df['Columns'] = [k.find('td').getText() for k in bs.find_all('tr')]
    for crypto in ['btc', 'eth', 'ltc']:
        df[crypto.upper()] = [p.getText() for p in bs.find_all(class_='c_%s' % crypto)]
    df2 = df.copy()
    stopwords = ['BTC', 'ETH', 'LTC']
    def remove_chars(x):
        num = re.sub('[^0-9]','', x)
        if len(str(num)) < 3:
            return x
        else:
            return num
    def convert_number(x):
        return float(x.replace(',',''))
    def remove_crypt(x):
        for k in stopwords:
            if k in x:
                return convert_number(x[:x.index(k)])
    def clean_reward(x):
        for k in stopwords:
            if k in x:
                x = x[:x.index(k)]
                return tuple(map(float, x.replace(',','').split('+')))

    df2.loc[0] = df2.loc[0].apply(lambda x:x[:x.index('(')] if '(' in x else x)
    df2.loc[1] = df2.loc[1].apply(remove_chars)
    df2.loc[2] = df2.loc[2].apply(lambda x:convert_number(x[x.find('$')+1:x.find('USD')]) if 'USD' in x else x)
    df2.loc[3] = df2.loc[3].apply(lambda x:convert_number(x[x.find('$')+1:x.find('USD')]) if 'USD' in x else x)
    df2.iloc[4, 1:] = df2.iloc[4, 1:].apply(convert_number)
    for p in range(6,10):
        df2.iloc[p, 1:] = df2.iloc[p, 1:].apply(remove_crypt)
    df2.iloc[14, 1:] = df2.iloc[14, 1:].apply(clean_reward)
    df2.iloc[15, 1:] = df2.iloc[15, 1:].apply(clean_reward)
    return df2

def parse_one_day_btc(year, month, day):
    """
    Scrapper to get all the block of one day on BTC.com
    :param date: info about the day to scrap
    """
    d = webdriver.PhantomJS()
    d.get("https://btc.com/block?date=%s-%s-%s" % (year, month, day))
    table = d.find_element_by_class_name('table').find_element_by_tag_name('tbody').get_attribute('innerHTML')
    bs = BeautifulSoup(table, "lxml")
    d.quit()
    row = bs.find_all('tr')[1:]
    cols = pd.Series([k.getText() for k in bs.find_all('tr')[0].find_all('th')][:-1]), 
    values = pd.DataFrame([[k.getText().strip() for k in r.find_all('td')][:-1] for r in row])
    # print('Day %s/%s done!' % (day, month))
    return cols, values

def parse_btc(n_days=10):
    """
    Parsing multiple days all the block from BTC.com
    :param n_days: number of days to parse
    :return: "clean" dataframe
    """
    month = datetime.now().month
    year = datetime.now().year
    current_day = datetime.now().day

    df = pd.DataFrame()
    for dd in range(current_day, current_day-n_days, -1):
        cols, temp = parse_one_day_btc(year, month, dd)
        df = pd.concat([df, temp])
    df = df.reset_index(drop=True)
    df.columns = cols[0]
    if len(df.columns) > 8:
        del df[df.columns[1]]
    # Remove ',' in number 
    for col in df.columns[:6]:
        df[col] = df[col].apply(lambda x:float(x.replace(',', '')))
    df['RewardFee'] = df[df.columns[6]].apply(lambda x:float(x[x.index('+ ')+2:x.index(' BTC')]))
    return df

def parse_one_day_ether(p_number, verbose=False):
    """
    Scrapper to get all the block of one day on EtherScan
    :param p_number: page number to scrap
    :param verbose: boolean for verbose
    """
    d = webdriver.Chrome()
    try:
        d.set_page_load_timeout(7)
        d.get("https://etherscan.io/blocks?p=%s" % p_number)
    except TimeoutException:
        pass
    table = d.find_element_by_class_name('table').find_element_by_tag_name('tbody').get_attribute('innerHTML')
    thead = d.find_element_by_class_name('table').find_element_by_tag_name('thead').get_attribute('innerHTML')
    bs = BeautifulSoup(table, "lxml")
    thead = BeautifulSoup(thead, "lxml")
    d.quit()
    cols = pd.Series([k.getText() for k in thead.find_all('th')]) 
    row = bs.find_all('tr')
    values = pd.DataFrame([[k.getText().strip() for k in r.find_all('td')] for r in row])
    time = pd.Series([r.find_all('td')[1].span.attrs['data-original-title'] for r in row])
    if verbose:
        print('Page %s done' % p_number)
    return cols, values, time

def parse_ether(n_blocks):
    """
    Parsing multiple days all the block from EtherScan.
    Caution it could be long : 0.16s/block
    :param n_blocks: number of blocks to parse
    :return: "clean" dataframe
    """ 
    df = pd.DataFrame()
    page_number_max = int(n_blocks/25) # 25 block per page
    for dd in range(1, page_number_max+1):
        cols, temp, time = parse_one_day_ether(dd)
        temp.columns = cols.values
        temp['Age'] = time
        df = pd.concat([df, temp])
    # Remove duplicates, Ethereum blocks can be faster than scrapping
    df = df.drop_duplicates(df.columns[0])
    df = df.reset_index(drop=True)
    # Cleaning
    df[df.columns[8]] = df[df.columns[8]].apply(lambda x:float(x[:x.find(' E')]))
    df[df.columns[7]] = df[df.columns[7]].apply(lambda x:float(x[:x.find(' G')].replace(',', '')) if not '-' in x else 0)
    df[df.columns[2]] = df[df.columns[2]].apply(float)
    return df

def parse_one_block_blockcypher(blockchain, block_number):
    """
    Parsing one LTC block usting BlockCypher API
    Hourly rate : 200 blocks
    :param blockchain: Cryptocurrency symbol (e.g ltc, doge)
    :param block_number: block number to parse
    :return: dict with values, -1 if not good status_code
    """
    results = {}
    response = requests.get('https://api.blockcypher.com/v1/%s/main/blocks/%s' % (blockchain, block_number))
    if response.status_code == 200:
        r = json.loads(response.content.decode('latin1'))
        results["fees_satoshi"] = r['fees']
        results['block_number'] = r['height']
        results['transactions'] = r['n_tx']
        results['time'] = r['time']
        results['nonce'] = r['nonce']
        results['blockchain'] = r["chain"]
        return results
    else:
        return -1

def get_first_block(blockchain):
    """
    Use BitInfoCharts to get the first ltc block number
    :return: block number as int
    """
    response = requests.get('https://api.blockcypher.com/v1/%s/main' % blockchain)
    if response.status_code == 200:
        return int(json.loads(response.content.decode('latin1'))['height'])
    elif response.status_code == 429:
        print('Too many requests')

def parse_blockcypher(blockchain, first_block=None, n_block=200):
    """
    Parsing multiple crypto blocks usting BlockCypher API
    :param blockchain: Cryptocurrency symbol (e.g ltc, doge)
    :param first_block: most recent block to parse
    :param last_block: last block to parse (< first_block)
    :return: list of dictionaries for each block
    """
    r = []
    if not first_block:
        first_block = get_first_block(blockchain)
    for block_number in range(first_block, first_block-n_block, -1):
        block = parse_one_block_blockcypher(blockchain, block_number)
        if block != -1:
            r.append(block)
        else:
            print('Error after block number %s (%s blocks done)' % (block_number, first_block-block_number))
            break
    return pd.DataFrame(r)