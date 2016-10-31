
import my_sql_routines.my_sql_utilities as msu
import ta.strategy as ts
import ta.pnl as tpnl
import shared.converters as sc
import shared.calendar_utilities as cu
import signals.futures_signals as fs
import signals.options_filters as of
import contract_utilities.expiration as exp
import pandas as pd
import numpy as np
import contract_utilities.contract_meta_info as cmi
import get_price.get_futures_price as gfp
import opportunity_constructs.spread_carry as osc
import opportunity_constructs.vcs as ovcs
import ta.strategy_greeks as sg
import ta.portfolio_manager as tpm


def get_results_4strategy(**kwargs):

    signal_input = dict()

    if 'futures_data_dictionary' in kwargs.keys():
        signal_input['futures_data_dictionary'] = kwargs['futures_data_dictionary']

    if 'date_to' in kwargs.keys():
        date_to = kwargs['date_to']
    else:
        date_to = exp.doubledate_shift_bus_days()

    if 'datetime5_years_ago' in kwargs.keys():
        signal_input['datetime5_years_ago'] = kwargs['datetime5_years_ago']

    if 'strategy_info_output' in kwargs.keys():
        strategy_info_output = kwargs['strategy_info_output']
    else:
        strategy_info_output = ts.get_strategy_info_from_alias(**kwargs)

    con = msu.get_my_sql_connection(**kwargs)

    strategy_info_dict = sc.convert_from_string_to_dictionary(string_input=strategy_info_output['description_string'])
    #print(kwargs['alias'])

    strategy_class = strategy_info_dict['strategy_class']

    pnl_frame = tpm.get_daily_pnl_snapshot(as_of_date=date_to)
    pnl_frame = pnl_frame[pnl_frame['alias']==kwargs['alias']]
    strategy_position = ts.get_net_position_4strategy_alias(alias=kwargs['alias'],as_of_date=date_to)

    if strategy_class == 'futures_butterfly':

        ticker_head = cmi.get_contract_specs(strategy_info_dict['ticker1'])['ticker_head']
        if not strategy_position.empty:
            total_contracts2trade = strategy_position['qty'].abs().sum()
            t_cost = cmi.t_cost[ticker_head]
        QF_initial = float(strategy_info_dict['QF'])
        z1_initial = float(strategy_info_dict['z1'])

        bf_signals_output = fs.get_futures_butterfly_signals(ticker_list=[strategy_info_dict['ticker1'],
                                                                          strategy_info_dict['ticker2'],
                                                                          strategy_info_dict['ticker3']],
                                          aggregation_method=int(strategy_info_dict['agg']),
                                          contracts_back=int(strategy_info_dict['cBack']),
                                          date_to=date_to,**signal_input)

        aligned_output = bf_signals_output['aligned_output']
        current_data = aligned_output['current_data']
        holding_tr_dte = int(strategy_info_dict['trDte1'])-current_data['c1']['tr_dte']

        if strategy_position.empty:
            recommendation = 'CLOSE'
        elif (z1_initial>0)&(holding_tr_dte > 5) &\
                (bf_signals_output['qf']<QF_initial-20)&\
                (pnl_frame['total_pnl'].iloc[0] > 3*t_cost*total_contracts2trade):
            recommendation = 'STOP'
        elif (z1_initial<0)&(holding_tr_dte > 5) &\
                (bf_signals_output['qf']>QF_initial+20)&\
                (pnl_frame['total_pnl'].iloc[0] > 3*t_cost*total_contracts2trade):
            recommendation = 'STOP'
        elif (current_data['c1']['tr_dte'] < 35)&\
            (pnl_frame['total_pnl'].iloc[0] > 3*t_cost*total_contracts2trade):
            recommendation = 'STOP'
        elif (current_data['c1']['tr_dte'] < 35)&\
            (pnl_frame['total_pnl'].iloc[0] < 3*t_cost*total_contracts2trade):
            recommendation = 'WINDDOWN'
        else:
            recommendation = 'HOLD'

        result_output = {'success': True,'ticker_head': ticker_head,
                        'QF_initial':QF_initial,'z1_initial': z1_initial,
                        'QF': bf_signals_output['qf'],'z1': bf_signals_output['zscore1'],
                        'short_tr_dte': current_data['c1']['tr_dte'],
                        'holding_tr_dte': holding_tr_dte,
                        'second_spread_weight': bf_signals_output['second_spread_weight_1'],'recommendation': recommendation}

    elif strategy_class == 'spread_carry':
        trades4_strategy = ts.get_trades_4strategy_alias(**kwargs)
        grouped = trades4_strategy.groupby('ticker')
        net_position = pd.DataFrame()
        net_position['ticker'] = (grouped['ticker'].first()).values
        net_position['qty'] = (grouped['trade_quantity'].sum()).values
        net_position = net_position[net_position['qty'] != 0]

        net_position['ticker_head'] = [cmi.get_contract_specs(x)['ticker_head'] for x in net_position['ticker']]
        price_output = [gfp.get_futures_price_preloaded(ticker=x, settle_date=date_to) for x in net_position['ticker']]
        net_position['tr_dte'] = [x['tr_dte'].values[0] for x in price_output]

        results_frame = pd.DataFrame()
        unique_tickerhead_list = net_position['ticker_head'].unique()
        results_frame['tickerHead'] = unique_tickerhead_list
        results_frame['ticker1'] = [None]*len(unique_tickerhead_list)
        results_frame['ticker2'] = [None]*len(unique_tickerhead_list)
        results_frame['qty'] = [None]*len(unique_tickerhead_list)
        results_frame['pnl'] = [None]*len(unique_tickerhead_list)
        results_frame['downside'] = [None]*len(unique_tickerhead_list)
        results_frame['indicator'] = [None]*len(unique_tickerhead_list)
        results_frame['timeHeld'] = [None]*len(unique_tickerhead_list)
        results_frame['recommendation'] = [None]*len(unique_tickerhead_list)

        spread_carry_output = osc.generate_spread_carry_sheet_4date(report_date=date_to)
        spread_report = spread_carry_output['spread_report']

        pnl_output = tpnl.get_strategy_pnl(**kwargs)
        pnl_per_tickerhead = pnl_output['pnl_per_tickerhead']

        for i in range(len(unique_tickerhead_list)):

            net_position_per_tickerhead = net_position[net_position['ticker_head'] == unique_tickerhead_list[i]]
            net_position_per_tickerhead.sort('tr_dte',ascending=True,inplace=True)

            selected_spread = spread_report[(spread_report['ticker1'] == net_position_per_tickerhead['ticker'].values[0]) &
                             (spread_report['ticker2'] == net_position_per_tickerhead['ticker'].values[1])]

            results_frame['ticker1'][i] = selected_spread['ticker1'].values[0]
            results_frame['ticker2'][i] = selected_spread['ticker2'].values[0]
            results_frame['qty'][i] = net_position_per_tickerhead['qty'].values[0]

            selected_trades = trades4_strategy[trades4_strategy['ticker'] == results_frame['ticker1'].values[i]]

            price_output = gfp.get_futures_price_preloaded(ticker=results_frame['ticker1'].values[i],
                                                           settle_date=pd.to_datetime(selected_trades['trade_date'].values[0]))

            results_frame['timeHeld'][i] = price_output['tr_dte'].values[0]-net_position_per_tickerhead['tr_dte'].values[0]
            results_frame['pnl'][i] = pnl_per_tickerhead[unique_tickerhead_list[i]].sum()

            if unique_tickerhead_list[i] in ['CL', 'B', 'ED']:
                results_frame['indicator'][i] = selected_spread['reward_risk'].values[0]

                if results_frame['qty'][i] > 0:
                    results_frame['recommendation'][i] = 'STOP'
                elif results_frame['qty'][i] < 0:
                    if results_frame['indicator'][i] > -0.06:
                        results_frame['recommendation'][i] = 'STOP'
                    else:
                        results_frame['recommendation'][i] = 'HOLD'
            else:

                results_frame['indicator'][i] = selected_spread['q_carry'].values[0]

                if results_frame['qty'][i] > 0:
                    if results_frame['indicator'][i] < 19:
                        results_frame['recommendation'][i] = 'STOP'
                    else:
                        results_frame['recommendation'][i] = 'HOLD'

                elif results_frame['qty'][i] < 0:
                    if results_frame['indicator'][i] > -9:
                        results_frame['recommendation'][i] = 'STOP'
                    else:
                        results_frame['recommendation'][i] = 'HOLD'

            if results_frame['qty'][i] > 0:
                results_frame['downside'][i] = selected_spread['downside'].values[0]*results_frame['qty'][i]
            else:
                results_frame['downside'][i] = selected_spread['upside'].values[0]*results_frame['qty'][i]

        return {'success': True, 'results_frame': results_frame}

    elif strategy_class == 'vcs':

        greeks_out = sg.get_greeks_4strategy_4date(alias=kwargs['alias'], as_of_date=date_to)
        ticker_portfolio = greeks_out['ticker_portfolio']

        if ticker_portfolio.empty:
            min_tr_dte = np.NaN
            result_output = {'success': False, 'net_oev': np.NaN, 'net_theta': np.NaN, 'long_short_ratio': np.NaN,
                         'recommendation': 'EMPTY', 'last_adjustment_days_ago': np.NaN,
                         'min_tr_dte': np.NaN, 'long_oev': np.NaN, 'short_oev': np.NaN, 'favQMove': np.NaN}
        else:
            min_tr_dte = min([exp.get_days2_expiration(ticker=x,date_to=date_to,instrument='options',con=con)['tr_dte'] for x in ticker_portfolio['ticker']])

            net_oev = ticker_portfolio['total_oev'].sum()
            net_theta = ticker_portfolio['theta'].sum()

            long_portfolio = ticker_portfolio[ticker_portfolio['total_oev'] > 0]
            short_portfolio = ticker_portfolio[ticker_portfolio['total_oev'] < 0]
            short_portfolio['total_oev']=abs(short_portfolio['total_oev'])

            long_oev = long_portfolio['total_oev'].sum()
            short_oev = short_portfolio['total_oev'].sum()

            if (not short_portfolio.empty) & (not long_portfolio.empty):
                long_short_ratio = 100*long_oev/short_oev

                long_portfolio.sort('total_oev', ascending=False, inplace=True)
                short_portfolio.sort('total_oev', ascending=False, inplace=True)

                long_ticker = long_portfolio['ticker'].iloc[0]
                short_ticker = short_portfolio['ticker'].iloc[0]

                long_contract_specs = cmi.get_contract_specs(long_ticker)
                short_contract_specs = cmi.get_contract_specs(short_ticker)

                if 12*long_contract_specs['ticker_year']+long_contract_specs['ticker_month_num'] < \
                                        12*short_contract_specs['ticker_year']+short_contract_specs['ticker_month_num']:
                    front_ticker = long_ticker
                    back_ticker = short_ticker
                    direction = 'long'
                else:
                    front_ticker = short_ticker
                    back_ticker = long_ticker
                    direction = 'short'

                if 'vcs_output' in kwargs.keys():
                    vcs_output = kwargs['vcs_output']
                else:
                    vcs_output = ovcs.generate_vcs_sheet_4date(date_to=date_to)

                vcs_pairs = vcs_output['vcs_pairs']
                selected_result = vcs_pairs[(vcs_pairs['ticker1'] == front_ticker) & (vcs_pairs['ticker2'] == back_ticker)]

                if selected_result.empty:
                    favQMove = np.NaN
                else:
                    current_Q = selected_result['Q'].iloc[0]
                    q_limit = of.get_vcs_filter_values(product_group=long_contract_specs['ticker_head'],
                                                   filter_type='tickerHead',direction=direction,indicator='Q')
                    if direction == 'long':
                        favQMove = current_Q-q_limit
                    elif direction == 'short':
                        favQMove = q_limit-current_Q
            else:
                long_short_ratio = np.NaN
                favQMove = np.NaN

            trades_frame = ts.get_trades_4strategy_alias(**kwargs)
            trades_frame_options = trades_frame[trades_frame['instrument'] == 'O']
            last_adjustment_days_ago = len(exp.get_bus_day_list(date_to=date_to,datetime_from=max(trades_frame_options['trade_date']).to_datetime()))

            if favQMove >= 10 and last_adjustment_days_ago > 10:
                recommendation = 'STOP-ratio normalized'
            elif min_tr_dte<25:
                recommendation = 'STOP-close to expiration'
            elif np.isnan(long_short_ratio):
                recommendation = 'STOP-not a proper calendar'
            else:
                if long_short_ratio < 80:
                    if favQMove < 0:
                        recommendation = 'buy_options_to_grow'
                    else:
                        recommendation = 'buy_options_to_shrink'
                elif long_short_ratio > 120:
                    if favQMove < 0:
                        recommendation = 'sell_options_to_grow'
                    else:
                        recommendation = 'sell_options_to_shrink'
                else:
                    recommendation = 'HOLD'

            result_output = {'success': True, 'net_oev': net_oev, 'net_theta': net_theta, 'long_short_ratio': long_short_ratio,
                         'recommendation': recommendation, 'last_adjustment_days_ago': last_adjustment_days_ago,
                         'min_tr_dte': min_tr_dte, 'long_oev': long_oev, 'short_oev': short_oev, 'favQMove': favQMove}

    else:
        result_output = {'success': False}

    if 'con' not in kwargs.keys():
        con.close()

    return result_output



