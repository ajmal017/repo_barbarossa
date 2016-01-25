__author__ = 'kocat_000'

import pandas as pd
import numpy as np
import opportunity_constructs.curve_pca as cpc
import contract_utilities.contract_meta_info as cmi
pd.options.mode.chained_assignment = None  # default='warn'

def backtest_curve_pca(**kwargs):

    ticker_head = kwargs['ticker_head']
    date_list = kwargs['date_list']

    if 'use_existing_filesQ' in kwargs.keys():
        use_existing_filesQ = kwargs['use_existing_filesQ']
    else:
        use_existing_filesQ = True

    report_results_list = []
    success_indx = []

    contract_multiplier = cmi.contract_multiplier[ticker_head]

    for date_to in date_list:

        report_out = cpc.get_curve_pca_report(ticker_head=ticker_head,date_to=date_to,use_existing_filesQ=use_existing_filesQ)
        success_indx.append(report_out['success'])

        if report_out['success']:
            report_results_list.append(report_out['pca_results'])


    good_dates = [date_list[i] for i in range(len(date_list)) if success_indx[i]]

    total_pnl_list = []
    z_score_list = []
    residual_list = []
    num_contract_list = []
    short_side_weight_list = []

    for i in range(len(good_dates)):

        daily_report = report_results_list[i]
        median_factor_load2 = daily_report['factor_load2'].median()

        if median_factor_load2>0:
            daily_report_filtered = daily_report[daily_report['factor_load2']>=0]
        else:
            daily_report_filtered = daily_report[daily_report['factor_load2']<=0]

        daily_report_filtered.sort('z',ascending=True,inplace=True)
        num_contract_4side = round(len(daily_report_filtered.index)/4)
        long_side = daily_report_filtered.iloc[:num_contract_4side]
        short_side = daily_report_filtered.iloc[-num_contract_4side:]
        short_side_weight = long_side['factor_load1'].sum()/short_side['factor_load1'].sum()

        z_score_list.append(np.nanmean(short_side['z'])-np.nanmean(long_side['z']))

        if any(np.isnan(long_side['change5'])) or any(np.isnan(short_side['change5'])):
            total_pnl_list.append(np.NAN)
        else:
            total_pnl_list.append(np.nanmean(long_side['change5'])-short_side_weight*np.nanmean(short_side['change5']))

        residual_list.append(np.nanmean(short_side['residuals'])-np.nanmean(long_side['residuals']))
        num_contract_list.append(num_contract_4side)
        short_side_weight_list.append(short_side_weight)

    return {'pnl_frame': pd.DataFrame.from_items([('settle_date',good_dates),
                                                   ('num_contracts',num_contract_list),
                                                   ('z',z_score_list),
                                                   ('residual',residual_list),
                                                  ('short_side_weight',short_side_weight_list),
                                                   ('pnl',[x*contract_multiplier for x in total_pnl_list])]),
            'report_results_list': report_results_list}



