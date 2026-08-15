from src.indicators.StochAstic.StochAstic import StochAstic
from src.utils.Divergence.Divergence import Divergence
from .ParameterReader import ParameterReader
from src.indicators.MACD.MACD import MACD
from src.utils.Tools.timer import stTime
from src.indicators.ZigZag import ZigZag
from src.indicators.RSI.RSI import RSI
from .DatasetIO import DatasetIO
from progress.bar import Bar
from .Config import Config
import pandas_ta as ind
import pandas as pd
import numpy as np


#Functions:

#CandlePatterns()

#Run()
#Get()

#////////////////////


class Patterns():

	def __init__(self):

		self.config_candle_pattern_5m = True
		self.config_candle_pattern_15m = True
		self.config_candle_pattern_1h = True
		self.config_candle_pattern_4h = True
		self.config_candle_pattern_1d = True

		#Run Flags:
		self.CandlePatternFlag = False
		self.DailyPatternFlag = False
		self.DivergencePatternFlag = False
		self.ColorCandleFlag = True
		self.CandleNumberPatternFlag = False
		#///////////////////////////

		#ZigZag Parameters:
		self.percent_zigzag_finder = 0.25
		self.profit = 0.4
		#/////////////////////////////


	#Candle Patterns:
	def CandlePatterns(self, dataset_5M = '', dataset_15M = '', dataset_1H = '', dataset_4H = '', dataset_1D = ''):

		#Sell = 1
		#Buy = 2
		#Noting = 0

		#//////////////////////////////////////////////////////
		cdl_patterns_5m = ind.cdl_pattern(
										open_ = dataset_5M['open'],
										high = dataset_5M['high'],
										low = dataset_5M['low'],
										close = dataset_5M['close'],
										name = 'all',
										scalar = 1
										)
		cdl_patterns_5m[cdl_patterns_5m < 0] = 1
		cdl_patterns_5m[cdl_patterns_5m > 0] = 2
		cdl_patterns_5m['candle_pattern'] = cdl_patterns_5m.sum(axis=1)/(len(cdl_patterns_5m.columns) * 2)


		#//////////////////////////////////////////////////////
		cdl_patterns_15m = ind.cdl_pattern(
										open_ = dataset_15M['open'],
										high = dataset_15M['high'],
										low = dataset_15M['low'],
										close = dataset_15M['close'],
										name = 'all',
										scalar = 1
										)
		cdl_patterns_15m[cdl_patterns_15m < 0] = 1
		cdl_patterns_15m[cdl_patterns_15m > 0] = 2
		cdl_patterns_15m['candle_pattern'] = cdl_patterns_15m.sum(axis=1)/(len(cdl_patterns_15m.columns) * 2)


		#//////////////////////////////////////////////////////
		cdl_patterns_1h = ind.cdl_pattern(
										open_ = dataset_1H['open'],
										high = dataset_1H['high'],
										low = dataset_1H['low'],
										close = dataset_1H['close'],
										name = 'all',
										scalar = 1
										)
		cdl_patterns_1h[cdl_patterns_1h < 0] = 1
		cdl_patterns_1h[cdl_patterns_1h > 0] = 2
		cdl_patterns_1h['candle_pattern'] = cdl_patterns_1h.sum(axis=1)/(len(cdl_patterns_1h.columns) * 2)

		#//////////////////////////////////////////////////////
		cdl_patterns_4h = ind.cdl_pattern(
										open_ = dataset_4H['open'],
										high = dataset_4H['high'],
										low = dataset_4H['low'],
										close = dataset_4H['close'],
										name = 'all',
										scalar = 1
										)
		cdl_patterns_4h[cdl_patterns_4h < 0] = 1
		cdl_patterns_4h[cdl_patterns_4h > 0] = 2
		cdl_patterns_4h['candle_pattern'] = cdl_patterns_4h.sum(axis=1)/(len(cdl_patterns_4h.columns) * 2)

		#//////////////////////////////////////////////////////
		cdl_patterns_1d = ind.cdl_pattern(
										open_ = dataset_1D['open'],
										high = dataset_1D['high'],
										low = dataset_1D['low'],
										close = dataset_1D['close'],
										name = 'all',
										scalar = 1
										)
		cdl_patterns_1d[cdl_patterns_1d < 0] = 1
		cdl_patterns_1d[cdl_patterns_1d > 0] = 2
		cdl_patterns_1d['candle_pattern'] = cdl_patterns_1d.sum(axis=1)/(len(cdl_patterns_1d.columns) * 2)

		return cdl_patterns_5m, cdl_patterns_15m, cdl_patterns_1h, cdl_patterns_4h, cdl_patterns_1d
	#////////////////////////////////////////


	#Color Candle Pattern:
	def ColorCandle(self, dataset_5M = '', dataset_15M = '', dataset_1H = '', dataset_4H = '', dataset_1D = ''):

		if True:#(dataset_5M != ''):
			red_index = np.where(dataset_5M['open'] > dataset_5M['close'])[0]
			green_index = np.where(dataset_5M['open'] <= dataset_5M['close'])[0]

			color_candles_5M = pd.DataFrame(index = dataset_5M.index)
			color_candles_5M['color_candle'] = np.nan

			color_candles_5M['color_candle'][green_index] = 1
			color_candles_5M['color_candle'][red_index] = 0
		else:
			color_candles_5M = pd.DataFrame()


		if True:#(dataset_15M != ''):
			red_index = np.where(dataset_15M['open'] > dataset_15M['close'])[0]
			green_index = np.where(dataset_15M['open'] <= dataset_15M['close'])[0]

			color_candles_15M = pd.DataFrame(index = dataset_15M.index)
			color_candles_15M['color_candle'] = np.nan

			color_candles_15M['color_candle'][green_index] = 1
			color_candles_15M['color_candle'][red_index] = 0
		else:
			color_candles_15M = pd.DataFrame()


		if True:#(dataset_1H != ''):
			red_index = np.where(dataset_1H['open'] > dataset_1H['close'])[0]
			green_index = np.where(dataset_1H['open'] <= dataset_1H['close'])[0]

			color_candles_1H = pd.DataFrame(index = dataset_1H.index)
			color_candles_1H['color_candle'] = np.nan

			color_candles_1H['color_candle'][green_index] = 1
			color_candles_1H['color_candle'][red_index] = 0
		else:
			color_candles_1H = pd.DataFrame()


		if True:#(dataset_1H != ''):
			red_index = np.where(dataset_4H['open'] > dataset_4H['close'])[0]
			green_index = np.where(dataset_4H['open'] <= dataset_4H['close'])[0]

			color_candles_4H = pd.DataFrame(index = dataset_4H.index)
			color_candles_4H['color_candle'] = np.nan

			color_candles_4H['color_candle'][green_index] = 1
			color_candles_4H['color_candle'][red_index] = 0
		else:
			color_candles_4H = pd.DataFrame()

		if True:#(dataset_1H != ''):
			red_index = np.where(dataset_1D['open'] > dataset_1D['close'])[0]
			green_index = np.where(dataset_1D['open'] <= dataset_1D['close'])[0]

			color_candles_1D = pd.DataFrame(index = dataset_1D.index)
			color_candles_1D['color_candle'] = np.nan

			color_candles_1D['color_candle'][green_index] = 1
			color_candles_1D['color_candle'][red_index] = 0
		else:
			color_candles_1D = pd.DataFrame()

		return color_candles_5M, color_candles_15M, color_candles_1H, color_candles_4H, color_candles_1D
	#//////////////////////


	#Daily Pattern:
	def DailyPatterns(self, dataset_5M = '', dataset_15M = '', dataset_1H = '', dataset_4H = '', dataset_1D = ''):

		DaysOfWeek = ['Monday', 'Tuesday', 'Thursday', 'Wednesday', 'Friday']

		daily_pattern_5M = pd.DataFrame()
		daily_pattern_15M = pd.DataFrame()
		daily_pattern_1H = pd.DataFrame()
		daily_pattern_4H = pd.DataFrame()
		daily_pattern_1D = pd.DataFrame()

		#//////////////////////////////////////////////////////
		daily_pattern_5M['pattern_day'] = (
											dataset_5M['time'].copy(deep = True).dt.isocalendar().day/
											dataset_5M['time'].copy(deep = True).dt.isocalendar().day.max()
											)
		daily_pattern_5M['pattern_week'] = (
											dataset_5M['time'].copy(deep = True).dt.isocalendar().week/
											dataset_5M['time'].copy(deep = True).dt.isocalendar().week.max()
											)
		#//////////////////////////////////////////////////////
		daily_pattern_15M['pattern_day'] = (
											dataset_15M['time'].copy(deep = True).dt.isocalendar().day/
											dataset_15M['time'].copy(deep = True).dt.isocalendar().day.max()
											)
		daily_pattern_15M['pattern_week'] = (
											dataset_15M['time'].copy(deep = True).dt.isocalendar().week/
											dataset_15M['time'].copy(deep = True).dt.isocalendar().week.max()
											)
		#//////////////////////////////////////////////////////
		daily_pattern_1H['pattern_day'] = (
											dataset_1H['time'].copy(deep = True).dt.isocalendar().day/
											dataset_1H['time'].copy(deep = True).dt.isocalendar().day.max()
											)
		daily_pattern_1H['pattern_week'] = (
											dataset_1H['time'].copy(deep = True).dt.isocalendar().week/
											dataset_1H['time'].copy(deep = True).dt.isocalendar().week.max()
											)
		#//////////////////////////////////////////////////////

		daily_pattern_4H['pattern_day'] = (
											dataset_4H['time'].copy(deep = True).dt.isocalendar().day/
											dataset_4H['time'].copy(deep = True).dt.isocalendar().day.max()
											)
		daily_pattern_4H['pattern_week'] = (
											dataset_4H['time'].copy(deep = True).dt.isocalendar().week/
											dataset_4H['time'].copy(deep = True).dt.isocalendar().week.max()
											)
		#//////////////////////////////////////////////////////

		daily_pattern_1D['pattern_day'] = (
											dataset_1D['time'].copy(deep = True).dt.isocalendar().day/
											dataset_1D['time'].copy(deep = True).dt.isocalendar().day.max()
											)
		daily_pattern_1D['pattern_week'] = (
											dataset_1D['time'].copy(deep = True).dt.isocalendar().week/
											dataset_1D['time'].copy(deep = True).dt.isocalendar().week.max()
											)
		#//////////////////////////////////////////////////////

		return daily_pattern_5M, daily_pattern_15M, daily_pattern_1H, daily_pattern_4H, daily_pattern_1D
	#//////////////////////

	#Candle Number Pattern in day:
	def CandleNumberPatterns(self, dataset_5M = '', dataset_15M = '', dataset_1H = '', dataset_4H = '', dataset_1D = ''):

		cdl_number_pattern_5m = pd.DataFrame()
		cdl_number_pattern_5m['number'] = (dataset_5M['time'].dt.hour * 12) + (dataset_5M['time'].dt.minute / 5)
		cdl_number_pattern_5m['number'] = cdl_number_pattern_5m['number'] / cdl_number_pattern_5m['number'].max()


		#//////////////////////////////////////////////////////
		cdl_number_pattern_15m = pd.DataFrame()
		cdl_number_pattern_15m['number'] = (dataset_15M['time'].dt.hour * 4) + (dataset_15M['time'].dt.minute / 15)
		cdl_number_pattern_15m['number'] = cdl_number_pattern_15m['number'] / cdl_number_pattern_15m['number'].max()


		#//////////////////////////////////////////////////////
		cdl_number_pattern_1h = pd.DataFrame()
		cdl_number_pattern_1h['number'] = (dataset_1H['time'].dt.hour * 1)
		cdl_number_pattern_1h['number'] = cdl_number_pattern_1h['number'] / cdl_number_pattern_1h['number'].max()

		#//////////////////////////////////////////////////////
		cdl_number_pattern_4h = pd.DataFrame()
		cdl_number_pattern_4h['number'] = (dataset_4H['time'].dt.hour * 1)
		cdl_number_pattern_4h['number'] = cdl_number_pattern_4h['number'] / cdl_number_pattern_4h['number'].max()

		#//////////////////////////////////////////////////////
		cdl_number_pattern_1d = pd.DataFrame()
		cdl_number_pattern_1d['number'] = (dataset_1D['time'].dt.hour * 1)
		cdl_number_pattern_1d['number'] = cdl_number_pattern_1d['number'] / cdl_number_pattern_1d['number'].max()

		return cdl_number_pattern_5m, cdl_number_pattern_15m, cdl_number_pattern_1h, cdl_number_pattern_4h ,cdl_number_pattern_1d
		
		
	#//////////////////////

	#Divergence Pattern:
	def DivergencePatterns(self, dataset_5M = '', dataset_15M = '', dataset_1H = '', dataset_4H = '', dataset_1D = '', symbol = 'XAUUSD_i'):

		signalpriority = ['primary', 'secondry', 'primary', 'secondry']
		signaltype = ['buy' , 'sell', 'sell' , 'buy']
		indicator_names = ['macd', 'stochastic', 'rsi']

		parameter_reader = ParameterReader()

		divergence_pattern_5M = pd.DataFrame(index = dataset_5M.index)
		divergence_pattern_15M = pd.DataFrame(index = dataset_15M.index)
		divergence_pattern_1H = pd.DataFrame(index = dataset_1H.index)
		divergence_pattern_4H = pd.DataFrame(index = dataset_4H.index)
		divergence_pattern_1D = pd.DataFrame(index = dataset_1D.index)

		dataset_5M_ = {symbol: dataset_5M.copy(deep = True)}
		dataset_15M_ = {symbol: dataset_15M.copy(deep = True)}
		dataset_1H_ = {symbol: dataset_1H.copy(deep = True)}
		dataset_4H_ = {symbol: dataset_4H.copy(deep = True)}
		dataset_1D_ = {symbol: dataset_1D.copy(deep = True)}

		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Daily Patterns Finding: ', 
																	max = int(
																			len(signalpriority) * 
																			len(signaltype) * 
																			len(timeframes) * 
																			len(indicator_names)
																			)
					)

		#******* 5M ******************************************
		for ind_name in indicator_names:
			for sigpriority, sigtype in zip(signalpriority, signaltype):

				ind_parameters, ind_config, div_parameters, div_config = parameter_reader.Divergence(
																									signalpriority = sigpriority,
																									signaltype = sigtype,
																									symbol = symbol,
																									timeframe = '5M',
																									dataset = dataset_5M_,
																									indicator_name = ind_name
																									)

				try:
					#Add MACD Calculate Params AS Alpha Factor To Dataset:
					if ind_name == 'macd':

						ind = MACD(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_macd()

						ind_calc['time'] = dataset_5M_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['MACD_column_div']
					#///////////////////////////////////////

					#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'stochastic':

						ind = StochAstic(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_StochAstic()

						ind_calc['time'] = dataset_5M_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['StochAstic_column_div']
					#//////////////////////////////////////////////////////////

					#Add RSI Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'rsi':

						ind = RSI(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_rsi()

						ind_calc['time'] = dataset_5M_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = 'rsi'
					#////////////////////////////////////////////////////////////

					divergence = Divergence(parameters = div_parameters, config = div_config)

					signal, _, _ = divergence.divergence(
														sigtype = sigtype,
														sigpriority = sigpriority,
														indicator = ind_calc,
														column_div = column_div,
														ind_name = ind_name,
														dataset_5M = dataset_5M_,
														dataset_1H = dataset_5M_,
														symbol = symbol,
														flaglearn = False,
														flagtest = False
														)

					signal = signal.drop_duplicates(subset = ['time_low_front'])

					divergence_pattern_5M['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'
					divergence_pattern_5M['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority][signal.index] = signal['signal']

				except Exception as ex:
					divergence_pattern_5M['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'

				if bar_config.cfg['show_bar']:
					bar.next()
		#//////////////////////////////////////////////////////


		#******* 15M ******************************************
		for ind_name in indicator_names:
			for sigpriority, sigtype in zip(signalpriority, signaltype):

				ind_parameters, ind_config, div_parameters, div_config = parameter_reader.Divergence(
																									signalpriority = sigpriority,
																									signaltype = sigtype,
																									symbol = symbol,
																									timeframe = '15M',
																									dataset = dataset_15M_,
																									indicator_name = ind_name
																									)

				try:
					#Add MACD Calculate Params AS Alpha Factor To Dataset:
					if ind_name == 'macd':

						ind = MACD(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_macd()

						ind_calc['time'] = dataset_15M_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['MACD_column_div']
					#///////////////////////////////////////

					#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'stochastic':

						ind = StochAstic(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_StochAstic()

						ind_calc['time'] = dataset_15M_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['StochAstic_column_div']
					#//////////////////////////////////////////////////////////

					#Add RSI Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'rsi':

						ind = RSI(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_rsi()

						ind_calc['time'] = dataset_15M_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = 'rsi'
					#////////////////////////////////////////////////////////////

					divergence = Divergence(parameters = div_parameters, config = div_config)

					signal, _, _ = divergence.divergence(
														sigtype = sigtype,
														sigpriority = sigpriority,
														indicator = ind_calc,
														column_div = column_div,
														ind_name = ind_name,
														dataset_5M = dataset_15M_,
														dataset_1H = dataset_15M_,
														symbol = symbol,
														flaglearn = False,
														flagtest = False
														)

					signal = signal.drop_duplicates(subset = ['time_low_front'])

					divergence_pattern_15M['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'
					divergence_pattern_15M['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority][signal.index] = signal['signal']

				except Exception as ex:
					divergence_pattern_15M['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'

				if bar_config.cfg['show_bar']:
					bar.next()
		#//////////////////////////////////////////////////////

		#****** 1H ********************************************
		for ind_name in indicator_names:
			for sigpriority, sigtype in zip(signalpriority, signaltype):

				ind_parameters, ind_config, div_parameters, div_config = parameter_reader.Divergence(
																									signalpriority = sigpriority,
																									signaltype = sigtype,
																									symbol = symbol,
																									timeframe = '1H',
																									dataset = dataset_1H_,
																									indicator_name = ind_name
																									)
				try:
					#Add MACD Calculate Params AS Alpha Factor To Dataset:
					if ind_name == 'macd':

						ind = MACD(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_macd()

						ind_calc['time'] = dataset_1H_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['MACD_column_div']
					#///////////////////////////////////////

					#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'stochastic':

						ind = StochAstic(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_StochAstic()

						ind_calc['time'] = dataset_1H_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['StochAstic_column_div']
					#//////////////////////////////////////////////////////////

					#Add RSI Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'rsi':

						ind = RSI(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_rsi()

						ind_calc['time'] = dataset_1H_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = 'rsi'
					#////////////////////////////////////////////////////////////

					divergence = Divergence(parameters = div_parameters, config = div_config)

					signal, _, _ = divergence.divergence(
														sigtype = sigtype,
														sigpriority = sigpriority,
														indicator = ind_calc,
														column_div = column_div,
														ind_name = ind_name,
														dataset_5M = dataset_1H_,
														dataset_1H = dataset_1H_,
														symbol = symbol,
														flaglearn = False,
														flagtest = False
														)

					signal = signal.drop_duplicates(subset = ['time_low_front'])

					divergence_pattern_1H['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'
					divergence_pattern_1H['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority][signal.index] = signal['signal']

				except Exception as ex:
					divergence_pattern_1H['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'

				if bar_config.cfg['show_bar']:
					bar.next()

		#****** 4H ********************************************
		for ind_name in indicator_names:
			for sigpriority, sigtype in zip(signalpriority, signaltype):

				ind_parameters, ind_config, div_parameters, div_config = parameter_reader.Divergence(
																									signalpriority = sigpriority,
																									signaltype = sigtype,
																									symbol = symbol,
																									timeframe = '4H',
																									dataset = dataset_4H_,
																									indicator_name = ind_name
																									)
				try:
					#Add MACD Calculate Params AS Alpha Factor To Dataset:
					if ind_name == 'macd':

						ind = MACD(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_macd()

						ind_calc['time'] = dataset_4H_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['MACD_column_div']
					#///////////////////////////////////////

					#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'stochastic':

						ind = StochAstic(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_StochAstic()

						ind_calc['time'] = dataset_4H_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['StochAstic_column_div']
					#//////////////////////////////////////////////////////////

					#Add RSI Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'rsi':

						ind = RSI(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_rsi()

						ind_calc['time'] = dataset_4H_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = 'rsi'
					#////////////////////////////////////////////////////////////

					divergence = Divergence(parameters = div_parameters, config = div_config)

					signal, _, _ = divergence.divergence(
														sigtype = sigtype,
														sigpriority = sigpriority,
														indicator = ind_calc,
														column_div = column_div,
														ind_name = ind_name,
														dataset_5M = dataset_4H_,
														dataset_4H = dataset_4H_,
														symbol = symbol,
														flaglearn = False,
														flagtest = False
														)

					signal = signal.drop_duplicates(subset = ['time_low_front'])

					divergence_pattern_4H['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'
					divergence_pattern_4H['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority][signal.index] = signal['signal']

				except Exception as ex:
					divergence_pattern_4H['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'

				if bar_config.cfg['show_bar']:
					bar.next()

		#****** 1D ********************************************
		for ind_name in indicator_names:
			for sigpriority, sigtype in zip(signalpriority, signaltype):

				ind_parameters, ind_config, div_parameters, div_config = parameter_reader.Divergence(
																									signalpriority = sigpriority,
																									signaltype = sigtype,
																									symbol = symbol,
																									timeframe = '1D',
																									dataset = dataset_1D_,
																									indicator_name = ind_name
																									)
				try:
					#Add MACD Calculate Params AS Alpha Factor To Dataset:
					if ind_name == 'macd':

						ind = MACD(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_macd()

						ind_calc['time'] = dataset_1D_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['MACD_column_div']
					#///////////////////////////////////////

					#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'stochastic':

						ind = StochAstic(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_StochAstic()

						ind_calc['time'] = dataset_1D_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = ind_parameters.elements['StochAstic_column_div']
					#//////////////////////////////////////////////////////////

					#Add RSI Calculate Params AS Alpha Factor To Dataset:
					elif ind_name == 'rsi':

						ind = RSI(parameters = ind_parameters, config = ind_config)
						ind_calc = ind.calculator_rsi()

						ind_calc['time'] = dataset_1D_[symbol]['time']
						ind_calc['index'] = ind_calc.index
						ind_calc.index = ind_calc['time']

						ind_calc.index = ind_calc['index']

						column_div = 'rsi'
					#////////////////////////////////////////////////////////////

					divergence = Divergence(parameters = div_parameters, config = div_config)

					signal, _, _ = divergence.divergence(
														sigtype = sigtype,
														sigpriority = sigpriority,
														indicator = ind_calc,
														column_div = column_div,
														ind_name = ind_name,
														dataset_5M = dataset_1D_,
														dataset_1D = dataset_1D_,
														symbol = symbol,
														flaglearn = False,
														flagtest = False
														)

					signal = signal.drop_duplicates(subset = ['time_low_front'])

					divergence_pattern_1D['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'
					divergence_pattern_1D['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority][signal.index] = signal['signal']

				except Exception as ex:
					divergence_pattern_1D['pattern_' + ind_name + '_' + sigtype + '_' + sigpriority] = 'no_trade'

				if bar_config.cfg['show_bar']:
					bar.next()

		divergence_pattern_5M[divergence_pattern_5M == 'buy_primary'] = 4
		divergence_pattern_5M[divergence_pattern_5M == 'buy_secondry'] = 2
		divergence_pattern_5M[divergence_pattern_5M == 'sell_primary'] = 3
		divergence_pattern_5M[divergence_pattern_5M == 'sell_secondry'] = 1
		divergence_pattern_5M[divergence_pattern_5M == 'no_trade'] = 0
		divergence_pattern_5M['macd_div'] = divergence_pattern_5M[divergence_pattern_5M.filter(regex='macd').columns].sum(axis=1)/10
		divergence_pattern_5M['stochastic_div'] = divergence_pattern_5M[divergence_pattern_5M.filter(regex='stochastic').columns].sum(axis=1)/10
		divergence_pattern_5M['rsi_div'] = divergence_pattern_5M[divergence_pattern_5M.filter(regex='rsi').columns].sum(axis=1)/10

		#/////////////////////////////////////////////////////////////////////

		divergence_pattern_15M[divergence_pattern_15M == 'buy_primary'] = 4
		divergence_pattern_15M[divergence_pattern_15M == 'buy_secondry'] = 2
		divergence_pattern_15M[divergence_pattern_15M == 'sell_primary'] = 3
		divergence_pattern_15M[divergence_pattern_15M == 'sell_secondry'] = 1
		divergence_pattern_15M[divergence_pattern_15M == 'no_trade'] = 0
		divergence_pattern_15M['macd_div'] = divergence_pattern_15M[divergence_pattern_15M.filter(regex='macd').columns].sum(axis=1)/10
		divergence_pattern_15M['stochastic_div'] = divergence_pattern_15M[divergence_pattern_15M.filter(regex='stochastic').columns].sum(axis=1)/10
		divergence_pattern_15M['rsi_div'] = divergence_pattern_15M[divergence_pattern_15M.filter(regex='rsi').columns].sum(axis=1)/10

		#/////////////////////////////////////////////////////////////////////


		divergence_pattern_1H[divergence_pattern_1H == 'buy_primary'] = 4
		divergence_pattern_1H[divergence_pattern_1H == 'buy_secondry'] = 2
		divergence_pattern_1H[divergence_pattern_1H == 'sell_primary'] = 3
		divergence_pattern_1H[divergence_pattern_1H == 'sell_secondry'] = 1
		divergence_pattern_1H[divergence_pattern_1H == 'no_trade'] = 0
		divergence_pattern_1H['macd_div'] = divergence_pattern_1H[divergence_pattern_1H.filter(regex='macd').columns].sum(axis=1)/10
		divergence_pattern_1H['stochastic_div'] = divergence_pattern_1H[divergence_pattern_1H.filter(regex='stochastic').columns].sum(axis=1)/10
		divergence_pattern_1H['rsi_div'] = divergence_pattern_1H[divergence_pattern_1H.filter(regex='rsi').columns].sum(axis=1)/10

		#/////////////////////////////////////////////////////////////////////


		divergence_pattern_4H[divergence_pattern_4H == 'buy_primary'] = 4
		divergence_pattern_4H[divergence_pattern_4H == 'buy_secondry'] = 2
		divergence_pattern_4H[divergence_pattern_4H == 'sell_primary'] = 3
		divergence_pattern_4H[divergence_pattern_4H == 'sell_secondry'] = 1
		divergence_pattern_4H[divergence_pattern_4H == 'no_trade'] = 0
		divergence_pattern_4H['macd_div'] = divergence_pattern_4H[divergence_pattern_4H.filter(regex='macd').columns].sum(axis=1)/10
		divergence_pattern_4H['stochastic_div'] = divergence_pattern_4H[divergence_pattern_4H.filter(regex='stochastic').columns].sum(axis=1)/10
		divergence_pattern_4H['rsi_div'] = divergence_pattern_4H[divergence_pattern_4H.filter(regex='rsi').columns].sum(axis=1)/10


		#/////////////////////////////////////////////////////////////////////


		divergence_pattern_1D[divergence_pattern_1D == 'buy_primary'] = 4
		divergence_pattern_1D[divergence_pattern_1D == 'buy_secondry'] = 2
		divergence_pattern_1D[divergence_pattern_1D == 'sell_primary'] = 3
		divergence_pattern_1D[divergence_pattern_1D == 'sell_secondry'] = 1
		divergence_pattern_1D[divergence_pattern_1D == 'no_trade'] = 0
		divergence_pattern_1D['macd_div'] = divergence_pattern_1D[divergence_pattern_1D.filter(regex='macd').columns].sum(axis=1)/10
		divergence_pattern_1D['stochastic_div'] = divergence_pattern_1D[divergence_pattern_1D.filter(regex='stochastic').columns].sum(axis=1)/10
		divergence_pattern_1D['rsi_div'] = divergence_pattern_1D[divergence_pattern_1D.filter(regex='rsi').columns].sum(axis=1)/10

		return divergence_pattern_5M, divergence_pattern_15M, divergence_pattern_1H, divergence_pattern_4H, divergence_pattern_1D
	#/////////////////////


	#ZigZag Patterns:
	def ZigZagPatterns(self, dataset_5M = '', percent_zigzag_finder = 0.04, profit = 0.6, symbol = 'XAUUSD_i'):

		ts_pivots = ZigZag.Find(dataset = dataset_5M, percent = percent_zigzag_finder, index_first = 0, index_last = dataset_5M.index.max() + 1)

		zigzag_patterns = pd.DataFrame(index = dataset_5M.index)
		zigzag_patterns['first_price'] = ts_pivots
		zigzag_patterns['signal_pct'] = np.nan
		zigzag_patterns['future_price'] = np.nan
		

		for point in ts_pivots.index:

			if np.isnan(ts_pivots.pct_change(-1)[point]) == True: continue

			counter = -1
			pct = pd.DataFrame(index = range(1, 100))
			pct['pct'] = np.zeros(99)

			if -ts_pivots.pct_change(-1)[point] >= 0:
				while counter > -100:
					if -ts_pivots.pct_change(counter)[point] <= 0: break
					if np.isnan(ts_pivots.pct_change(counter)[point]) == True: break
					if -ts_pivots.pct_change(counter)[point] < pct['pct'].max() * 0.5: break

					pct['pct'][-counter] = -ts_pivots.pct_change(counter)[point]
					counter -= 1
				
				zigzag_patterns['future_price'][point] = ts_pivots.shift(-pct['pct'].idxmax())[point]
				zigzag_patterns['signal_pct'][point] = pct['pct'].max()

			elif -ts_pivots.pct_change(-1)[point] < 0: 
				counter = -1
				pct = pd.DataFrame(index = range(1, 100))
				pct['pct'] = np.zeros(99)

				while counter > -100:
					if -ts_pivots.pct_change(counter)[point] >= 0: break
					if np.isnan(ts_pivots.pct_change(counter)[point]) == True: break
					if ts_pivots.pct_change(counter)[point] < -pct['pct'].min() * 0.5: break

					pct['pct'][-counter] = -ts_pivots.pct_change(counter)[point]
					counter -= 1
				
				zigzag_patterns['future_price'][point] = ts_pivots.shift(-pct['pct'].idxmin())[point]
				zigzag_patterns['signal_pct'][point] = pct['pct'].min()


		zigzag_patterns['signal'] = np.nan
		zigzag_patterns['signal'][zigzag_patterns['signal_pct'] >= (profit/100)] = 'buy'
		zigzag_patterns['signal'][zigzag_patterns['signal_pct'] <= -(profit/100)] = 'sell'

		zigzag_patterns['signal'][(
									zigzag_patterns['signal_pct'] < (profit/100)) * 
									(zigzag_patterns['signal_pct'] > -(profit/100)
									)] = 'no_trade'

		return zigzag_patterns

	#/////////////////////

	def Run(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, mode = 'Run', symbol = 'XAUUSD_i'):
		
		datasetio = DatasetIO()

		pattern_5M = pd.DataFrame(index = dataset_5M.index)
		pattern_15M = pd.DataFrame(index = dataset_15M.index)
		pattern_1H = pd.DataFrame(index = dataset_1H.index)
		pattern_4H = pd.DataFrame(index = dataset_4H.index)
		pattern_1D = pd.DataFrame(index = dataset_1D.index)


		#Color Patterns
		if self.ColorCandleFlag == True:
			color_pattern_5M, color_pattern_15M, color_pattern_1H, color_pattern_4H, color_pattern_1D = self.ColorCandle(
																														dataset_5M = dataset_5M,
																														dataset_15M = dataset_15M,
																														dataset_1H = dataset_1H,
																														dataset_4H = dataset_4H,
																														dataset_1D = dataset_1D
																														)

			pattern_5M = pattern_5M.join(color_pattern_5M, how = 'right')
			pattern_15M = pattern_15M.join(color_pattern_15M, how = 'right')
			pattern_1H = pattern_1H.join(color_pattern_1H, how = 'right')
			pattern_4H = pattern_4H.join(color_pattern_4H, how = 'right')
			pattern_1D = pattern_1D.join(color_pattern_1D, how = 'right')
		#//////////////////////////////////////

		#Daily Patterns:
		if self.DailyPatternFlag == True:
			daily_pattern_5M, daily_pattern_15M, daily_pattern_1H, daily_pattern_4H, daily_pattern_1D = self.DailyPatterns(
																															dataset_5M = dataset_5M,
																															dataset_15M = dataset_15M,
																															dataset_1H = dataset_1H,
																															dataset_4H = dataset_4H,
																															dataset_1D = dataset_1D,
																															)

			pattern_5M = pattern_5M.join(daily_pattern_5M, how = 'right')
			pattern_15M = pattern_15M.join(daily_pattern_15M, how = 'right')
			pattern_1H = pattern_1H.join(daily_pattern_1H, how = 'right')
			pattern_4H = pattern_4H.join(daily_pattern_4H, how = 'right')
			pattern_1D = pattern_1D.join(daily_pattern_1D, how = 'right')
		#//////////////////////////////////////

		#Candle Patterns:
		if self.CandlePatternFlag == True:
			candle_pattern_5M, candle_pattern_15M, candle_pattern_1H, candle_pattern_4H, candle_pattern_1D = self.CandlePatterns(
																																dataset_5M = dataset_5M,
																																dataset_15M = dataset_15M,
																																dataset_1H = dataset_1H,
																																dataset_4H = dataset_4H,
																																dataset_1D = dataset_1D,
																																)

			pattern_5M = pattern_5M.join(candle_pattern_5M, how = 'right')
			pattern_15M = pattern_15M.join(candle_pattern_15M, how = 'right')
			pattern_1H = pattern_1H.join(candle_pattern_1H, how = 'right')
			pattern_4H = pattern_4H.join(candle_pattern_4H, how = 'right')
			pattern_1D = pattern_1D.join(candle_pattern_1D, how = 'right')
		#//////////////////////////////////////


		#Number Patterns:
		if self.CandleNumberPatternFlag == True:
			number_pattern_5M, number_pattern_15M, number_pattern_1H, number_pattern_4H, number_pattern_1D = self.CandleNumberPatterns(
																																		dataset_5M = dataset_5M,
																																		dataset_15M = dataset_15M,
																																		dataset_1H = dataset_1H,
																																		dataset_4H = dataset_4H,
																																		dataset_1D = dataset_1D,
																																		)

			pattern_5M = pattern_5M.join(number_pattern_5M, how = 'right')
			pattern_15M = pattern_15M.join(number_pattern_15M, how = 'right')
			pattern_1H = pattern_1H.join(number_pattern_1H, how = 'right')
			pattern_4H = pattern_4H.join(number_pattern_4H, how = 'right')
			pattern_1D = pattern_1D.join(number_pattern_1D, how = 'right')
		#//////////////////////////////////////


		#Divergence Patterns:
		if self.DivergencePatternFlag == True:
			div_pattern_5M, div_pattern_15M, div_pattern_1H, div_pattern_4H, div_pattern_1D = self.DivergencePatterns(
																													dataset_5M = dataset_5M,
																													dataset_15M = dataset_15M,
																													dataset_1H = dataset_1H,
																													dataset_4H = dataset_4H,
																													dataset_1D = dataset_1D,
																													symbol = symbol
																													)

			pattern_5M = pattern_5M.join(div_pattern_5M, how = 'right')
			pattern_15M = pattern_15M.join(div_pattern_15M, how = 'right')
			pattern_1H = pattern_1H.join(div_pattern_1H, how = 'right')
			pattern_4H = pattern_4H.join(div_pattern_4H, how = 'right')
			pattern_1D = pattern_1D.join(div_pattern_1D, how = 'right')
		#//////////////////////////////////////

		if mode != 'online':
			datasetio.Write(type_feature = 'pattern', name = '5M' , dataset = pattern_5M, symbol = symbol)
			datasetio.Write(type_feature = 'pattern', name = '15M' , dataset = pattern_15M, symbol = symbol)
			datasetio.Write(type_feature = 'pattern', name = '1H' , dataset = pattern_1H, symbol = symbol)
			datasetio.Write(type_feature = 'pattern', name = '4H' , dataset = pattern_4H, symbol = symbol)
			datasetio.Write(type_feature = 'pattern', name = '1D' , dataset = pattern_1D, symbol = symbol)

			minmax_scaler_5M = pd.DataFrame(index = [0])
			minmax_scaler_5M['min_' + pattern_5M.columns] = pattern_5M.min()
			minmax_scaler_5M['max_' + pattern_5M.columns] = pattern_5M.max()

			minmax_scaler_15M = pd.DataFrame(index = [0])
			minmax_scaler_15M['min_' + pattern_15M.columns] = pattern_15M.min()
			minmax_scaler_15M['max_' + pattern_15M.columns] = pattern_15M.max()

			minmax_scaler_1H = pd.DataFrame(index = [0])
			minmax_scaler_1H['min_' + pattern_1H.columns] = pattern_1H.min()
			minmax_scaler_1H['max_' + pattern_1H.columns] = pattern_1H.max()

			minmax_scaler_4H = pd.DataFrame(index = [0])
			minmax_scaler_4H['min_' + pattern_4H.columns] = pattern_4H.min()
			minmax_scaler_4H['max_' + pattern_4H.columns] = pattern_4H.max()

			minmax_scaler_1D = pd.DataFrame(index = [0])
			minmax_scaler_1D['min_' + pattern_1D.columns] = pattern_1D.min()
			minmax_scaler_1D['max_' + pattern_1D.columns] = pattern_1D.max()

			datasetio.Write(type_feature = 'pattern_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
			datasetio.Write(type_feature = 'pattern_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
			datasetio.Write(type_feature = 'pattern_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
			datasetio.Write(type_feature = 'pattern_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
			datasetio.Write(type_feature = 'pattern_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')

		return pattern_5M, pattern_15M, pattern_1H, pattern_4H, pattern_1D 

	# @stTime
	def Get(
			self, 
			mode = None, 
			dataset_5M = {}, 
			dataset_15M = {}, 
			dataset_1H = {}, 
			dataset_4H = {}, 
			dataset_1D = {}, 
			symbol = 'XAUUSD_i', 
			pattern_name = '',
			timeframe = ''
			):

		#Modes:
		#online: for runnig in online trading
		#None: for reading from Hard
		#Run: for Updating and new writing on hard

		#pattern_name:
		#zigzag: for ZigZag Patterns with above Modes, Note: just Use in Oflline Mode.

		datasetio = DatasetIO()

		pattern_5M = pd.DataFrame(index = dataset_5M.index)
		pattern_15M = pd.DataFrame(index = dataset_15M.index)
		pattern_1H = pd.DataFrame(index = dataset_1H.index)
		pattern_4H = pd.DataFrame(index = dataset_4H.index)
		pattern_1D = pd.DataFrame(index = dataset_1D.index)
		
		if mode == None and pattern_name != 'zigzag':

			pattern_5M = datasetio.Read(type_feature = 'pattern', name = '5M', symbol = symbol)
			pattern_15M = datasetio.Read(type_feature = 'pattern', name = '15M', symbol = symbol)
			pattern_1H = datasetio.Read(type_feature = 'pattern', name = '1H', symbol = symbol)
			pattern_4H = datasetio.Read(type_feature = 'pattern', name = '4H', symbol = symbol)
			pattern_1D = datasetio.Read(type_feature = 'pattern', name = '1D', symbol = symbol)

			if (
				pattern_5M.empty == False and
				pattern_15M.empty == False and
				pattern_1H.empty == False and
				pattern_4H.empty == False and
				pattern_1D.empty == False
				):

				return pattern_5M, pattern_15M, pattern_1H, pattern_4H, pattern_1D

			else:
				return self.Run(
								dataset_5M = dataset_5M.copy(deep = True), 
								dataset_15M = dataset_15M.copy(deep = True),
								dataset_1H = dataset_1H.copy(deep = True),
								dataset_4H = dataset_4H.copy(deep = True),
								dataset_1D = dataset_1D.copy(deep = True),
								symbol = symbol
								)

		elif mode == 'Run' and pattern_name != 'zigzag':

			datasetio.Delete(type_feature = 'pattern', name = '5M', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern', name = '15M', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern', name = '1H', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern', name = '4H', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern', name = '1D', symbol = symbol)

			datasetio.Delete(type_feature = 'pattern_minmaxscaler', name = '5M', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern_minmaxscaler', name = '15M', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern_minmaxscaler', name = '1H', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern_minmaxscaler', name = '4H', symbol = symbol)
			datasetio.Delete(type_feature = 'pattern_minmaxscaler', name = '1D', symbol = symbol)

			return self.Run(
							dataset_5M = dataset_5M.copy(deep = True), 
							dataset_15M = dataset_15M.copy(deep = True),
							dataset_1H = dataset_1H.copy(deep = True),
							dataset_4H = dataset_4H.copy(deep = True),
							dataset_1D = dataset_1D.copy(deep = True),
							symbol = symbol
							)

		elif mode == 'online' and pattern_name != 'zigzag':

			return self.Run(
							dataset_5M = dataset_5M.copy(deep = True), 
							dataset_15M = dataset_15M.copy(deep = True),
							dataset_1H = dataset_1H.copy(deep = True),
							dataset_4H = dataset_4H.copy(deep = True),
							dataset_1D = dataset_1D.copy(deep = True),
							symbol = symbol,
							mode = mode
							)

		if pattern_name == 'zigzag':

			if timeframe == '5M':
				dataset = dataset_5M
			elif timeframe == '15M':
				dataset = dataset_15M
			elif timeframe == '1H':
				dataset = dataset_1H
			elif timeframe == '4H':
				dataset = dataset_4H
			elif timeframe == '1D':
				dataset = dataset_1D

			if mode == None:

				zigzag_patterns = datasetio.Read(type_feature = 'pattern', name = 'zigzag_' + timeframe, symbol = symbol)

				if zigzag_patterns.empty == False:

					return zigzag_patterns

				else:
					zigzag_patterns = self.ZigZagPatterns(
														dataset_5M = dataset.copy(deep = True),
														percent_zigzag_finder = self.percent_zigzag_finder,
														profit = self.profit,
														symbol = symbol
														)

					datasetio.Write(type_feature = 'pattern', name = 'zigzag_' + timeframe , dataset = zigzag_patterns, symbol = symbol)

					return zigzag_patterns

			elif mode == 'Run':

				datasetio.Delete(type_feature = 'pattern', name = 'zigzag_' + timeframe, symbol = symbol)

				zigzag_patterns = self.ZigZagPatterns(
													dataset_5M = dataset.copy(deep = True),
													percent_zigzag_finder = self.percent_zigzag_finder,
													profit = self.profit,
													symbol = symbol
													)

				datasetio.Write(type_feature = 'pattern', name = 'zigzag_' + timeframe , dataset = zigzag_patterns, symbol = symbol)

				return zigzag_patterns
			
