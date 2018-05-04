__author__ = 'kocat_000'

import os
import contract_utilities.expiration as exp
import shared.calendar_utilities as cu

root_home = r'C:\Users\kocat_000\quantFinance'
root_work = r'C:\Research'
root_quantgo = r'D:\Research'
root_work_dropbox = r'C:\Users\ekocatulum\Dropbox'
tt_fill_directory = r'C:\tt\datfiles\Export'


extension_dict = {'presaved_futures_data': '/data/futures_data',
                  'book_snapshot_data': '/data/book_snapshot',
                  'config': '/config',
                  'ib_data': '/ib_data',
                  'drop_box_trading':'/trading',
                  'commitments_of_traders_data': '/data/fundamental_data/cot_data',
                  'intraday_ttapi_data': '/data/intraday_data/tt_api',
                  'intraday_ttapi_data_fixed_interval': '/data/intraday_data/tt_api_fixed_interval',
                  'raw_options_data': '/data/options_data_raw',
                  'options_backtesting_data': '/data/options_backtesting_data',
                  'option_model_test_data': '/data/option_model_tests',
                  'aligned_time_series_output': '/data/alignedTimeSeriesOutputTemp',
                  'ta': '/ta',
                  'admin': '/admin',
                  'test_data': '/data/test_data',
                  'stock_data': '/data/stock_data',
                  'strategy_output': '/strategy_output',
                  'backtest_results': '/backtest_results',
                  'daily': '/daily',
                  'log': '/logs',
                   'man_positions': '/man_positions',
                  'python_file': '/PycharmProjects'}


def get_directory_name(**kwargs):

    computer_name = os.environ['COMPUTERNAME']

    ext = kwargs['ext']

    if computer_name == '601-TREKW71' or computer_name == '601-TREKW72':
        if ext in ['ib_data', 'drop_box_trading']:
            root_dir = root_work_dropbox
        else:
            root_dir = root_work
    elif computer_name == 'WIN-3G1R7L5NT4H':
        root_dir = root_quantgo
    else:
        root_dir = root_home

    directory_name = root_dir + extension_dict[ext]

    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    return directory_name


def get_dated_directory_extension(**kwargs):

    if 'folder_date' in kwargs.keys():
        folder_date = kwargs['folder_date']
    else:
        folder_date = exp.doubledate_shift_bus_days()

    if 'ext' not in kwargs.keys():
        print('Need to provide a valid ext !')
        return

    directory_name = get_directory_name(**kwargs)

    dated_directory_name = directory_name + '/' + cu.get_directory_extension(folder_date)

    if not os.path.exists(dated_directory_name):
        os.makedirs(dated_directory_name)

    return dated_directory_name












