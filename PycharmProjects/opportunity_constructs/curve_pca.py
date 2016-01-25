
import shared.calendar_utilities as cu
import get_price.curve_data as cd
import pandas as pd
import numpy as np
import shared.statistics as stats
import ta.strategy as ts
import os.path


def get_curve_pca_report(**kwargs):

    ticker_head = kwargs['ticker_head']
    date_to = kwargs['date_to']

    if 'use_existing_filesQ' in kwargs.keys():
        use_existing_filesQ = kwargs['use_existing_filesQ']
    else:
        use_existing_filesQ = True

    output_dir = ts.create_strategy_output_dir(strategy_class='curve_pca', report_date=date_to)

    if os.path.isfile(output_dir + '/' + ticker_head + '.pkl') and use_existing_filesQ:
        pca_results = pd.read_pickle(output_dir + '/' + ticker_head + '.pkl')
        return {'pca_results': pca_results, 'success': True}

    date10_years_ago = cu.doubledate_shift(date_to, 10*365)

    if ticker_head == 'ED':
        num_contracts = 12
    else:
        num_contracts = 18


    rolling_data = cd.get_rolling_curve_data(ticker_head=ticker_head, num_contracts=num_contracts,
                                         front_tr_dte_limit=10,
                                        date_from=date10_years_ago,
                                        date_to=date_to)

    datetime_to = cu.convert_doubledate_2datetime(date_to)

    if datetime_to != rolling_data[0].index[-1].to_datetime():
        return {'pca_results': pd.DataFrame(), 'success': False}

    if ticker_head == 'ED':
        yield_raw = [rolling_data[x]['close_price']-rolling_data[x+1]['close_price'] for x in range(len(rolling_data)-1)]
    else:
        yield_raw = [(rolling_data[x]['close_price']-rolling_data[x+1]['close_price'])/rolling_data[x+1]['close_price'] for x in range(len(rolling_data)-1)]

    yield_merged = pd.concat(yield_raw, axis=1)
    yield_data = 100*yield_merged.values

    change5_raw = [rolling_data[x]['change5']-rolling_data[x+1]['change5'] for x in range(len(rolling_data)-1)]
    change5_merged = pd.concat(change5_raw, axis=1)
    change5_data = change5_merged.values

    tr_dte_raw = [rolling_data[x]['tr_dte'] for x in range(len(rolling_data)-1)]
    tr_dte__merged = pd.concat(tr_dte_raw, axis=1)
    tr_dte_data = tr_dte__merged.values

    pca_out = stats.get_pca(data_input=yield_data, n_components=2)

    residuals = yield_data-pca_out['model_fit']

    ticker1_list = [rolling_data[x]['ticker'][-1] for x in range(len(rolling_data)-1)]
    ticker2_list = [rolling_data[x+1]['ticker'][-1] for x in range(len(rolling_data)-1)]

    price_list = [rolling_data[x]['close_price'][-1]-rolling_data[x+1]['close_price'][-1] for x in range(len(rolling_data)-1)]

    pca_results = pd.DataFrame.from_items([('ticker1',ticker1_list),
                             ('ticker2',ticker2_list),
                             ('tr_dte_front', tr_dte_data[-1]),
                             ('residuals',residuals[-1]),
                             ('price',price_list),
                             ('yield',yield_data[-1]),
                             ('z', (residuals[-1]-residuals.mean(axis=0))/residuals.std(axis=0)),
                             ('factor_load1',pca_out['loadings'][0]),
                             ('factor_load2',pca_out['loadings'][1]),
                             ('change5', change5_data[-1])])

    pca_results['residuals'] = pca_results['residuals'].round(3)
    pca_results['yield'] = pca_results['yield'].round(2)
    pca_results['z'] = pca_results['z'].round(2)
    pca_results['factor_load1'] = pca_results['factor_load1'].round(3)
    pca_results['factor_load2'] = pca_results['factor_load2'].round(3)

    pca_results.to_pickle(output_dir + '/' + ticker_head + '.pkl')

    return {'pca_results': pca_results, 'success': True}

