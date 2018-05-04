
import shared.downloads as sd
import shared.directory_names as dn
import shared.utils as su
import contract_utilities.expiration as exp
import shared.calendar_utilities as cu
import pandas as pd
import datetime as dt
import os.path
from alpha_vantage.timeseries import TimeSeries
import time as t

other_symbol_address = 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt'
nasdaq_symbol_address = 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt'

def get_symbol_frame(**kwargs):

    frame_type = kwargs['frame_type']
    settle_date = kwargs['settle_date']

    if frame_type=='nasdaq':
        symbol_address = nasdaq_symbol_address
    elif frame_type=='other':
        symbol_address = other_symbol_address

    output_dir = dn.get_directory_name(ext='stock_data')
    file_name = output_dir + '/' + frame_type + '_' + str(settle_date) + '.pkl'

    if os.path.isfile(file_name):
        return pd.read_pickle(file_name)
    else:

        datetime_now = dt.datetime.now()

        if datetime_now.weekday() in [5, 6]:
            last_settle_date = exp.doubledate_shift_bus_days()
        elif 100 * datetime_now.hour + datetime_now.minute > 930:
            last_settle_date = cu.get_doubledate()
        else:
            last_settle_date = exp.doubledate_shift_bus_days()

        if settle_date==last_settle_date:

            data_list = sd.download_txt_from_web(web_address=symbol_address)
            column_names = data_list[0].decode('iso-8859-1').split("|")
            parset_data_list = [data_list[x].decode('iso-8859-1').split("|") for x in range(1, len(data_list) - 1)]
            symbol_frame = pd.DataFrame(parset_data_list, columns=column_names)
            symbol_frame.to_pickle(file_name)
        else:
            symbol_frame = pd.DataFrame()

    return symbol_frame

def save_stock_data(**kwargs):

    settle_date = kwargs['settle_date']

    other_frame = get_symbol_frame(frame_type='other', settle_date=settle_date)
    nasdaq_frame = get_symbol_frame(frame_type='nasdaq', settle_date=settle_date)

    other_frame = other_frame[['$' not in x and '.' not in x for x in other_frame['ACT Symbol']]]
    nasdaq_frame = nasdaq_frame[['$' not in x and '.' not in x for x in nasdaq_frame['Symbol']]]

    symbol_list = list(set(list(nasdaq_frame['Symbol'].unique()) + list(other_frame['ACT Symbol'].unique())))

    file_dir = dn.get_directory_name(ext='drop_box_trading')
    file_name = file_dir + '/apiKeys.txt'
    config_output = su.read_config_file(file_name=file_name)
    apiKey = config_output['alphaVantage']

    output_dir = dn.get_directory_name(ext='stock_data')
    ts = TimeSeries(key=apiKey, output_format='pandas')

    for i in range(len(symbol_list)):
        file_name = output_dir + '/' + symbol_list[i] + '.pkl'
        if os.path.isfile(file_name):
            old_data = pd.read_pickle(file_name)
            while True:
                try:
                    t.sleep(1)
                    result = ts.get_daily_adjusted(symbol=symbol_list[i], outputsize='compact')
                    new_data = result[0]
                    new_data['frame_indx'] = 1
                    old_data['frame_indx'] = 0

                    new_data['settle_date'] = new_data.index
                    new_data.rename(columns={'1. open': 'open', '2. high': 'high', '3. low': 'low', '4. close': 'close',
                                 '5. adjusted close': 'adjusted_close', '6. volume': 'volume',
                                 '7. dividend amount': 'dividend_amount',
                                 '8. split coefficient': 'split_coefficient'}, inplace=True)
                    new_data['settle_datetime'] = [dt.datetime.strptime(x, '%Y-%m-%d') for x in new_data['settle_date']]

                    merged_data = pd.concat([old_data, new_data], ignore_index=True)
                    merged_data.sort(['settle_date', 'frame_indx'], ascending=[True, False], inplace=True)
                    merged_data.drop_duplicates(subset=['settle_date'], take_last=False, inplace=True)
                    merged_data = merged_data.drop('frame_indx', 1, inplace=False)
                    merged_data.reset_index(drop=True, inplace=True)
                    merged_data.to_pickle(file_name)
                    break
                except Exception as e:
                    print(e)
                    if 'API call frequency' in str(e):
                        print('waiting 20 seconds...')
                        t.sleep(20)
                    else:
                        break

        else:
            print(str(i) + ': ' + symbol_list[i])
            while True:
                try:
                    t.sleep(1)
                    result = ts.get_daily_adjusted(symbol=symbol_list[i], outputsize='full')
                    data_out = result[0]

                    data_out['settle_date'] = data_out.index
                    data_out.rename(columns={'1. open': 'open', '2. high': 'high', '3. low': 'low', '4. close': 'close',
                                             '5. adjusted close': 'adjusted_close', '6. volume': 'volume',
                                             '7. dividend amount': 'dividend_amount',
                                             '8. split coefficient': 'split_coefficient'}, inplace=True)
                    data_out['settle_datetime'] = [dt.datetime.strptime(x, '%Y-%m-%d') for x in data_out['settle_date']]
                    data_out.reset_index(drop=True, inplace=True)
                    data_out.to_pickle(file_name)
                    break
                except Exception as e:
                    print(e)
                    if 'API call frequency' in str(e):
                        print('waiting 20 seconds...')
                        t.sleep(20)
                    else:
                        break

if __name__ == "__main__":

    datetime_now = dt.datetime.now()

    if datetime_now.weekday() in [5, 6]:
        last_settle_date = exp.doubledate_shift_bus_days()
    elif 100 * datetime_now.hour + datetime_now.minute > 930:
        last_settle_date = cu.get_doubledate()
    else:
        last_settle_date = exp.doubledate_shift_bus_days()


    save_stock_data(settle_date=last_settle_date)









