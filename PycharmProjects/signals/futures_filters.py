__author__ = 'kocat_000'

import shared.utils as su
import numpy as np


def get_futures_butterfly_filters(**kwargs):

    data_frame_input = kwargs['data_frame_input']
    filter_list = kwargs['filter_list']

    selection_indx = [False]*len(data_frame_input.index)

    if 'long1' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] <= -1.2) & (data_frame_input['QF'] <= 12))

    if 'short1' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] >= 0.6) & (data_frame_input['QF'] >= 85))

    if 'long2' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] <= -0.6) & (data_frame_input['QF'] <= 12))

    if 'short2' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] >= 0.6) & (data_frame_input['QF'] >= 85))

    if 'long3' in filter_list:
        selection_indx = selection_indx|((data_frame_input['Q'] <= 15) & (data_frame_input['QF'] <= 40) &
                                         (data_frame_input['recent_5day_pnl'] > 2*data_frame_input['downside']))

    if 'short3' in filter_list:
        selection_indx = selection_indx|((data_frame_input['Q'] >= 85) & (data_frame_input['QF'] >= 60) &
                                         (data_frame_input['recent_5day_pnl'] < 2*data_frame_input['upside']))

    if 'long4' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] <= -1.2) &
                                         (data_frame_input['QF'] <= 12) &
                                         (data_frame_input['second_spread_weight_1'] > 0.5) &
                                         (data_frame_input['second_spread_weight_1'] < 1.5))

    if 'short4' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] >= 0.6) &
                                         (data_frame_input['QF'] >= 85) &
                                         (data_frame_input['second_spread_weight_1'] > 0.5) &
                                         (data_frame_input['second_spread_weight_1'] < 1.5))

    if 'long5' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] <= -1.2) &
                                         (data_frame_input['QF'] <= 12) &
                                         (data_frame_input['tickerHead'] != 'S') &
                                         (data_frame_input['tickerHead'] != 'RB'))

    if 'short5' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] >= 0.6) &
                                         (data_frame_input['QF'] >= 85) &
                                           (data_frame_input['tickerHead'] != 'S') &
                                         (data_frame_input['tickerHead'] != 'RB'))

    if 'long6' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] <= -1.2) &
                                         (data_frame_input['QF'] <= 12) &
                                         (data_frame_input['mean_reversion_signif'] == True))

    if 'short6' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] >= 0.6) &
                                         (data_frame_input['QF'] >= 85) &
                                         (data_frame_input['mean_reversion_signif'] == True))

    if 'long7' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] <= -1.2) & (data_frame_input['QF'] <= 12) & (data_frame_input['tickerHead'].isin(['CL', 'B'])) & (data_frame_input['z6'] <= -0.6))|\
                                        ((data_frame_input['z1'] <= -1.2) &(data_frame_input['QF'] <= 12) & (np.logical_not(data_frame_input['tickerHead'].isin(['CL', 'B']))))

    if 'short7' in filter_list:
        selection_indx = selection_indx|((data_frame_input['z1'] >= 0.6) &(data_frame_input['QF'] >= 85)& (data_frame_input['tickerHead'].isin(['CL', 'B'])) & (data_frame_input['z6'] >= 0.3))|\
                                        ((data_frame_input['z1'] >= 0.6) &(data_frame_input['QF'] >= 85)& (np.logical_not(data_frame_input['tickerHead'].isin(['CL', 'B']))))


    return {'selected_frame': data_frame_input[selection_indx],'selection_indx': selection_indx }

def get_spread_carry_filters(**kwargs):

    data_frame_input = kwargs['data_frame_input']
    filter_list = kwargs['filter_list']

    selection_indx = [False]*len(data_frame_input.index)

    if 'long1' in filter_list:
        selection_indx = selection_indx|((data_frame_input['q_carry'] >= 19) &
                                         ([x not in ['CL','B','ED'] for x in data_frame_input['tickerHead']]))

    if 'short1' in filter_list:
        selection_indx = selection_indx|((data_frame_input['q_carry'] <= -9) &
                                         ([x not in ['CL','B','ED'] for x in data_frame_input['tickerHead']]))

        selection_indx = selection_indx|((data_frame_input['reward_risk'] <= -0.06) &
                                         ([x in ['CL','B','ED'] for x in data_frame_input['tickerHead']]))

    return {'selected_frame': data_frame_input[selection_indx],'selection_indx': selection_indx }


def get_curve_pca_filters(**kwargs):

    data_frame_input = kwargs['data_frame_input']
    filter_list = kwargs['filter_list']

    selection_indx = [False]*len(data_frame_input.index)

    #median_factor_load2 = data_frame_input['factor_load2'].median()

    #if median_factor_load2 > 0:
    #    daily_report_filtered = data_frame_input[data_frame_input['factor_load2'] >= 0]
    #else:
    #    daily_report_filtered = data_frame_input[data_frame_input['factor_load2'] <= 0]

    daily_report_filtered = data_frame_input[(data_frame_input['tr_dte_front'] > 80) & (data_frame_input['monthSpread'] == 1)]

    daily_report_filtered.sort_values('z', ascending=True, inplace=True)
    num_contract_4side = round(len(daily_report_filtered.index)/4)

    if 'long1' in filter_list:
        selected_trades = daily_report_filtered.iloc[:num_contract_4side]
        selection_indx = su.list_or(selection_indx, su.list_and([x in selected_trades['ticker1'].values for x in data_frame_input['ticker1'].values],
                                                                [x == 1 for x in data_frame_input['monthSpread'].values]))
    if 'short1' in filter_list:
        selected_trades = daily_report_filtered.iloc[-num_contract_4side:]
        selection_indx = su.list_or(selection_indx, su.list_and([x in selected_trades['ticker1'].values for x in data_frame_input['ticker1'].values],
                                                                [x == 1 for x in data_frame_input['monthSpread'].values]))

    return {'selected_frame': data_frame_input[selection_indx],'selection_indx': selection_indx }





