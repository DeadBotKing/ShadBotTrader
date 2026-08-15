from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata

from src.indicators.StochAstic.StochAstic import StochAstic
from src.indicators.StochAstic.Parameters import Parameters as StochAsticParameters
from src.indicators.StochAstic.Config import Config as StochAsticConfig

from src.indicators.MACD.MACD import MACD
from src.indicators.MACD.Parameters import Parameters as MacdParameters
from src.indicators.MACD.Config import Config as MacdConfig

from src.indicators.RSI.RSI import RSI
from src.indicators.RSI.Parameters import Parameters as RsiParameters
from src.indicators.RSI.Config import Config as RsiConfig

from src.utils.Tools.DataChanger import DataChanger

import mplfinance as mpf_1H
import mplfinance as mpf_5M

import matplotlib.pyplot as plt

import pandas as pd
import numpy as np

import os

symbol = 'XAUUSD_i'
applyto = 'close'
number_data_5M = 'all'
number_data_1H = 'all'
start_point = 10000
coef_money = 20
money = 100
spred = 0.0004
percent = 0
tp_pr_eq = 0
st_pr_eq = 0


def BuyChecker(dataset_5M_real, tp, st, candle_index, money, coef_money, spred):

	if (
		dataset_5M_real['high'][candle_index] * (1 + spred) >= tp or
		dataset_5M_real['low'][candle_index] <= st
		):
		flag = 'no_flag'
		tp_pr = 0
		st_pr = 0

		return money, flag, tp_pr, st_pr, candle_index

	if (len(np.where(((dataset_5M_real['high'][(candle_index):-1].values) >= tp))[0]) > 1):
			index_tp =	candle_index + min(
											np.where(
														(
															(dataset_5M_real['high'][(candle_index):-1].values) >= tp
														)
													)[0] 
											)

	elif (len(np.where(((dataset_5M_real['high'][(candle_index):-1].values) >= tp))[0]) == 1):
		index_tp =	candle_index + np.where(
												(
													(dataset_5M_real['high'][(candle_index):-1].values) >= tp
												)
											)[0][0] 

	else:
		index_tp = -1
		tp_pr = 0

	if (len(np.where(((dataset_5M_real['low'][(candle_index):-1].values) <= st))[0]) > 1):
		index_st =	candle_index + min(
									np.where(
												(
													(dataset_5M_real['low'][(candle_index):-1].values) <= st
												)
											)[0]
									)

	elif (len(np.where(((dataset_5M_real['low'][(candle_index):-1].values) <= st))[0]) == 1):
		index_st =	candle_index + np.where(
											(
												(dataset_5M_real['low'][(candle_index):-1].values) <= st
											)
										)[0][0]

	else:
		index_st = -1
		st_pr = 0

	loc_end_5M_price = candle_index
	if (
		index_tp < index_st and
		index_tp != -1
		):

		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_tp]))/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['high'][index_tp] - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		if dataset_5M_real['high'][index_tp] > tp: tp_pr = ((tp - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		flag = 'tp'

	elif (
		index_tp != -1 and
		index_st == -1
		):
		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_tp]))/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['high'][index_tp] - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		if dataset_5M_real['high'][index_tp] > tp: tp_pr = ((tp - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100


		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		flag = 'tp'

	elif (
		index_st < index_tp and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_st])/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_st]) - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		if dataset_5M_real['low'][index_st] < st: st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - st)/dataset_5M_real['low'][loc_end_5M_price]) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		flag = 'st'

	elif (
		index_tp == -1 and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_st])/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_st]) - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100
		
		if dataset_5M_real['low'][index_st] < st: st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - st)/dataset_5M_real['low'][loc_end_5M_price]) * 100

		my_money = money
		coef_money = self.elements['Tester_coef_money']

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		flag = 'st'

	if index_st == index_tp:

		if index_st != -1:
			st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_st])/dataset_5M_real['low'][loc_end_5M_price]) * 100
			tp_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_st]) - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100
			
			if dataset_5M_real['low'][index_st] < st: st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - st)/dataset_5M_real['low'][loc_end_5M_price]) * 100

			my_money = money
			coef_money = self.elements['Tester_coef_money']

			if my_money >=100:
				lot = int(my_money/100) * coef_money
			else:
				lot = coef_money

			if lot > 2000: lot = 2000

			my_money = my_money - (lot * st_pr)

			money = my_money

			candle_index = index_st

			flag = 'st'

		else:
			flag = 'no_flag'
			tp_pr = 0
			st_pr = 0

	return money, flag, tp_pr, st_pr, candle_index

def SellChecker(dataset_5M_real, tp, st, candle_index, money, coef_money, spred):

	loc_end_5M_price = candle_index

	if (
		dataset_5M_real['high'][loc_end_5M_price] * (1 + spred) >= st or
		dataset_5M_real['low'][loc_end_5M_price] <= tp 
		):

		flag = 'no_flag'
		tp_pr = 0
		st_pr = 0

		return money, flag, tp_pr, st_pr, candle_index

	

	#*************** Finding Take Profit:

	if (len(np.where(((dataset_5M_real['low'][(loc_end_5M_price):-1].values * (1 + spred)) <= tp))[0]) > 1):
		index_tp =	loc_end_5M_price + min(
									np.where(
												(
													(dataset_5M_real['low'][(loc_end_5M_price):-1].values) * (1 + spred) <= tp
												)
											)[0] 
									)

	elif (len(np.where(((dataset_5M_real['low'][(loc_end_5M_price):-1].values * (1 + spred)) <= tp))[0]) == 1):
		index_tp =	loc_end_5M_price + np.where(
											(
												(dataset_5M_real['low'][(loc_end_5M_price):-1].values * (1 + spred)) <= tp
											)
										)[0][0] 

	else:
		index_tp = -1
		tp_pr = 0
	#///////////////////////////////

	#************ Finding Stop Loss:

	if (len(np.where(((dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st))[0]) > 1):
		index_st =	loc_end_5M_price + min(
									np.where(
												(
													(dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st
												)
											)[0]
									)

	elif (len(np.where(((dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st))[0]) == 1):
		index_st =	loc_end_5M_price + np.where(
											(
												(dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st
											)
										)[0][0]

	else:
		index_st = -1
		st_pr = 0

	if (
		index_tp < index_st and
		index_tp != -1
		):

		st_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_tp]) - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_tp])/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		if dataset_5M_real['low'][index_tp] < tp: tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - tp)/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		# print('tp = ', top_prim, ' ', down_prim)

		flag = 'tp'

	elif (
		index_tp != -1 and
		index_st == -1
		):
		st_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_tp]) - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_tp])/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		if dataset_5M_real['low'][index_tp] < tp: tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - tp)/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		# print('tp = ', top_prim, ' ', down_prim)

		flag = 'tp'

	elif (
		index_st < index_tp and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['high'][index_st] - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_st]))/(dataset_5M_real['low'][loc_end_5M_price])) * 100
		
		if dataset_5M_real['high'][index_st] > st: st_pr = ((st - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		# print('st = ', signals['pattern_day'][loc_end_5M], ' ', signals['time_high_front'][loc_end_5M].hour)

		flag = 'st'

	elif (
		index_tp == -1 and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['high'][index_st] - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_st]))/(dataset_5M_real['low'][loc_end_5M_price])) * 100
		
		if dataset_5M_real['high'][index_st] > st: st_pr = ((st - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		# print('st = ', signals['pattern_day'][loc_end_5M], ' ', signals['time_high_front'][loc_end_5M].hour)

		flag = 'st'

	if index_st == index_tp:

		if index_st != -1:
			st_pr = ((dataset_5M_real['high'][index_st] - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
			tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_st]))/(dataset_5M_real['low'][loc_end_5M_price])) * 100
			
			if dataset_5M_real['high'][index_st] > st: st_pr = ((st - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
			
			my_money = money

			if my_money >=100:
				lot = int(my_money/100) * coef_money
			else:
				lot = coef_money

			if lot > 2000: lot = 2000

			my_money = my_money - (lot * st_pr)

			money = my_money

			candle_index = index_st

			# print('st = ', signals['pattern_day'][loc_end_5M], ' ', signals['time_high_front'][loc_end_5M].hour)

			flag = 'st'

		else:
			flag = 'no_flag'
			tp_pr = 0
			st_pr = 0

	return money, flag, tp_pr, st_pr, candle_index

loging = getdata()
# loging.account_name = 'ahmadipc'
# loging.initilizer()
# loging.login()

dataset_5M, dataset_1H = loging.readall(symbol = symbol, number_5M = number_data_5M, number_1H = number_data_1H)

# parameters.elements['dataset_5M'] = loging.getone(timeframe = '5M', number = number_data_5M, symbol = 'XAUUSD_i')
# parameters.elements['dataset_1H'] = loging.getone(timeframe = '1H', number = 4000, symbol = 'XAUUSD_i')

# dataset_5M_real = loging.getone(timeframe = '5M', number = number_data_5M, symbol = 'XAUUSD_i')
dataset_5M_real, _ = loging.readall(symbol = symbol, number_5M = 'all', number_1H = 0)
dataset_5M_real = dataset_5M_real[symbol]

# dataset_5M[symbol]['index'] = dataset_5M[symbol].index
# dataset_5M[symbol].index = dataset_5M[symbol]['time']
# dataset_5M[symbol] = dataset_5M[symbol].resample('70T').last()
# dataset_5M[symbol].index = dataset_5M[symbol]['index']
# dataset_5M[symbol] = dataset_5M[symbol].drop(columns = 'index').dropna()

# dataset_5M[symbol] = dataset_5M[symbol].reset_index(inplace = False)

# print(dataset_5M[symbol])

# sys.exit()

data_changer = DataChanger()

macd_parameters = MacdParameters()
macd_config = MacdConfig()

rsi_parameters = RsiParameters()
rsi_config = RsiConfig()

stochastic_parameters = StochAsticParameters()
stochastic_config = StochAsticConfig()

macd_parameters.elements['dataset_5M'] = dataset_5M
macd_parameters.elements['dataset_1H'] = dataset_1H
macd_parameters.elements['symbol'] = symbol

rsi_parameters.elements['dataset_5M'] = dataset_5M
rsi_parameters.elements['dataset_1H'] = dataset_1H
rsi_parameters.elements['symbol'] = symbol

stochastic_parameters.elements['dataset_5M'] = dataset_5M
stochastic_parameters.elements['dataset_1H'] = dataset_1H
stochastic_parameters.elements['symbol'] = symbol


macd = MACD(parameters = macd_parameters, config = macd_config)
rsi = RSI(parameters = rsi_parameters, config = rsi_config)
stochastic = StochAstic(parameters = stochastic_parameters, config = stochastic_config)

candle_index = start_point
counter_index = start_point

number_tp = 0
number_st = 0

output = pd.DataFrame(columns = [
								'candle_index', 
								'time', 
								'time_1H',
								'Day',
								'signal', 
								'indicator',
								'flag', 
								'number_tp', 
								'number_st', 
								'money', 
								'tp_final', 
								'st_final', 
								'percent', 
								'tp', 
								'st',
								])
	
supply_zone_upper = 0
supply_zone_lowwer = 0
demand_zone_upper = 0
demand_zone_lowwer = 0

diff = 10

candle_idx_list = [
					# 2573 - diff,
					10947 - diff,
					11111 - diff,
					12349 - diff,
					13187 - diff,
					13639 - diff,
					14927 - diff,
					16221 - diff,
					16325 - diff,
					16573 - diff,
					17525 - diff,
					17821 - diff,
					18199 - diff,
					19083 - diff,
					19531 - diff,
					20005 - diff,
					20387 - diff,
					20813 - diff,
					21287 - diff,
					21759 - diff,
					23859 - diff,
					23975 - diff,
					24403 - diff,
					25239 - diff,
					25486 - diff,
					25767 - diff,
					37759 - diff,
					38077 - diff,
					38927 - diff,
					39854 - diff,
					40917 - diff,
					41319 - diff,
					41563 - diff,
					41853 - diff,
					42037 - diff,
					42867 - diff,
					47046 - diff,
					47491 - diff,
					50902 - diff,
					51431 - diff,
					51687 - diff,
					51875 - diff,
					52687 - diff,
					56535 - diff,
					56751 - diff,
					57117 - diff,
					58157 - diff,
					58493 - diff,
					58773 - diff,
					59082 - diff,
					59541 - diff,
					59723 - diff,
					60691 - diff,
					66711 - diff,
					66893 - diff,
					71821 - diff,
					72035 - diff,
					72373 - diff,
					72547 - diff,
					72891 - diff,
					73491 - diff,
					74583 - diff,
					75503 - diff,
					79775 - diff,
					79966 - diff,
					80347 - diff,
					84083 - diff,
					84315 - diff,
					84939 - diff,
					92973 - diff,
					93111 - diff,
					93675 - diff,
					94271 - diff,
					95579 - diff,
					96891 - diff,
					97223 - diff,
					100755 - diff,
					101247 - diff,
					101878 - diff,
					102071 - diff,
					102269 - diff,
					102708 - diff,
					103479 - diff,
					103639 - diff,
					104406 - diff,
					104583 - diff,
					105174 - diff,
					107631 - diff,
					107875 - diff,
					108982 - diff,
					110399 - diff,
					110643 - diff,
					111033 - diff,
					113033 - diff,
					114781 - diff,
					114945 - diff,
					115771 - diff,
					116165 - diff,
					116527 - diff,
					116819 - diff,
					117078 - diff,
					117475 - diff,
					117676 - diff,
					]


print('Start ....')
# while candle_index < dataset_5M[symbol].index[-1]:
for index_candle in candle_idx_list:

	candle_index = index_candle

	# diff = 100

	while candle_index <= index_candle + 2 * diff:

		if candle_index < 10936: 
			candle_index += 1
			continue

		# if candle_index > 11130: break

		dataset_1H_trade = dataset_1H.copy()
		dataset_1H_trade[symbol] = dataset_1H[symbol].copy(deep = True)
		dataset_5M_sliced = dataset_5M.copy()
		dataset_5M_sliced[symbol] = dataset_5M_sliced[symbol].truncate(before=candle_index - start_point, after=candle_index, axis=None, copy=True).reset_index(drop=True)
		# print(dataset_5M[symbol])
		# dataset_5M_sliced[symbol] = dataset_5M_sliced[symbol].reset_index(inplace = False)
		# dataset_5M_sliced[symbol] = dataset_5M_sliced[symbol].drop(columns = 'index')

		# print('no Sliced = ', dataset_1H[symbol])
		# print('sliced = ', dataset_5M_sliced[symbol]['index'][start_point])

		flag = 'no_flag'

		# print(dataset_5M_sliced[symbol])
		
		# print(candle_index)
		# print()

		try:
			# plt.plot(range(candle_index - int(start_point/4) , candle_index + int(start_point/4)), dataset_5M_real['high'][candle_index - int(start_point/4) : candle_index + int(start_point/4)], c = 'orange')
			# plt.plot(range(candle_index - int(start_point/4) , candle_index + int(start_point/4)), dataset_5M_real['low'][candle_index - int(start_point/4) : candle_index + int(start_point/4)], c = 'pink')
			# plt.axvline(x = candle_index, linestyle = 'dotted', c = 'g')
			
			# plt.show()

			# matplotlib.use("Agg")

			dataset_1H_trade[symbol] = dataset_1H[symbol].copy(deep = True)

			dataset_plot_5M, dataset_plot_1H = data_changer.SpliterSyncPR(
																		dataset_5M = dataset_5M_real,
																		dataset_1H = dataset_1H_trade[symbol],
																		loc_end_5M = candle_index + 240,
																		length_5M = 440,
																		length_1H = 440,
																		)

			daily_1H = pd.DataFrame(dataset_plot_1H)
			daily_1H.index.name = 'Time'
			daily_1H.index = dataset_plot_1H['time']
			daily_1H.head(3)
			daily_1H.tail(3)

			daily_5M = pd.DataFrame(dataset_plot_5M)
			daily_5M.index.name = 'Time'
			daily_5M.index = dataset_plot_5M['time']
			daily_5M.head(3)
			daily_5M.tail(3)

			mc_1H = mpf_1H.make_marketcolors(
										base_mpf_style='yahoo',
										up='green',
										down='red',
										#vcedge = {'up': 'green', 'down': 'red'}, 
										vcdopcod = True,
										alpha = 0.0001
										)

			mco_1H = [mc_1H]*len(daily_1H)


			mc_5M = mpf_5M.make_marketcolors(
										base_mpf_style='yahoo',
										up='green',
										down='red',
										#vcedge = {'up': 'green', 'down': 'red'}, 
										vcdopcod = True,
										alpha = 0.0001
										)

			mco_5M = [mc_5M]*len(daily_5M)

			_, dataset_priceaction_1H = data_changer.SpliterSyncPR(
																	dataset_5M = dataset_5M_real,
																	dataset_1H = dataset_1H_trade[symbol],
																	loc_end_5M = candle_index,
																	length_5M = start_point,
																	length_1H = 600,
																	)
			vertical_1H = dataset_5M_sliced[symbol]['time'].iloc[-1]

			# print(daily['Time'][vertical_1H])


			signal_macd, tp_macd, st_macd, supply_zone_upper, supply_zone_lowwer, demand_zone_upper, demand_zone_lowwer, lst_idx_signal = macd.LastSignal(
																															dataset_5M = dataset_5M_sliced.copy(), 
																															dataset_1H = dataset_1H_trade.copy(), 
																															dataset_1H_priceaction = dataset_priceaction_1H.copy(deep = True),
																															symbol = symbol,
																															supply_zone_upper = 0,
																															supply_zone_lowwer = 0,
																															demand_zone_upper = 0,
																															demand_zone_lowwer = 0,
																															candle_index = candle_index
																															)
			# print(lst_idx_signal)
			# print(tp_macd)
			# print()
			if lst_idx_signal != 0 and lst_idx_signal != start_point:
				try:
					mpf_5M.plot(
								daily_5M,
								type='candle',
								volume=True,
								style='yahoo',
								figscale=1,
								hlines=dict(hlines=[supply_zone_upper, supply_zone_lowwer, st_macd, tp_macd],colors=['r', 'g', 'orange', 'pink'],linestyle='dotted'),
								vlines=dict(vlines=[vertical_1H, dataset_5M_sliced[symbol]['time'][lst_idx_signal]],colors=['purple', 'orange'],linestyle='dotted'),
								savefig=dict(fname='SimulatePics/sell/' + str(candle_index) + '_5M_candle_',dpi=600,pad_inches=0.25),
								marketcolor_overrides=mco_5M,
								)
				except Exception as ex:
					pass
			else:
				# mpf_1H.figure().clear()
				mpf_5M.figure().clear()

		except Exception as ex:
			# print('MACD: ', ex)
			signal_macd = 'no_flag'

		# print(signal_macd)

		# dataset_1H_trade = dataset_1H.copy()
		# dataset_1H_trade[symbol] = dataset_1H[symbol].copy(deep = True)

		# try:
		# 	signal_stochastic, tp_stochastic, st_stochastic = stochastic.LastSignal(
		# 																			dataset_5M = dataset_5M_sliced.copy(), 
		# 																			dataset_1H = dataset_1H_trade.copy(), 
		# 																			symbol = symbol
		# 																			)
		# except Exception as ex:
		# 	print('RSI: ', ex)

		# dataset_1H_trade = dataset_1H.copy()
		# dataset_1H_trade[symbol] = dataset_1H[symbol].copy(deep = True)

		# try:
		# 	signal_rsi, tp_rsi, st_rsi = rsi.LastSignal(
		# 												dataset_5M = dataset_5M_sliced.copy(), 
		# 												dataset_1H = dataset_1H_trade.copy(), 
		# 												symbol = symbol
		# 												)
		# except Exception as ex:
		# 	print('StochAstic: ', ex)

		signal = 'no_signal'
		resist = 0
		protect = 0

		if signal_macd == 'buy_primary' or signal_macd == 'buy_secondry' or signal_macd == 'sell_primary' or signal_macd == 'sell_secondry':

			signal = ''#signal_macd
			tp = tp_macd
			st = st_macd
			indicator = 'macd'
			
			if signal_macd == 'sell_primary' or signal_macd == 'sell_secondry':
				signal = ''#signal_macd
				tp = tp_macd
				st = st_macd
				indicator = 'macd'

				dataset_1H_trade[symbol] = dataset_1H[symbol].copy(deep = True)

				dataset_plot_5M, dataset_plot_1H = data_changer.SpliterSyncPR(
																			dataset_5M = dataset_5M_real,
																			dataset_1H = dataset_1H_trade[symbol],
																			loc_end_5M = candle_index + 240,
																			length_5M = 440,
																			length_1H = 440,
																			)

				daily_1H = pd.DataFrame(dataset_plot_1H)
				daily_1H.index.name = 'Time'
				daily_1H.index = dataset_plot_1H['time']
				daily_1H.head(3)
				daily_1H.tail(3)

				daily_5M = pd.DataFrame(dataset_plot_5M)
				daily_5M.index.name = 'Time'
				daily_5M.index = dataset_plot_5M['time']
				daily_5M.head(3)
				daily_5M.tail(3)

				mc_1H = mpf_1H.make_marketcolors(
											base_mpf_style='yahoo',
											up='green',
											down='red',
											#vcedge = {'up': 'green', 'down': 'red'}, 
											vcdopcod = True,
											alpha = 0.0001
											)

				mco_1H = [mc_1H]*len(daily_1H)


				mc_5M = mpf_5M.make_marketcolors(
											base_mpf_style='yahoo',
											up='green',
											down='red',
											#vcedge = {'up': 'green', 'down': 'red'}, 
											vcdopcod = True,
											alpha = 0.0001
											)

				mco_5M = [mc_5M]*len(daily_5M)

		# elif signal_stochastic == 'buy_primary' or signal_stochastic == 'buy_secondry' or signal_stochastic == 'sell_primary' or signal_stochastic == 'sell_secondry':
		# 	signal = signal_stochastic
		# 	tp = tp_stochastic
		# 	st = st_stochastic
		# 	indicator = 'stochastic'

		# elif signal_rsi == 'buy_primary' or signal_rsi == 'buy_secondry' or signal_rsi == 'sell_primary' or signal_rsi == 'sell_secondry':
		# 	signal = signal_rsi
		# 	tp = tp_rsi
		# 	st = st_rsi
		# 	indicator = 'rsi'

		# print('ccccccaaaaandle = ', candle_index)
		
		if signal == 'buy_primary' or signal == 'buy_secondry':

			# print('st = ', st)
			# print('low = ', dataset_5M_real['low'][candle_index])
			

			# print('tp = ', tp)
			# print('high = ', (1 + spred) * dataset_5M_real['high'][candle_index])
			

			# print()

			# print('signal_macd = ', signal_macd)
			# print('signal_rsi = ', signal_rsi)
			# print('signal_stochastic = ', signal_stochastic)
			# print()

			try:
				money, flag, tp_pr, st_pr, candle_index_last = BuyChecker(dataset_5M_real, tp, st, candle_index, money, coef_money, spred)

				# plt.plot(dataset_5M[symbol]['low'][candle_index: candle_index_last + 1000], c = 'r')
				plt.axvline(x = candle_index, linestyle = '-.', c = 'g')

				plt.plot(dataset_5M[symbol]['high'][candle_index: candle_index_last + 4000], c = 'r')
				plt.plot(dataset_5M[symbol]['low'][candle_index: candle_index_last + 4000], c = 'g')
				# plt.show()
				plt.title(label = signal)


				if not os.path.exists('SimulatePics/buy/' + flag + '/'):
					os.makedirs('SimulatePics/buy/' + flag + '/')

				plt.savefig('SimulatePics/buy/' + flag + '/' + signal + '_' + str(candle_index), dpi=600, bbox_inches='tight')

				plt.figure().clear()
				plt.close('all')
				plt.cla()
				plt.clf()
				# plt.show()
			except Exception as ex:
				print('Buy: ', ex) 
				flag = 'no_flag' 
				tp_pr = 0
				st_pr = 0

		elif signal == 'sell_primary' or signal == 'sell_secondry':

			# print('st = ', st)
			# print('high = ', (1 + spred) * dataset_5M_real['high'][candle_index])

			# print('tp = ', tp)
			# print('low = ', dataset_5M_real['low'][candle_index])

			# print()

			# print('signal_macd = ', signal_macd)
			# print('signal_rsi = ', signal_rsi)
			# print('signal_stochastic = ', signal_stochastic)
			# print()

			try:
				money, flag, tp_pr, st_pr, candle_index_last = SellChecker(dataset_5M_real, tp, st, candle_index, money, coef_money, spred)

				
				# plt.show()
				plt.title(label = signal + ' -> ' + flag)

				if not os.path.exists('SimulatePics/sell/'):
					os.makedirs('SimulatePics/sell/')


				# if supply_zone_lowwer == 0: supply_zone_lowwer = st
				# if supply_zone_upper == 0: supply_zone_upper = st

				time_clash = dataset_5M_real['time'][candle_index_last]


				mpf_1H.plot(
						daily_1H,
						type='candle',
						volume=True,
						style='yahoo',
						figscale=1,
						hlines=dict(hlines=[tp,st, supply_zone_upper, supply_zone_lowwer, demand_zone_upper, demand_zone_lowwer],colors=['black','purple', 'r', 'g', 'r', 'g'],linestyle='dotted'),
						vlines=dict(vlines=[vertical_1H, time_clash, dataset_5M_sliced[symbol]['time'][lst_idx_signal]],colors=['purple', 'r', 'orange'],linestyle='dotted'),
						savefig=dict(fname='SimulatePics/sell/' + str(candle_index) + '_1H_candle_' + flag,dpi=600,pad_inches=0.25),
						marketcolor_overrides=mco_1H,
						#alines=dict(alines=two_points,colors=['orange'],linestyle='-.'),
						)

				mpf_5M.plot(
						daily_5M,
						type='candle',
						volume=True,
						style='yahoo',
						figscale=1,
						hlines=dict(hlines=[tp,st, supply_zone_upper, supply_zone_lowwer, demand_zone_upper, demand_zone_lowwer],colors=['black','purple', 'r', 'g', 'r', 'g'],linestyle='dotted'),
						vlines=dict(vlines=[vertical_1H, time_clash, dataset_5M_sliced[symbol]['time'][lst_idx_signal]],colors=['purple', 'r', 'orange'],linestyle='dotted'),
						savefig=dict(fname='SimulatePics/sell/' + str(candle_index) + '_5M_candle_' + flag,dpi=600,pad_inches=0.25),
						marketcolor_overrides=mco_5M,
						#alines=dict(alines=two_points,colors=['orange'],linestyle='-.'),
						)

				#if flag != 'no_flag':
				# plt.show()
				# plt.axhline(y = tp, c = 'r')
				# plt.axhline(y = st, c = 'r')
				# plt.savefig('SimulatePics/sell/' + str(candle_index) + '_5M', dpi=600, bbox_inches='tight')

				mpf_1H.figure().clear()
				mpf_5M.figure().clear()
				plt.figure().clear()
				plt.close('all')
				plt.cla()
				plt.clf()

			except Exception as ex: 
				print('SELL: ', ex)
				flag = 'no_flag' 
				tp_pr = 0
				st_pr = 0
		else:
			plt.figure().clear()
			plt.close('all')
			plt.cla()
			plt.clf()
			mpf_1H.figure().clear()
			mpf_5M.figure().clear()

		if flag == 'tp':
			percent += tp_pr
			tp_pr_eq += tp_pr
			number_tp += 1

			output = output.append(
									{
									'candle_index': candle_index,
									'time': dataset_5M_sliced[symbol]['time'].iloc[-1],
									'time_1H': dataset_priceaction_1H['time'].iloc[-1],
									'Day': dataset_5M_real['time'][candle_index].day_name(),
									'signal': signal,
									'indicator': indicator,
									'flag': flag,
									'number_tp': number_tp,
									'number_st': number_st,
									'money': money,
									'tp_final': tp_pr_eq,
									'st_final': st_pr_eq,
									'percent': percent,
									'tp': tp_pr,
									'st': st_pr,
									},
									ignore_index = True
									)
			# candle_index = candle_index_last
			print()
			with pd.option_context('display.max_rows', None, 'display.max_columns', None):
				print(output.iloc[-1])
			print()

			if os.path.exists('MainTester.csv'):
				os.remove('MainTester.csv')
			output.to_csv('MainTester.csv')

		elif flag == 'st':
			percent -= st_pr
			st_pr_eq += st_pr
			number_st += 1

			output = output.append(
									{
									'candle_index': candle_index,
									'time': dataset_5M_sliced[symbol]['time'].iloc[-1],
									'time_1H': dataset_plot_1H['time'][dataset_plot_1H['time'] == vertical_1H],
									'Day': dataset_5M_real['time'][candle_index].day_name(),
									'signal': signal,
									'indicator': indicator,
									'flag': flag,
									'number_tp': number_tp,
									'number_st': number_st,
									'money': money,
									'tp_final': tp_pr_eq,
									'st_final': st_pr_eq,
									'percent': percent,
									'tp': tp_pr,
									'st': st_pr,
									},
									ignore_index = True
									)
			# candle_index = candle_index_last
			print()
			with pd.option_context('display.max_rows', None, 'display.max_columns', None):
				print(output.iloc[-1])
			print()

			if os.path.exists('MainTester.csv'):
				os.remove('MainTester.csv')
			output.to_csv('MainTester.csv')

		# if money <= 4: break

		candle_index += 1

output.to_csv('MainTester.csv')


print('* Final Money = ', money)
print('********** tp = ', tp_pr_eq)
print('********** st = ', st_pr_eq)
print('Fanal percent = ', percent)


