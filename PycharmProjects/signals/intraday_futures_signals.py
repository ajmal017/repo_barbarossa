
import signals.utils as sutil
import opportunity_constructs.utilities as opUtil
import contract_utilities.contract_lists as cl
import contract_utilities.expiration as exp
import contract_utilities.contract_meta_info as cmi
import get_price.get_futures_price as gfp
import shared.calendar_utilities as cu
import shared.statistics as stats
import pandas as pd
import numpy as np
import pytz as pytz
import datetime as dt
import time as tm
import signals.ifs as ifs
central_zone = pytz.timezone('US/Central')

def get_intraday_spread_signals(**kwargs):

    ticker_list = kwargs['ticker_list']
    date_to = kwargs['date_to']

    ticker_list = [x for x in ticker_list if x is not None]
    ticker_head_list = [cmi.get_contract_specs(x)['ticker_head'] for x in ticker_list]
    ticker_class_list = [cmi.ticker_class[x] for x in ticker_head_list]

    if 'tr_dte_list' in kwargs.keys():
        tr_dte_list = kwargs['tr_dte_list']
    else:
        tr_dte_list = [exp.get_days2_expiration(ticker=x,date_to=date_to, instrument='futures')['tr_dte'] for x in ticker_list]

    weights_output = sutil.get_spread_weights_4contract_list(ticker_head_list=ticker_head_list)

    if 'aggregation_method' in kwargs.keys() and 'contracts_back' in kwargs.keys():
        aggregation_method = kwargs['aggregation_method']
        contracts_back = kwargs['contracts_back']
    else:

        amcb_output = [opUtil.get_aggregation_method_contracts_back(cmi.get_contract_specs(x)) for x in ticker_list]
        aggregation_method = max([x['aggregation_method'] for x in amcb_output])
        contracts_back = min([x['contracts_back'] for x in amcb_output])

    if 'futures_data_dictionary' in kwargs.keys():
        futures_data_dictionary = kwargs['futures_data_dictionary']
    else:
        futures_data_dictionary = {x: gfp.get_futures_price_preloaded(ticker_head=x) for x in list(set(ticker_head_list))}

    if 'use_last_as_current' in kwargs.keys():
        use_last_as_current = kwargs['use_last_as_current']
    else:
        use_last_as_current = True

    if 'datetime5_years_ago' in kwargs.keys():
        datetime5_years_ago = kwargs['datetime5_years_ago']
    else:
        date5_years_ago = cu.doubledate_shift(date_to,5*365)
        datetime5_years_ago = cu.convert_doubledate_2datetime(date5_years_ago)

    if 'num_days_back_4intraday' in kwargs.keys():
        num_days_back_4intraday = kwargs['num_days_back_4intraday']
    else:
        num_days_back_4intraday = 5

    contract_multiplier_list = [cmi.contract_multiplier[x] for x in ticker_head_list]

    aligned_output = opUtil.get_aligned_futures_data(contract_list=ticker_list,
                                                          tr_dte_list=tr_dte_list,
                                                          aggregation_method=aggregation_method,
                                                          contracts_back=contracts_back,
                                                          date_to=date_to,
                                                          futures_data_dictionary=futures_data_dictionary,
                                                          use_last_as_current=use_last_as_current)

    aligned_data = aligned_output['aligned_data']
    current_data = aligned_output['current_data']
    spread_weights = weights_output['spread_weights']
    portfolio_weights = weights_output['portfolio_weights']
    aligned_data['spread'] = 0
    aligned_data['spread_pnl_1'] = 0
    aligned_data['spread_pnl1'] = 0
    spread_settle = 0

    last5_years_indx = aligned_data['settle_date']>=datetime5_years_ago

    num_contracts = len(ticker_list)

    for i in range(num_contracts):
        aligned_data['spread'] = aligned_data['spread']+aligned_data['c' + str(i+1)]['close_price']*spread_weights[i]
        spread_settle = spread_settle + current_data['c' + str(i+1)]['close_price']*spread_weights[i]
        aligned_data['spread_pnl_1'] = aligned_data['spread_pnl_1']+aligned_data['c' + str(i+1)]['change_1']*portfolio_weights[i]*contract_multiplier_list[i]
        aligned_data['spread_pnl1'] = aligned_data['spread_pnl1']+aligned_data['c' + str(i+1)]['change1_instant']*portfolio_weights[i]*contract_multiplier_list[i]

    aligned_data['spread_normalized'] = aligned_data['spread']/aligned_data['c1']['close_price']

    data_last5_years = aligned_data[last5_years_indx]

    percentile_vector = stats.get_number_from_quantile(y=data_last5_years['spread_pnl_1'].values,
                                                       quantile_list=[1, 15, 85, 99],
                                                       clean_num_obs=max(100, round(3*len(data_last5_years.index)/4)))

    downside = (percentile_vector[0]+percentile_vector[1])/2
    upside = (percentile_vector[2]+percentile_vector[3])/2

    date_list = [exp.doubledate_shift_bus_days(double_date=date_to,shift_in_days=x) for x in reversed(range(1,num_days_back_4intraday))]
    date_list.append(date_to)

    intraday_data = opUtil.get_aligned_futures_data_intraday(contract_list=ticker_list,
                                       date_list=date_list)

    intraday_data['time_stamp'] = [x.to_datetime() for x in intraday_data.index]
    intraday_data['settle_date'] = intraday_data['time_stamp'].apply(lambda x: x.date())

    end_hour = min([cmi.last_trade_hour_minute[x] for x in ticker_head_list])
    start_hour = max([cmi.first_trade_hour_minute[x] for x in ticker_head_list])

    trade_start_hour = dt.time(9, 30, 0, 0)

    if 'Ag' in ticker_class_list:
        start_hour1 = dt.time(0, 45, 0, 0)
        end_hour1 = dt.time(7, 45, 0, 0)
        selection_indx = [x for x in range(len(intraday_data.index)) if
                          ((intraday_data['time_stamp'].iloc[x].time() < end_hour1)
                           and(intraday_data['time_stamp'].iloc[x].time() >= start_hour1)) or
                          ((intraday_data['time_stamp'].iloc[x].time() < end_hour)
                           and(intraday_data['time_stamp'].iloc[x].time() >= start_hour))]

    else:
        selection_indx = [x for x in range(len(intraday_data.index)) if
                          (intraday_data.index[x].to_datetime().time() < end_hour)
                          and(intraday_data.index[x].to_datetime().time() >= start_hour)]

    intraday_data = intraday_data.iloc[selection_indx]

    intraday_data['spread'] = 0

    for i in range(num_contracts):
        intraday_data['c' + str(i+1), 'mid_p'] = (intraday_data['c' + str(i+1)]['best_bid_p'] +
                                         intraday_data['c' + str(i+1)]['best_ask_p'])/2

        intraday_data['spread'] = intraday_data['spread']+intraday_data['c' + str(i+1)]['mid_p']*spread_weights[i]

    unique_settle_dates = intraday_data['settle_date'].unique()
    intraday_data['spread1'] = np.nan

    for i in range(len(unique_settle_dates)-1):
        if (intraday_data['settle_date'] == unique_settle_dates[i]).sum() == \
                (intraday_data['settle_date'] == unique_settle_dates[i+1]).sum():
            intraday_data.loc[intraday_data['settle_date'] == unique_settle_dates[i],'spread1'] = \
                intraday_data['spread'][intraday_data['settle_date'] == unique_settle_dates[i+1]].values

    intraday_data = intraday_data[intraday_data['settle_date'].notnull()]

    intraday_mean = intraday_data['spread'].mean()
    intraday_std = intraday_data['spread'].std()

    intraday_data_last2days = intraday_data[intraday_data['settle_date'] >= cu.convert_doubledate_2datetime(date_list[-2]).date()]
    intraday_data_yesterday = intraday_data[intraday_data['settle_date'] == cu.convert_doubledate_2datetime(date_list[-1]).date()]

    intraday_mean2 = intraday_data_last2days['spread'].mean()
    intraday_std2 = intraday_data_last2days['spread'].std()

    intraday_mean1 = intraday_data_yesterday['spread'].mean()
    intraday_std1 = intraday_data_yesterday['spread'].std()

    intraday_z = (spread_settle-intraday_mean)/intraday_std

    num_obs_intraday = len(intraday_data.index)
    num_obs_intraday_half = round(num_obs_intraday/2)
    intraday_tail = intraday_data.tail(num_obs_intraday_half)

    num_positives = sum(intraday_tail['spread'] > intraday_data['spread'].mean())
    num_negatives = sum(intraday_tail['spread'] < intraday_data['spread'].mean())

    recent_trend = 100*(num_positives-num_negatives)/(num_positives+num_negatives)

    pnl_frame = ifs.get_pnl_4_date_range(date_to=date_to, num_bus_days_back=20, ticker_list=ticker_list)

    if len(pnl_frame.index)>15:
        historical_sharp = (250**(0.5))*pnl_frame['total_pnl'].mean()/pnl_frame['total_pnl'].std()
    else:
        historical_sharp = np.nan

    return {'downside': downside, 'upside': upside,'intraday_data': intraday_data,
            'z': intraday_z,'recent_trend': recent_trend,
            'intraday_mean': intraday_mean, 'intraday_std': intraday_std,
            'intraday_mean2': intraday_mean2, 'intraday_std2': intraday_std2,
            'intraday_mean1': intraday_mean1, 'intraday_std1': intraday_std1,
            'aligned_output': aligned_output, 'spread_settle': spread_settle,
            'data_last5_years': data_last5_years,'historical_sharp':historical_sharp}


def get_intraday_trend_signals(**kwargs):

    ticker = kwargs['ticker']
    date_to = kwargs['date_to']
    datetime_to = cu.convert_doubledate_2datetime(date_to)
    breakout_method = 2

    #print(ticker)

    ticker_head = cmi.get_contract_specs(ticker)['ticker_head']
    contract_multiplier = cmi.contract_multiplier[ticker_head]
    ticker_class = cmi.ticker_class[ticker_head]

    daily_settles = gfp.get_futures_price_preloaded(ticker=ticker)
    daily_settles = daily_settles[daily_settles['settle_date'] <= datetime_to]
    daily_settles['ewma10'] = pd.ewma(daily_settles['close_price'], span=10)
    daily_settles['ewma50'] = pd.ewma(daily_settles['close_price'], span=50)

    if daily_settles['ewma10'].iloc[-1] > daily_settles['ewma50'].iloc[-1]:
        long_term_trend = 1
    else:
        long_term_trend = -1

    date_list = [exp.doubledate_shift_bus_days(double_date=date_to,shift_in_days=1)]
    date_list.append(date_to)

    intraday_data = opUtil.get_aligned_futures_data_intraday(contract_list=[ticker],
                                       date_list=date_list)

    intraday_data['time_stamp'] = [x.to_datetime() for x in intraday_data.index]

    intraday_data['hour_minute'] = [100*x.hour+x.minute for x in intraday_data['time_stamp']]

    end_hour = cmi.last_trade_hour_minute[ticker_head]
    start_hour = cmi.first_trade_hour_minute[ticker_head]

    if ticker_class in ['Ag']:
        start_hour1 = dt.time(0, 45, 0, 0)
        end_hour1 = dt.time(7, 45, 0, 0)
        selection_indx = [x for x in range(len(intraday_data.index)) if
                          ((intraday_data['time_stamp'].iloc[x].time() < end_hour1)
                           and(intraday_data['time_stamp'].iloc[x].time() >= start_hour1)) or
                          ((intraday_data['time_stamp'].iloc[x].time() < end_hour)
                           and(intraday_data['time_stamp'].iloc[x].time() >= start_hour))]

    else:
        selection_indx = [x for x in range(len(intraday_data.index)) if
                          (intraday_data.index[x].to_datetime().time() < end_hour)
                          and(intraday_data.index[x].to_datetime().time() >= start_hour)]

    selected_data = intraday_data.iloc[selection_indx]
    selected_data['mid_p'] = (selected_data['c1']['best_bid_p']+selected_data['c1']['best_ask_p'])/2

    selected_data['ewma100'] = pd.ewma(selected_data['mid_p'], span=100)
    selected_data['ewma25'] = pd.ewma(selected_data['mid_p'], span=25)

    selected_data.reset_index(inplace=True,drop=True)

    datetime_to = cu.convert_doubledate_2datetime(date_to)

    range_start = dt.datetime.combine(datetime_to,dt.time(8,30,0,0))
    range_end = dt.datetime.combine(datetime_to,dt.time(9,0,0,0))

    first_30_minutes = selected_data[(selected_data['time_stamp'] >= range_start)&
                                     (selected_data['time_stamp'] <= range_end)]

    trading_data = selected_data[selected_data['time_stamp'] > range_end]

    trading_data_shifted = trading_data.shift(5)

    range_min = first_30_minutes['mid_p'].min()
    range_max = first_30_minutes['mid_p'].max()

    initial_range = range_max-range_min

    if breakout_method == 1:

        bullish_breakout = trading_data[(trading_data['mid_p'] > range_max)&
                                    (trading_data['mid_p'] < range_max+0.5*initial_range)&
                                    (trading_data_shifted['mid_p']<range_max)&
                                    (trading_data['ewma25'] > range_max)&
                                    (trading_data['mid_p'] > trading_data['ewma100'])]

        bearish_breakout = trading_data[(trading_data['mid_p'] < range_min)&
                                    (trading_data['mid_p'] > range_min-0.5*initial_range)&
                                    (trading_data_shifted['mid_p']>range_min)&
                                    (trading_data['ewma25'] < range_min)&
                                    (trading_data['mid_p'] < trading_data['ewma100'])]
    elif breakout_method == 2:

        bullish_breakout = pd.DataFrame()
        bearish_breakout = pd.DataFrame()

        if long_term_trend > 0:
            bullish_breakout = trading_data[(trading_data['mid_p'] > range_max)&
                                        (trading_data_shifted['mid_p']<range_max)&
                                        (long_term_trend == 1)&
                                        (trading_data['mid_p'] > trading_data['ewma100'])]
        elif long_term_trend < 0:
            bearish_breakout = trading_data[(trading_data['mid_p'] < range_min)&
                                        (trading_data_shifted['mid_p']>range_min)&
                                        (long_term_trend == -1)&
                                        (trading_data['mid_p'] < trading_data['ewma100'])]

    bullish_cross = trading_data[trading_data['mid_p'] > trading_data['ewma100']]
    bearish_cross = trading_data[trading_data['mid_p'] < trading_data['ewma100']]

    end_of_day_price = trading_data['mid_p'].iloc[-1]
    end_of_day_time_stamp = trading_data['time_stamp'].iloc[-1]

    valid_bearish_breakoutQ = False
    valid_bullish_breakoutQ = False
    bearish_breakout_price_entry = np.NaN
    bullish_breakout_price_entry = np.NaN

    if not bearish_breakout.empty:
        if bearish_breakout.index[0]+1 < trading_data.index[-1]:
            if trading_data['mid_p'].loc[bearish_breakout.index[0]+1]>range_min-0.5*initial_range:
                valid_bearish_breakoutQ = True
                bearish_breakout_price_entry = trading_data['mid_p'].loc[bearish_breakout.index[0]+1]
                bearish_breakout_time_stamp = trading_data['time_stamp'].loc[bearish_breakout.index[0]+1]

    if not bullish_breakout.empty:
        if bullish_breakout.index[0]+1<trading_data.index[-1]:
            if trading_data['mid_p'].loc[bullish_breakout.index[0]+1]<range_max+0.5*initial_range:
                valid_bullish_breakoutQ = True
                bullish_breakout_price_entry = trading_data['mid_p'].loc[bullish_breakout.index[0]+1]
                bullish_breakout_time_stamp = trading_data['time_stamp'].loc[bullish_breakout.index[0]+1]

    stop_loss = (range_max-range_min)*contract_multiplier

    pnl_list = []
    direction_list = []
    entry_time_list = []
    exit_time_list = []
    entry_price_list = []
    exit_price_list = []
    daily_trade_no_list = []
    exit_type_list = []
    ticker_list = []

    if valid_bearish_breakoutQ:

        direction_list.append(-1)
        entry_time_list.append(bearish_breakout_time_stamp)
        entry_price_list.append(bearish_breakout_price_entry)

        daily_pnl = bearish_breakout_price_entry-end_of_day_price
        exit_price = end_of_day_price
        exit_type = 'eod'
        exit_time = end_of_day_time_stamp
        daily_trade_no = 1

        #bullish_cross_stop_frame = bullish_cross[(bullish_cross['time_stamp'] > bearish_breakout_time_stamp)]

        #if (not bullish_cross_stop_frame.empty) and (bullish_cross_stop_frame.index[0]+1<trading_data.index[-1]):
        #    daily_pnl = bearish_breakout_price_entry-trading_data['mid_p'].loc[bullish_cross_stop_frame.index[0]+1]
        #    exit_price = trading_data['mid_p'].loc[bullish_cross_stop_frame.index[0]+1]
        #    exit_type = 'oso'
        #    exit_time = trading_data['time_stamp'].loc[bullish_cross_stop_frame.index[0]+1]

        #if valid_bullish_breakoutQ:
        #    if bullish_breakout_time_stamp>bearish_breakout_time_stamp:
        #        if bullish_breakout_time_stamp<exit_time:
        #            daily_pnl = bearish_breakout_price_entry-bullish_breakout_price_entry
        #            exit_price = bullish_breakout_price_entry
        #            exit_type = 'fso'
        #            exit_time = bullish_breakout_time_stamp
        #    else:
        #        daily_trade_no = 2

        exit_time_list.append(exit_time)
        exit_type_list.append(exit_type)
        daily_trade_no_list.append(daily_trade_no)
        pnl_list.append(daily_pnl)
        exit_price_list.append(exit_price)
        ticker_list.append(ticker)

    if valid_bullish_breakoutQ:
        direction_list.append(1)
        entry_time_list.append(bullish_breakout_time_stamp)
        entry_price_list.append(bullish_breakout_price_entry)

        daily_pnl = end_of_day_price-bullish_breakout_price_entry
        exit_price = end_of_day_price
        exit_type = 'eod'
        exit_time = end_of_day_time_stamp
        daily_trade_no = 1

        bearish_cross_stop_frame = bearish_cross[(bearish_cross['time_stamp'] > bullish_breakout_time_stamp)]

        #if (not bearish_cross_stop_frame.empty) and (bearish_cross_stop_frame.index[0]+1 < trading_data.index[-1]):
        #    daily_pnl = trading_data['mid_p'].loc[bearish_cross_stop_frame.index[0]+1]-bullish_breakout_price_entry
        #    exit_price = trading_data['mid_p'].loc[bearish_cross_stop_frame.index[0]+1]
        #    exit_type = 'oso'
        #    exit_time = trading_data['time_stamp'].loc[bearish_cross_stop_frame.index[0]+1]

        #if valid_bearish_breakoutQ:
        #    if bearish_breakout_time_stamp>bullish_breakout_time_stamp:
        #        if bearish_breakout_time_stamp<exit_time:
        #            daily_pnl = bearish_breakout_price_entry-bullish_breakout_price_entry
        #            exit_price = bearish_breakout_price_entry
        #            exit_type = 'fso'
        #            exit_time = bearish_breakout_time_stamp
        #    else:
         #       daily_trade_no = 2

        exit_time_list.append(exit_time)
        exit_type_list.append(exit_type)
        daily_trade_no_list.append(daily_trade_no)
        pnl_list.append(daily_pnl)
        exit_price_list.append(exit_price)
        ticker_list.append(ticker)


    pnl_frame = pd.DataFrame.from_items([('ticker', ticker_list),
                                         ('ticker_head',ticker_head),
                                    ('direction', direction_list),
                                         ('entry_price', entry_price_list),
                                         ('exit_price', exit_price_list),
                                    ('pnl', pnl_list),
                                    ('entry_time', entry_time_list),
                                    ('exit_time', exit_time_list),
                                   ('exit_type', exit_type_list),
                                    ('daily_trade_no', daily_trade_no_list)])

    pnl_frame['pnl'] = pnl_frame['pnl']*contract_multiplier

    return {'intraday_data': selected_data, 'range_min': range_min, 'range_max':range_max,'pnl_frame':pnl_frame,'stop_loss':stop_loss}


def get_intraday_outright_covariance(**kwargs):

    date_to = kwargs['date_to']
    num_days_back_4intraday = 20

    liquid_futures_frame = cl.get_liquid_outright_futures_frame(settle_date=date_to)

    date_list = [exp.doubledate_shift_bus_days(double_date=date_to,shift_in_days=x) for x in reversed(range(1,num_days_back_4intraday))]
    date_list.append(date_to)
    intraday_data = opUtil.get_aligned_futures_data_intraday(contract_list=liquid_futures_frame['ticker'].values,date_list=date_list)
    intraday_data['time_stamp'] = [x.to_datetime() for x in intraday_data.index]
    intraday_data['hour_minute'] = [100*x.hour+x.minute for x in intraday_data['time_stamp']]
    intraday_data = intraday_data.resample('30min',how='last')
    intraday_data = intraday_data[(intraday_data['hour_minute'] >= 830) &
                                  (intraday_data['hour_minute'] <= 1200)]
    intraday_data_shifted = intraday_data.shift(1)
    selection_indx = intraday_data['hour_minute']-intraday_data_shifted['hour_minute'] > 0

    num_contracts = len(liquid_futures_frame.index)

    diff_frame = pd.DataFrame()

    for i in range(num_contracts):

        mid_p = (intraday_data['c' + str(i+1)]['best_bid_p']+
                         intraday_data['c' + str(i+1)]['best_ask_p'])/2
        mid_p_shifted = (intraday_data_shifted['c' + str(i+1)]['best_bid_p']+
                                 intraday_data_shifted['c' + str(i+1)]['best_ask_p'])/2

        diff_frame[liquid_futures_frame['ticker_head'].iloc[i]] = (mid_p-mid_p_shifted)*cmi.contract_multiplier[liquid_futures_frame['ticker_head'].iloc[i]]

    diff_frame = diff_frame[selection_indx]

    return {'cov_matrix': diff_frame.cov(),
     'cov_data_integrity': 100*diff_frame.notnull().sum().sum()/(len(diff_frame.columns)*20*6)}










