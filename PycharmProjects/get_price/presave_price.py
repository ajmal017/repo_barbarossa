__author__ = 'kocat_000'

import os.path
import get_price.get_futures_price as gfp
import contract_utilities.contract_meta_info as cmi
import contract_utilities.expiration as exp
from pandas.tseries.offsets import CustomBusinessDay
import shared.calendar_utilities as cu
import shared.directory_names as dn
import pandas as pd
import numpy as np
import datetime as dt
pd.options.mode.chained_assignment = None

presaved_futures_data_folder = dn.get_directory_name(ext='presaved_futures_data')

dirty_data_points = pd.DataFrame([('CLG2008', dt.datetime(2007, 5, 31), True),
                                  ('CLH2008', dt.datetime(2007, 5, 31), True),
                                  ('CLG2008', dt.datetime(2007, 6, 21), True),
                                  ('CLN2008', dt.datetime(2007, 6, 21), True),
                                  ('CLX2008', dt.datetime(2007, 6, 21), True),
                                  ('CLX2008', dt.datetime(2007, 6, 25), True)],
                                columns=['ticker','settle_date','discard'])

def generate_and_update_futures_data_file_4tickerhead(**kwargs):

    ticker_head = kwargs['ticker_head']

    if os.path.isfile(presaved_futures_data_folder + '/' + ticker_head + '.pkl'):
        old_data = pd.read_pickle(presaved_futures_data_folder + '/' + ticker_head + '.pkl')
        last_available_date = int(old_data['settle_date'].max().to_datetime().strftime('%Y%m%d'))
        date_from = cu.doubledate_shift(last_available_date, 60)
        data4_tickerhead = gfp.get_futures_price_4ticker(ticker_head=ticker_head,date_from=date_from)
    else:
        data4_tickerhead = gfp.get_futures_price_4ticker(ticker_head=ticker_head)

    data4_tickerhead = pd.merge(data4_tickerhead, dirty_data_points, on=['settle_date', 'ticker'],how='left')
    data4_tickerhead = data4_tickerhead[data4_tickerhead['discard'] != True]
    data4_tickerhead = data4_tickerhead.drop('discard', 1)

    data4_tickerhead['close_price'] = [float(x) if x is not None else float('NaN') for x in data4_tickerhead['close_price'].values]

    data4_tickerhead['cont_indx']= 100*data4_tickerhead['ticker_year']+data4_tickerhead['ticker_month']
    unique_cont_indx_list = data4_tickerhead['cont_indx'].unique()
    num_contracts = len(unique_cont_indx_list)
    unique_cont_indx_list = np.sort(unique_cont_indx_list)
    merged_dataframe_list = [None]*num_contracts

    bday_us = CustomBusinessDay(calendar=exp.get_calendar_4ticker_head('CL'))
    full_dates = pd.date_range(start=data4_tickerhead['settle_date'].min(),end=data4_tickerhead['settle_date'].max(), freq=bday_us)

    for i in range(num_contracts):

        contract_data = data4_tickerhead[data4_tickerhead['cont_indx']==unique_cont_indx_list[i]]

        contract_full_dates = full_dates[(full_dates>=contract_data['settle_date'].min()) & (full_dates<=contract_data['settle_date'].max())]
        full_date_frame = pd.DataFrame(contract_full_dates, columns=['settle_date'])
        merged_dataframe_list[i] = pd.merge(full_date_frame,contract_data,on='settle_date',how='left')

        merged_dataframe_list[i]['ticker'] = contract_data['ticker'][contract_data.index[0]]
        merged_dataframe_list[i]['ticker_head'] = contract_data['ticker_head'][contract_data.index[0]]
        merged_dataframe_list[i]['ticker_month'] = contract_data['ticker_month'][contract_data.index[0]]
        merged_dataframe_list[i]['ticker_year'] = contract_data['ticker_year'][contract_data.index[0]]

        merged_dataframe_list[i]['change1'] = merged_dataframe_list[i]['close_price'].shift(-2)-merged_dataframe_list[i]['close_price'].shift(-1)
        merged_dataframe_list[i]['change2'] = merged_dataframe_list[i]['close_price'].shift(-3)-merged_dataframe_list[i]['close_price'].shift(-1)
        merged_dataframe_list[i]['change5'] = merged_dataframe_list[i]['close_price'].shift(-6)-merged_dataframe_list[i]['close_price'].shift(-1)
        merged_dataframe_list[i]['change10'] = merged_dataframe_list[i]['close_price'].shift(-11)-merged_dataframe_list[i]['close_price'].shift(-1)
        merged_dataframe_list[i]['change20'] = merged_dataframe_list[i]['close_price'].shift(-21)-merged_dataframe_list[i]['close_price'].shift(-1)
        merged_dataframe_list[i]['change_5'] = merged_dataframe_list[i]['close_price']-merged_dataframe_list[i]['close_price'].shift(5)
        merged_dataframe_list[i]['change_1'] = merged_dataframe_list[i]['close_price']-merged_dataframe_list[i]['close_price'].shift(1)

    data4_tickerhead = pd.concat(merged_dataframe_list)

    if os.path.isfile(presaved_futures_data_folder + '/' + ticker_head + '.pkl'):
        clean_data = data4_tickerhead[np.isfinite(data4_tickerhead['change_5'])]
        clean_data['frame_indx'] = 1
        old_data['frame_indx'] = 0
        merged_data = pd.concat([old_data,clean_data],ignore_index=True)
        merged_data.sort(['cont_indx','settle_date','frame_indx'],ascending=[True,True,False],inplace=True)
        merged_data.drop_duplicates(subset=['settle_date','cont_indx'],take_last=False,inplace=True)
        data4_tickerhead = merged_data.drop('frame_indx',1,inplace=False)

    data4_tickerhead.to_pickle(presaved_futures_data_folder + '/' + ticker_head + '.pkl')

def generate_and_update_futures_data_files():

    for ticker_head in cmi.futures_butterfly_strategy_tickerhead_list:
        generate_and_update_futures_data_file_4tickerhead(ticker_head=ticker_head)


