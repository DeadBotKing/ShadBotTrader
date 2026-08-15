from src.indicators.StochAstic.StochAstic import StochAstic
from src.utils.Tools.timer import stTime
from src.utils.Optimizers import NoiseCanceller
from .ParameterReader import ParameterReader
from src.indicators.MACD.MACD import MACD
from src.indicators.RSI.RSI import RSI
from .DatasetIO import DatasetIO
from progress.bar import Bar
from .Config import Config
import pandas_ta as ind
import pandas as pd
import numpy as np

#Functions:

#DatasetCreation()
#AlphaFactorOsilators()

#/////////////////


class MainFeatures():

	def __init__(self):

		#RSI Osilator Config:
		self.config_rsi_5m = True
		self.config_rsi_15m = True
		self.config_rsi_1h = True
		self.config_rsi_4h = True
		self.config_rsi_1d = True
		#///////////////////////

		#SMA Parameters:
		self.config_sma_5m = [True, True, True, True, True, True, True]
		self.sma_5m_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_sma_15m = [True, True, True, True, True, True, True]
		self.sma_15m_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_sma_1h = [True, True, True, True, True, True, True]
		self.sma_1h_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_sma_4h = [True, True, True, True, True, True, True]
		self.sma_4h_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_sma_1d = [True, True, True, True, True, True, True]
		self.sma_1d_length = [   5,   10,   15,   20,   25,   30,   35]
		#/////////////////////////////////////


		#EMA Parameters:
		self.config_ema_5m = [True, True, True, True, True, True, True]
		self.ema_5m_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_ema_15m = [True, True, True, True, True, True, True]
		self.ema_15m_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_ema_1h = [True, True, True, True, True, True, True]
		self.ema_1h_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_ema_4h = [True, True, True, True, True, True, True]
		self.ema_4h_length = [   5,   10,   15,   20,   25,   30,   35]

		self.config_ema_1d = [True, True, True, True, True, True, True]
		self.ema_1d_length = [   5,   10,   15,   20,   25,   30,   35]
		#/////////////////////////////////////

		#BBAND Parameters:
		self.config_bband_5m = True
		self.bband_5m_length = 5 
		self.bband_5m_std = 1 
		self.bband_5m_ddof = 0 
		self.bband_5m_mamod = 'ema'

		self.config_bband_15m = True
		self.bband_15m_length = 5 
		self.bband_15m_std = 1 
		self.bband_15m_ddof = 0 
		self.bband_15m_mamod = 'ema'

		self.config_bband_1h = True
		self.bband_1h_length = 5 
		self.bband_1h_std = 1 
		self.bband_1h_ddof = 0 
		self.bband_1h_mamod = 'ema'

		self.config_bband_4h = True
		self.bband_4h_length = 5 
		self.bband_4h_std = 1 
		self.bband_4h_ddof = 0 
		self.bband_4h_mamod = 'ema'

		self.config_bband_1d = True
		self.bband_1d_length = 5 
		self.bband_1d_std = 1 
		self.bband_1d_ddof = 0 
		self.bband_1d_mamod = 'ema'
		#/////////////////////////////////////

		#IchiMokou Parameters:
		self.config_ichi_5m = True
		self.ichi_5m_tenkan = 9
		self.ichi_5m_kijun = 26
		self.ichi_5m_senkou = 52

		self.config_ichi_15m = True
		self.ichi_15m_tenkan = 9
		self.ichi_15m_kijun = 26
		self.ichi_15m_senkou = 52

		self.config_ichi_1h = True
		self.ichi_1h_tenkan = 9
		self.ichi_1h_kijun = 26
		self.ichi_1h_senkou = 52

		self.config_ichi_4h = True
		self.ichi_4h_tenkan = 9
		self.ichi_4h_kijun = 26
		self.ichi_4h_senkou = 52

		self.config_ichi_1d = True
		self.ichi_1d_tenkan = 9
		self.ichi_1d_kijun = 26
		self.ichi_1d_senkou = 52
		#/////////////////////////////////////


		#ATR Parameters:
		self.config_atr_5m = [True, True, True, True, True, True, True]
		self.atr_5m_length = [   5,   10,   15,   20,   25,   30,   35]
		self.atr_5m_mamod =  ['ema', 'sma', 'wma', 'rma', 'tr']

		self.config_atr_15m = [True, True, True, True, True, True, True]
		self.atr_15m_length = [   5,   10,   15,   20,   25,   30,   35]
		self.atr_15m_mamod =  ['ema', 'sma', 'wma', 'rma', 'tr']

		self.config_atr_1h = [True, True, True, True, True, True, True]
		self.atr_1h_length = [   5,   10,   15,   20,   25,   30,   35]
		self.atr_1h_mamod =  ['ema', 'sma', 'wma', 'rma', 'tr']

		self.config_atr_4h = [True, True, True, True, True, True, True]
		self.atr_4h_length = [   5,   10,   15,   20,   25,   30,   35]
		self.atr_4h_mamod =  ['ema', 'sma', 'wma', 'rma', 'tr']

		self.config_atr_1d = [True, True, True, True, True, True, True]
		self.atr_1d_length = [   5,   10,   15,   20,   25,   30,   35]
		self.atr_1d_mamod =  ['ema', 'sma', 'wma', 'rma', 'tr']
		#//////////////////////////////////////

	#Main Dataset Creation:
	def DatasetCreation(self, dataset_5M, dataset_1H):

		dataset_5m = dataset_5M.copy(deep = True)
		dataset_5m.index = dataset_5m['time']

		dataset = pd.DataFrame()
		dataset = dataset.assign(
								close_5m = dataset_5m['close'],
								open_5m = dataset_5m['open'],
								low_5m = dataset_5m['low'],
								high_5m = dataset_5m['high'],
								HL2_5m = dataset_5m['HL/2'],
								HLC3_5m = dataset_5m['HLC/3'],
								HLCC4_5m = dataset_5m['HLCC/4'],
								OHLC4_5m = dataset_5m['OHLC/4'],
								volume_5m = dataset_5m['volume'],
								time_5m = dataset_5m['time'],
								)

		dataset.index = dataset['time_5m']

		dataset_1h = dataset_1H.copy(deep = True)
		dataset_1h.index = dataset_1h['time']

		dataset = dataset.assign(
								close_1h = dataset_1h['close'],
								open_1h = dataset_1h['open'],
								low_1h = dataset_1h['low'],
								high_1h = dataset_1h['high'],
								HL2_1h = dataset_1h['HL/2'],
								HLC3_1h = dataset_1h['HLC/3'],
								HLCC4_1h = dataset_1h['HLCC/4'],
								OHLC4_1h = dataset_1h['OHLC/4'],
								volume_1h = dataset_1h['volume'],
								time_1h = dataset_1h['time'],
								)

		# dataset.index = range(0 , len(dataset['close_5m']))
		return dataset 
	#/////////////////////////////////


	#Noise Filterd Feature:
	def AlphaFactorNoiseFilter(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D):

		noise_canceller = NoiseCanceller.NoiseCanceller()

		dataset_5M_ = dataset_5M.copy(deep = True)
		dataset_15M_ = dataset_15M.copy(deep = True)
		dataset_1H_ = dataset_1H.copy(deep = True)
		dataset_4H_ = dataset_4H.copy(deep = True)
		dataset_1D_ = dataset_1D.copy(deep = True)


		dataset_5M_['time'] = dataset_5M_.index
		dataset_5M_.index = range(0, len(dataset_5M_.index))

		dataset_15M_['time'] = dataset_15M_.index
		dataset_15M_.index = range(0, len(dataset_15M_.index))

		dataset_1H_['time'] = dataset_1H_.index
		dataset_1H_.index = range(0, len(dataset_1H_.index))

		dataset_4H_['time'] = dataset_4H_.index
		dataset_4H_.index = range(0, len(dataset_4H_.index))

		dataset_1D_['time'] = dataset_1D_.index
		dataset_1D_.index = range(0, len(dataset_1D_.index))

		feature_filter_5M = pd.DataFrame(index = dataset_5M.index)
		feature_filter_15M = pd.DataFrame(index = dataset_15M.index)
		feature_filter_1H = pd.DataFrame(index = dataset_1H.index)
		feature_filter_4H = pd.DataFrame(index = dataset_4H.index)
		feature_filter_1D = pd.DataFrame(index = dataset_1D.index)

		feature_filter_5M = feature_filter_5M.assign(
													close_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'close'),
													open_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'open'),
													high_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'high'),
													low_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'low'),
													HL2_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'HL/2'),
													HLC3_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'HLC/3'),
													HLCC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'HLCC/4'),
													OHLC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_5M_.copy(deep = True), applyto = 'OHLC/4'),
													)

		feature_filter_15M = feature_filter_15M.assign(
													close_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'close'),
													open_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'open'),
													high_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'high'),
													low_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'low'),
													HL2_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'HL/2'),
													HLC3_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'HLC/3'),
													HLCC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'HLCC/4'),
													OHLC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_15M_.copy(deep = True), applyto = 'OHLC/4'),
													)

		feature_filter_1H = feature_filter_1H.assign(
													close_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'close'),
													open_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'open'),
													high_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'high'),
													low_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'low'),
													HL2_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'HL/2'),
													HLC3_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'HLC/3'),
													HLCC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'HLCC/4'),
													OHLC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_1H_.copy(deep = True), applyto = 'OHLC/4'),
													)

		feature_filter_4H = feature_filter_4H.assign(
													close_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'close'),
													open_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'open'),
													high_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'high'),
													low_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'low'),
													HL2_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'HL/2'),
													HLC3_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'HLC/3'),
													HLCC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'HLCC/4'),
													OHLC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_4H_.copy(deep = True), applyto = 'OHLC/4'),
													)

		feature_filter_1D = feature_filter_1D.assign(
													close_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'close'),
													open_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'open'),
													high_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'high'),
													low_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'low'),
													HL2_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'HL/2'),
													HLC3_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'HLC/3'),
													HLCC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'HLCC/4'),
													OHLC4_filter = noise_canceller.NoiseWavelet(dataset = dataset_1D_.copy(deep = True), applyto = 'OHLC/4'),
													)

		return feature_filter_5M, feature_filter_15M, feature_filter_1H, feature_filter_4H, feature_filter_1D

	#/////////////////////////////////


	def AlphaFactorOsilators(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol):

		signalpriority = ['primary', 'secondry', 'primary', 'secondry']
		signaltype = ['buy' , 'sell', 'sell' , 'buy']
		indicator_names = ['macd', 'stochastic', 'rsi']

		parameter_reader = ParameterReader()

		dataset_5M_ = {symbol: dataset_5M.copy(deep = True)}
		dataset_15M_ = {symbol: dataset_15M.copy(deep = True)}
		dataset_1H_ = {symbol: dataset_1H.copy(deep = True)}
		dataset_4H_ = {symbol: dataset_4H.copy(deep = True)}
		dataset_1D_ = {symbol: dataset_1D.copy(deep = True)}

		feature_div_5M = pd.DataFrame(index = dataset_5M.index)
		feature_div_15M = pd.DataFrame(index = dataset_15M.index)
		feature_div_1H = pd.DataFrame(index = dataset_1H.index)
		feature_div_4H = pd.DataFrame(index = dataset_4H.index)
		feature_div_1D = pd.DataFrame(index = dataset_1D.index)

		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor Osilators Finding: ', 
																	max = int(
																			len(signalpriority) * 
																			len(signaltype) * 
																			len(indicator_names)
																			)
					)

		#5M ***************************************
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

				#Add MACD Calculate Params AS Alpha Factor To Dataset:
				if ind_name == 'macd':

					ind = MACD(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_macd()

					ind_calc['time'] = dataset_5M_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['MACD_column_div']

					ind_calc.index = ind_calc['index']
					feature_div_5M[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
					
				#///////////////////////////////////////

				#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'stochastic':

					ind = StochAstic(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_StochAstic()

					ind_calc['time'] = dataset_5M_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['StochAstic_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_5M[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]

				#//////////////////////////////////////////////////////////

				#Add RSI Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'rsi':

					ind = RSI(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_rsi()

					ind_calc['time'] = dataset_5M_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					ind_calc.index = ind_calc['index']

					feature_div_5M['rsi_' + sigtype + '_' + sigpriority] = ind_calc['rsi']

				#////////////////////////////////////////////////////////////
				if bar_config.cfg['show_bar']:
					bar.next()
		#///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////



		#15M ***************************************
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

				#Add MACD Calculate Params AS Alpha Factor To Dataset:
				if ind_name == 'macd':

					ind = MACD(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_macd()

					ind_calc['time'] = dataset_15M_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['MACD_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_15M[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#///////////////////////////////////////

				#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'stochastic':

					ind = StochAstic(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_StochAstic()

					ind_calc['time'] = dataset_15M_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['StochAstic_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_15M[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#//////////////////////////////////////////////////////////

				#Add RSI Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'rsi':

					# feature_div_15M['rsi_' + sigtype + '_' + sigpriority] = np.nan

					ind = RSI(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_rsi()

					ind_calc['time'] = dataset_15M_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					ind_calc.index = ind_calc['index']

					feature_div_15M['rsi_' + sigtype + '_' + sigpriority] = ind_calc['rsi']
				#////////////////////////////////////////////////////////////
				if bar_config.cfg['show_bar']:
					bar.next()
		#///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


		#1H ***************************************
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

				#Add MACD Calculate Params AS Alpha Factor To Dataset:
				if ind_name == 'macd':

					ind = MACD(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_macd()

					ind_calc['time'] = dataset_1H_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['MACD_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_1H[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#///////////////////////////////////////

				#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'stochastic':

					ind = StochAstic(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_StochAstic()

					ind_calc['time'] = dataset_1H_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['StochAstic_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_1H[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#//////////////////////////////////////////////////////////

				#Add RSI Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'rsi':

					ind = RSI(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_rsi()

					ind_calc['time'] = dataset_1H_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					ind_calc.index = ind_calc['index']

					feature_div_1H['rsi_' + sigtype + '_' + sigpriority] = ind_calc['rsi']
				#////////////////////////////////////////////////////////////
				if bar_config.cfg['show_bar']:
					bar.next()
		#///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

		#4H ***************************************
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

				#Add MACD Calculate Params AS Alpha Factor To Dataset:
				if ind_name == 'macd':

					ind = MACD(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_macd()

					ind_calc['time'] = dataset_4H_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['MACD_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_4H[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#///////////////////////////////////////

				#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'stochastic':

					ind = StochAstic(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_StochAstic()

					ind_calc['time'] = dataset_4H_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['StochAstic_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_4H[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#//////////////////////////////////////////////////////////

				#Add RSI Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'rsi':

					ind = RSI(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_rsi()

					ind_calc['time'] = dataset_4H_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					ind_calc.index = ind_calc['index']

					feature_div_4H['rsi_' + sigtype + '_' + sigpriority] = ind_calc['rsi']
				#////////////////////////////////////////////////////////////
				if bar_config.cfg['show_bar']:
					bar.next()
		#///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

		#1D ***************************************
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

				#Add MACD Calculate Params AS Alpha Factor To Dataset:
				if ind_name == 'macd':

					ind = MACD(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_macd()

					ind_calc['time'] = dataset_1D_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['MACD_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_1D[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#///////////////////////////////////////

				#Add StochAstic Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'stochastic':

					ind = StochAstic(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_StochAstic()

					ind_calc['time'] = dataset_1D_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					column_div = ind_parameters.elements['StochAstic_column_div']

					ind_calc.index = ind_calc['index']

					feature_div_1D[column_div + '_' + sigtype + '_' + sigpriority] = ind_calc[column_div]
				#//////////////////////////////////////////////////////////

				#Add RSI Calculate Params AS Alpha Factor To Dataset:
				elif ind_name == 'rsi':

					ind = RSI(parameters = ind_parameters, config = ind_config)
					ind_calc = ind.calculator_rsi()

					ind_calc['time'] = dataset_1D_[symbol]['time']
					ind_calc['index'] = ind_calc.index
					ind_calc.index = ind_calc['time']

					ind_calc.index = ind_calc['index']

					feature_div_1D['rsi_' + sigtype + '_' + sigpriority] = ind_calc['rsi']
				#////////////////////////////////////////////////////////////
				if bar_config.cfg['show_bar']:
					bar.next()
		#///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


		return feature_div_5M, feature_div_15M, feature_div_1H, feature_div_4H, feature_div_1D

	#Trend Factors:
	def AlphaFactorBBAND(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D):

		bband_feature_5M = pd.DataFrame(index = dataset_5M.index)
		bband_feature_15M = pd.DataFrame(index = dataset_15M.index)
		bband_feature_1H = pd.DataFrame(index = dataset_1H.index)
		bband_feature_4H = pd.DataFrame(index = dataset_4H.index)
		bband_feature_1D = pd.DataFrame(index = dataset_1D.index)

		if self.config_bband_5m == True:
			bband_ind_5m = ind.bbands(
									dataset_5M['close'], 
									length = self.bband_5m_length, #5, 
									std = self.bband_5m_std, #2, 
									ddof = self.bband_5m_ddof, #0, 
									mamod = self.bband_5m_mamod #'sma'
									)

			bband_lower_5m = bband_ind_5m[bband_ind_5m.columns[0]]
			bband_mid_5m = bband_ind_5m[bband_ind_5m.columns[1]]
			bband_upper_5m = bband_ind_5m[bband_ind_5m.columns[2]]
			# bband_bandwidth_5m = bband_ind_5m[bband_ind_5m.columns[3]]
			# bband_percent_5m = bband_ind_5m[bband_ind_5m.columns[4]]

			bband_feature_5M = bband_feature_5M.assign(
														bband_lower = bband_lower_5m,
														bband_mid = bband_mid_5m,
														bband_upper = bband_upper_5m,
														# bband_bandwidth = bband_bandwidth_5m,
														# bband_percent = bband_percent_5m,
														)

		if self.config_bband_15m == True:
			bband_ind_15m = ind.bbands(
									dataset_15M['close'], 
									length = self.bband_15m_length, #5, 
									std = self.bband_15m_std, #2, 
									ddof = self.bband_15m_ddof, #0, 
									mamod = self.bband_15m_mamod #'sma'
									)

			bband_lower_15m = bband_ind_15m[bband_ind_15m.columns[0]]
			bband_mid_15m = bband_ind_15m[bband_ind_15m.columns[1]]
			bband_upper_15m = bband_ind_15m[bband_ind_15m.columns[2]]
			# bband_bandwidth_15m = bband_ind_15m[bband_ind_15m.columns[3]]
			# bband_percent_15m = bband_ind_15m[bband_ind_15m.columns[4]]

			bband_feature_15M = bband_feature_15M.assign(
														bband_lower = bband_lower_15m,
														bband_mid = bband_mid_15m,
														bband_upper = bband_upper_15m,
														# bband_bandwidth = bband_bandwidth_15m,
														# bband_percent = bband_percent_15m,
														)


		if self.config_bband_1h == True:
			bband_ind_1h = ind.bbands(
									dataset_1H['close'].dropna(), 
									length = self.bband_1h_length, #5, 
									std = self.bband_1h_std, #2, 
									ddof = self.bband_1h_ddof, #0, 
									mamod = self.bband_1h_mamod #'sma'
									)

			bband_lower_1h = bband_ind_1h[bband_ind_1h.columns[0]]
			bband_mid_1h = bband_ind_1h[bband_ind_1h.columns[1]]
			bband_upper_1h = bband_ind_1h[bband_ind_1h.columns[2]]
			# bband_bandwidth_1h = bband_ind_1h[bband_ind_1h.columns[3]]
			# bband_percent_1h = bband_ind_1h[bband_ind_1h.columns[4]]

			bband_feature_1H = bband_feature_1H.assign(
														bband_lower = bband_lower_1h,
														bband_mid = bband_mid_1h,
														bband_upper = bband_upper_1h,
														# bband_bandwidth = bband_bandwidth_1h,
														# bband_percent = bband_percent_1h,
														)

		if self.config_bband_4h == True:
			bband_ind_4h = ind.bbands(
									dataset_4H['close'].dropna(), 
									length = self.bband_4h_length, #5, 
									std = self.bband_4h_std, #2, 
									ddof = self.bband_4h_ddof, #0, 
									mamod = self.bband_4h_mamod #'sma'
									)

			bband_lower_4h = bband_ind_1h[bband_ind_4h.columns[0]]
			bband_mid_4h = bband_ind_1h[bband_ind_4h.columns[1]]
			bband_upper_4h = bband_ind_1h[bband_ind_4h.columns[2]]
			# bband_bandwidth_4h = bband_ind_4h[bband_ind_4h.columns[3]]
			# bband_percent_4h = bband_ind_4h[bband_ind_4h.columns[4]]

			bband_feature_4H = bband_feature_4H.assign(
														bband_lower = bband_lower_4h,
														bband_mid = bband_mid_4h,
														bband_upper = bband_upper_4h,
														# bband_bandwidth = bband_bandwidth_4h,
														# bband_percent = bband_percent_4h,
														)

		if self.config_bband_1d == True:
			bband_ind_1d = ind.bbands(
									dataset_1D['close'].dropna(), 
									length = self.bband_1d_length, #5, 
									std = self.bband_1d_std, #2, 
									ddof = self.bband_1d_ddof, #0, 
									mamod = self.bband_1d_mamod #'sma'
									)

			bband_lower_1d = bband_ind_1d[bband_ind_1d.columns[0]]
			bband_mid_1d = bband_ind_1d[bband_ind_1d.columns[1]]
			bband_upper_1d = bband_ind_1d[bband_ind_1d.columns[2]]
			# bband_bandwidth_1d = bband_ind_1d[bband_ind_1d.columns[3]]
			# bband_percent_1d = bband_ind_1d[bband_ind_1d.columns[4]]

			bband_feature_1D = bband_feature_1D.assign(
														bband_lower = bband_lower_1d,
														bband_mid = bband_mid_1d,
														bband_upper = bband_upper_1d,
														# bband_bandwidth = bband_bandwidth_1d,
														# bband_percent = bband_percent_1d,
														)



		return bband_feature_5M, bband_feature_15M, bband_feature_1H, bband_feature_4H, bband_feature_1D

	def AlphaFactorSMA(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D):

		sma_feature_5M = pd.DataFrame(index = dataset_5M.index)
		sma_feature_15M = pd.DataFrame(index = dataset_15M.index)
		sma_feature_1H = pd.DataFrame(index = dataset_1H.index)
		sma_feature_4H = pd.DataFrame(index = dataset_4H.index)
		sma_feature_1D = pd.DataFrame(index = dataset_1D.index)

		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor SMA 5M Finding: ', 
						max = int(len(self.config_sma_5m))
					)

		#5M ******************:
		counter = 0
		for elm in self.config_sma_5m:

			if elm == True:
				sma_ind_5m = ind.sma(dataset_5M['close'], length = self.sma_5m_length[counter])

				sma_feature_5M[f'sma_{self.sma_5m_length[counter]}'] = sma_ind_5m

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#//////////////////////////////////

		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor SMA 15M Finding: ', 
						max = int(len(self.config_sma_15m))
					)

		#15M ******************:
		counter = 0
		for elm in self.config_sma_15m:

			if elm == True:
				sma_ind_15m = ind.sma(dataset_15M['close'], length = self.sma_15m_length[counter])

				sma_feature_15M[f'sma_{self.sma_15m_length[counter]}'] = sma_ind_15m

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#//////////////////////////////////


		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor SMA 1H Finding: ', 
						max = int(len(self.config_sma_1h))
					)

		#1H ************:
		counter = 0
		for elm in self.config_sma_1h:

			if elm == True:
				sma_ind_1h = ind.sma(dataset_1H['close'].dropna(), length = self.sma_1h_length[counter])

				sma_feature_1H[f'sma_{self.sma_1h_length[counter]}'] = sma_ind_1h

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#//////////////////////////////

		#4H ************:
		counter = 0
		for elm in self.config_sma_4h:

			if elm == True:
				sma_ind_4h = ind.sma(dataset_4H['close'].dropna(), length = self.sma_4h_length[counter])

				sma_feature_4H[f'sma_{self.sma_4h_length[counter]}'] = sma_ind_4h

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#//////////////////////////////

		#1H ************:
		counter = 0
		for elm in self.config_sma_1d:

			if elm == True:
				sma_ind_1d = ind.sma(dataset_1D['close'].dropna(), length = self.sma_1d_length[counter])

				sma_feature_1D[f'sma_{self.sma_1d_length[counter]}'] = sma_ind_1d

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#//////////////////////////////
		
		return sma_feature_5M, sma_feature_15M, sma_feature_1H, sma_feature_4H, sma_feature_1D

	def AlphaFactorEMA(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D):


		ema_feature_5M = pd.DataFrame(index = dataset_5M.index)
		ema_feature_15M = pd.DataFrame(index = dataset_15M.index)
		ema_feature_1H = pd.DataFrame(index = dataset_1H.index)
		ema_feature_4H = pd.DataFrame(index = dataset_4H.index)
		ema_feature_1D = pd.DataFrame(index = dataset_1D.index)

		#5M *********************:
		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor EMA 5M Finding: ', 
						max = int(len(self.config_ema_5m))
					)

		counter = 0
		for elm in self.config_ema_5m:

			if elm == True:

				ema_ind_5m = ind.ema(dataset_5M['close'], length = self.ema_5m_length[counter])

				ema_feature_5M[f'ema_{self.ema_5m_length[counter]}'] = ema_ind_5m

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#////////////////////////////////



		#15M *********************:
		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor EMA 15M Finding: ', 
						max = int(len(self.config_ema_5m))
					)

		counter = 0
		for elm in self.config_ema_15m:

			if elm == True:

				ema_ind_15m = ind.ema(dataset_15M['close'], length = self.ema_15m_length[counter])

				ema_feature_15M[f'ema_{self.ema_15m_length[counter]}'] = ema_ind_15m

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#////////////////////////////////


		#1H *********************:
		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor EMA 1H Finding: ', 
						max = int(len(self.config_ema_1h))
					)

		counter = 0
		for elm in self.config_ema_1h:

			if elm == True:

				ema_ind_1h = ind.ema(dataset_1H['close'].dropna(), length = self.ema_1h_length[counter])

				ema_feature_1H[f'ema_{self.ema_1h_length[counter]}'] = ema_ind_1h

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#////////////////////////////////////

		#1H *********************:
		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor EMA 4H Finding: ', 
						max = int(len(self.config_ema_4h))
					)

		counter = 0
		for elm in self.config_ema_4h:

			if elm == True:

				ema_ind_4h = ind.ema(dataset_4H['close'].dropna(), length = self.ema_4h_length[counter])

				ema_feature_4H[f'ema_{self.ema_4h_length[counter]}'] = ema_ind_4h

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#////////////////////////////////////

		#1H *********************:
		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(
						symbol + ' ' + 'Alpha Factor EMA 1D Finding: ', 
						max = int(len(self.config_ema_1d))
					)

		counter = 0
		for elm in self.config_ema_1d:

			if elm == True:

				ema_ind_1d = ind.ema(dataset_1D['close'].dropna(), length = self.ema_1d_length[counter])

				ema_feature_1D[f'ema_{self.ema_1d_length[counter]}'] = ema_ind_1d

			counter += 1

			if bar_config.cfg['show_bar']: bar.next()
		#////////////////////////////////////

		return ema_feature_5M, ema_feature_15M, ema_feature_1H, ema_feature_4H, ema_feature_1D

	def AlphaFactorIchimokou(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D):

		ichi_feature_5M = pd.DataFrame(index = dataset_5M.index)
		ichi_feature_15M = pd.DataFrame(index = dataset_15M.index)
		ichi_feature_1H = pd.DataFrame(index = dataset_1H.index)
		ichi_feature_4H = pd.DataFrame(index = dataset_4H.index)
		ichi_feature_1D = pd.DataFrame(index = dataset_1D.index)

		#5M *************:
		if self.config_ichi_5m == True:

			ichi_ind_5m, _ = ind.ichimoku(
										high = dataset_5M['high'],
										low = dataset_5M['low'],
										close = dataset_5M['close'],
										tenkan = self.ichi_5m_tenkan,
										kijun = self.ichi_5m_kijun,
										senkou = self.ichi_5m_senkou
										)

			spana_5m = ichi_ind_5m[ichi_ind_5m.columns[0]]
			spanb_5m = ichi_ind_5m[ichi_ind_5m.columns[1]]
			tenkan_5m = ichi_ind_5m[ichi_ind_5m.columns[2]]
			kijun_5m = ichi_ind_5m[ichi_ind_5m.columns[3]]
			chikou_5m = ichi_ind_5m[ichi_ind_5m.columns[4]]

			ichi_feature_5M = ichi_feature_5M.assign(
													spana = spana_5m,
													spanb = spanb_5m,
													tenkan = tenkan_5m,
													kijun = kijun_5m,
													chikou = chikou_5m,
													)
			ichi_feature_5M['chikou'] = ichi_feature_5M['chikou'].shift(self.ichi_5m_kijun)
		#/////////////////////////////////////////////


		#15M *************:
		if self.config_ichi_15m == True:

			ichi_ind_15m, _ = ind.ichimoku(
										high = dataset_15M['high'],
										low = dataset_15M['low'],
										close = dataset_15M['close'],
										tenkan = self.ichi_15m_tenkan,
										kijun = self.ichi_15m_kijun,
										senkou = self.ichi_15m_senkou
										)

			spana_15m = ichi_ind_15m[ichi_ind_15m.columns[0]]
			spanb_15m = ichi_ind_15m[ichi_ind_15m.columns[1]]
			tenkan_15m = ichi_ind_15m[ichi_ind_15m.columns[2]]
			kijun_15m = ichi_ind_15m[ichi_ind_15m.columns[3]]
			chikou_15m = ichi_ind_15m[ichi_ind_15m.columns[4]]

			ichi_feature_15M = ichi_feature_15M.assign(
													spana = spana_15m,
													spanb = spanb_15m,
													tenkan = tenkan_15m,
													kijun = kijun_15m,
													chikou = chikou_15m,
													)

			ichi_feature_15M['chikou'] = ichi_feature_15M['chikou'].shift(self.ichi_15m_kijun)
		#/////////////////////////////////////////////


		#1H *******************:
		if self.config_ichi_1h == True:

			ichi_ind_1h, _ = ind.ichimoku(
										high = dataset_1H['high'].dropna(),
										low = dataset_1H['low'].dropna(),
										close = dataset_1H['close'].dropna(),
										tenkan = self.ichi_1h_tenkan,
										kijun = self.ichi_1h_kijun,
										senkou = self.ichi_1h_senkou
										)

			spana_1h = ichi_ind_1h[ichi_ind_1h.columns[0]]
			spanb_1h = ichi_ind_1h[ichi_ind_1h.columns[1]]
			tenkan_1h = ichi_ind_1h[ichi_ind_1h.columns[2]]
			kijun_1h = ichi_ind_1h[ichi_ind_1h.columns[3]]
			chikou_1h = ichi_ind_1h[ichi_ind_1h.columns[4]]

			ichi_feature_1H = ichi_feature_1H.assign(
													spana = spana_1h,
													spanb = spanb_1h,
													tenkan = tenkan_1h,
													kijun = kijun_1h,
													chikou = chikou_1h,
													)

			ichi_feature_1H['chikou'] = ichi_feature_1H['chikou'].shift(self.ichi_1h_kijun)
		#/////////////////////////////////

		#4H *******************:
		if self.config_ichi_1h == True:

			ichi_ind_4h, _ = ind.ichimoku(
										high = dataset_4H['high'].dropna(),
										low = dataset_4H['low'].dropna(),
										close = dataset_4H['close'].dropna(),
										tenkan = self.ichi_4h_tenkan,
										kijun = self.ichi_4h_kijun,
										senkou = self.ichi_4h_senkou
										)

			spana_4h = ichi_ind_4h[ichi_ind_4h.columns[0]]
			spanb_4h = ichi_ind_4h[ichi_ind_4h.columns[1]]
			tenkan_4h = ichi_ind_4h[ichi_ind_4h.columns[2]]
			kijun_4h = ichi_ind_4h[ichi_ind_4h.columns[3]]
			chikou_4h = ichi_ind_4h[ichi_ind_4h.columns[4]]

			ichi_feature_4H = ichi_feature_4H.assign(
													spana = spana_4h,
													spanb = spanb_4h,
													tenkan = tenkan_4h,
													kijun = kijun_4h,
													chikou = chikou_4h,
													)

			ichi_feature_4H['chikou'] = ichi_feature_4H['chikou'].shift(self.ichi_4h_kijun)
		#/////////////////////////////////


		#1D *******************:
		if self.config_ichi_1d == True:

			ichi_ind_1d, _ = ind.ichimoku(
										high = dataset_1D['high'].dropna(),
										low = dataset_1D['low'].dropna(),
										close = dataset_1D['close'].dropna(),
										tenkan = self.ichi_1d_tenkan,
										kijun = self.ichi_1d_kijun,
										senkou = self.ichi_1d_senkou
										)

			spana_1d = ichi_ind_1d[ichi_ind_1d.columns[0]]
			spanb_1d = ichi_ind_1d[ichi_ind_1d.columns[1]]
			tenkan_1d = ichi_ind_1d[ichi_ind_1d.columns[2]]
			kijun_1d = ichi_ind_1d[ichi_ind_1d.columns[3]]
			chikou_1d = ichi_ind_1d[ichi_ind_1d.columns[4]]

			ichi_feature_1D = ichi_feature_1D.assign(
													spana = spana_1d,
													spanb = spanb_1d,
													tenkan = tenkan_1d,
													kijun = kijun_1d,
													chikou = chikou_1d,
													)

			ichi_feature_1D['chikou'] = ichi_feature_1D['chikou'].shift(self.ichi_1d_kijun)
		#/////////////////////////////////


		return ichi_feature_5M, ichi_feature_15M, ichi_feature_1H, ichi_feature_4H, ichi_feature_1D
	#//////////////////////////////////////////////////////


	#ATR Factor:
	def AlphaFactorATR(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D):

		atr_feature_5M = pd.DataFrame(index = dataset_5M.index)
		atr_feature_15M = pd.DataFrame(index = dataset_15M.index)
		atr_feature_1H = pd.DataFrame(index = dataset_1H.index)
		atr_feature_4H = pd.DataFrame(index = dataset_4H.index)
		atr_feature_1D = pd.DataFrame(index = dataset_1D.index)

		#5M ***********:
		counter = 0
		for elm in self.config_atr_5m:

			if elm == True:

				for mamod in self.atr_5m_mamod:

					ind_atr_5M = ind.atr(
										high = dataset_5M['high'],
										low = dataset_5M['low'],
										close = dataset_5M['close'],
										length = self.atr_5m_length[counter],
										mamod = mamod
										)

				atr_feature_5M[f'atr_{mamod}_{self.atr_5m_length[counter]}'] = ind_atr_5M

			counter += 1
		#/////////////////////

		#15M ***********:
		counter = 0
		for elm in self.config_atr_15m:

			if elm == True:

				for mamod in self.atr_15m_mamod:

					ind_atr_15M = ind.atr(
										high = dataset_15M['high'],
										low = dataset_15M['low'],
										close = dataset_15M['close'],
										length = self.atr_15m_length[counter],
										mamod = mamod
										)

				atr_feature_15M[f'atr_{mamod}_{self.atr_15m_length[counter]}'] = ind_atr_15M

			counter += 1
		#/////////////////////

		#1H ***********:
		counter = 0
		for elm in self.config_atr_1h:

			if elm == True:

				for mamod in self.atr_1h_mamod:

					ind_atr_1H = ind.atr(
										high = dataset_1H['high'],
										low = dataset_1H['low'],
										close = dataset_1H['close'],
										length = self.atr_1h_length[counter],
										mamod = mamod
										)

				atr_feature_1H[f'atr_{mamod}_{self.atr_1h_length[counter]}'] = ind_atr_1H

			counter += 1
		#/////////////////////

		#4H ***********:
		counter = 0
		for elm in self.config_atr_4h:

			if elm == True:

				for mamod in self.atr_4h_mamod:

					ind_atr_4H = ind.atr(
										high = dataset_4H['high'],
										low = dataset_4H['low'],
										close = dataset_4H['close'],
										length = self.atr_4h_length[counter],
										mamod = mamod
										)

				atr_feature_4H[f'atr_{mamod}_{self.atr_4h_length[counter]}'] = ind_atr_4H

			counter += 1
		#/////////////////////

		#1D ***********:
		counter = 0
		for elm in self.config_atr_1d:

			if elm == True:

				for mamod in self.atr_1d_mamod:

					ind_atr_1D = ind.atr(
										high = dataset_1D['high'],
										low = dataset_1D['low'],
										close = dataset_1D['close'],
										length = self.atr_1d_length[counter],
										mamod = mamod
										)

				atr_feature_1D[f'atr_{mamod}_{self.atr_1d_length[counter]}'] = ind_atr_1D

			counter += 1
		#/////////////////////

		return atr_feature_5M, atr_feature_15M, atr_feature_1H, atr_feature_4H, atr_feature_1D

	#//////////////////////////////////////////////////////


	def Run(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol):
		
		# dataset = self.DatasetCreation(dataset_5M = dataset_5M[symbol], dataset_1H = dataset_1H[symbol])

		main_feature_5M = pd.DataFrame(index = dataset_5M.index)
		main_feature_15M = pd.DataFrame(index = dataset_15M.index)
		main_feature_1H = pd.DataFrame(index = dataset_1H.index)
		main_feature_4H = pd.DataFrame(index = dataset_4H.index)
		main_feature_1D = pd.DataFrame(index = dataset_1D.index)


		filter_feature_5M, filter_feature_15M, filter_feature_1H, filter_feature_4H, filter_feature_1D = self.AlphaFactorNoiseFilter(
																																	dataset_5M = dataset_5M,
																																	dataset_15M = dataset_15M,
																																	dataset_1H = dataset_1H,
																																	dataset_4H = dataset_4H,
																																	dataset_1D = dataset_1D
																																	)

		main_feature_5M = main_feature_5M.join(filter_feature_5M, how = 'right')
		main_feature_15M = main_feature_15M.join(filter_feature_15M, how = 'right')
		main_feature_1H = main_feature_1H.join(filter_feature_1H, how = 'right')
		main_feature_4H = main_feature_4H.join(filter_feature_4H, how = 'right')
		main_feature_1D = main_feature_1D.join(filter_feature_1D, how = 'right')


		osc_feature_5M, osc_feature_15M, osc_feature_1H, osc_feature_4H, osc_feature_1D = self.AlphaFactorOsilators(
																													dataset_5M = dataset_5M,
																													dataset_15M = dataset_15M,
																													dataset_1H = dataset_1H,
																													dataset_4H = dataset_4H,
																													dataset_1D = dataset_1D,
																													symbol = symbol
																													)

		main_feature_5M = main_feature_5M.join(osc_feature_5M, how = 'right')
		main_feature_15M = main_feature_15M.join(osc_feature_15M, how = 'right')
		main_feature_1H = main_feature_1H.join(osc_feature_1H, how = 'right')
		main_feature_4H = main_feature_4H.join(osc_feature_4H, how = 'right')
		main_feature_1D = main_feature_1D.join(osc_feature_1D, how = 'right')


		bband_feature_5M, bband_feature_15M, bband_feature_1H, bband_feature_4H, bband_feature_1D = self.AlphaFactorBBAND(
																														dataset_5M = dataset_5M,
																														dataset_15M = dataset_15M,
																														dataset_1H = dataset_1H,
																														dataset_4H = dataset_4H,
																														dataset_1D = dataset_1D
																														)

		main_feature_5M = main_feature_5M.join(bband_feature_5M, how = 'right')
		main_feature_15M = main_feature_15M.join(bband_feature_15M, how = 'right')
		main_feature_1H = main_feature_1H.join(bband_feature_1H, how = 'right')
		main_feature_4H = main_feature_4H.join(bband_feature_4H, how = 'right')
		main_feature_1D = main_feature_1D.join(bband_feature_1D, how = 'right')


		sma_feature_5M, sma_feature_15M, sma_feature_1H, sma_feature_4H, sma_feature_1D = self.AlphaFactorSMA(
																											dataset_5M = dataset_5M,
																											dataset_15M = dataset_15M,
																											dataset_1H = dataset_1H,
																											dataset_4H = dataset_4H,
																											dataset_1D = dataset_1D
																											)

		main_feature_5M = main_feature_5M.join(sma_feature_5M, how = 'right')
		main_feature_15M = main_feature_15M.join(sma_feature_15M, how = 'right')
		main_feature_1H = main_feature_1H.join(sma_feature_1H, how = 'right')
		main_feature_4H = main_feature_4H.join(sma_feature_4H, how = 'right')
		main_feature_1D = main_feature_1D.join(sma_feature_1D, how = 'right')


		ema_feature_5M, ema_feature_15M, ema_feature_1H, ema_feature_4H, ema_feature_1D = self.AlphaFactorEMA(
																											dataset_5M = dataset_5M,
																											dataset_15M = dataset_15M,
																											dataset_1H = dataset_1H,
																											dataset_4H = dataset_4H,
																											dataset_1D = dataset_1D
																											)

		main_feature_5M = main_feature_5M.join(ema_feature_5M, how = 'right')
		main_feature_15M = main_feature_15M.join(ema_feature_15M, how = 'right')
		main_feature_1H = main_feature_1H.join(ema_feature_1H, how = 'right')
		main_feature_4H = main_feature_4H.join(ema_feature_4H, how = 'right')
		main_feature_1D = main_feature_1D.join(ema_feature_1D, how = 'right')


		ichi_feature_5M, ichi_feature_15M, ichi_feature_1H, ichi_feature_4H, ichi_feature_1D = self.AlphaFactorIchimokou(
																														dataset_5M = dataset_5M,
																														dataset_15M = dataset_15M,
																														dataset_1H = dataset_1H,
																														dataset_4H = dataset_4H,
																														dataset_1D = dataset_1D
																														)

		main_feature_5M = main_feature_5M.join(ichi_feature_5M, how = 'right')
		main_feature_15M = main_feature_15M.join(ichi_feature_15M, how = 'right')
		main_feature_1H = main_feature_1H.join(ichi_feature_1H, how = 'right')
		main_feature_4H = main_feature_4H.join(ichi_feature_4H, how = 'right')
		main_feature_1D = main_feature_1D.join(ichi_feature_1D, how = 'right')


		atr_feature_5M, atr_feature_15M, atr_feature_1H, atr_feature_4H, atr_feature_1D = self.AlphaFactorATR(
																											dataset_5M = dataset_5M,
																											dataset_15M = dataset_15M,
																											dataset_1H = dataset_1H,
																											dataset_4H = dataset_4H,
																											dataset_1D = dataset_1D
																											)

		main_feature_5M = main_feature_5M.join(atr_feature_5M, how = 'right')
		main_feature_15M = main_feature_15M.join(atr_feature_15M, how = 'right')
		main_feature_1H = main_feature_1H.join(atr_feature_1H, how = 'right')
		main_feature_4H = main_feature_4H.join(atr_feature_4H, how = 'right')
		main_feature_1D = main_feature_1D.join(atr_feature_1D, how = 'right')

		return main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D

	# @stTime
	def Get(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol = 'XAUUSD_i', mode = None):
		
		datasetio = DatasetIO()

		if mode == None:

			main_feature_5M = datasetio.Read(type_feature = 'main_features', symbol = symbol, name = '5M')
			main_feature_15M = datasetio.Read(type_feature = 'main_features', symbol = symbol, name = '15M')
			main_feature_1H = datasetio.Read(type_feature = 'main_features', symbol = symbol, name = '1H')
			main_feature_4H = datasetio.Read(type_feature = 'main_features', symbol = symbol, name = '4H')
			main_feature_1D = datasetio.Read(type_feature = 'main_features', symbol = symbol, name = '1D')

			if (
				main_feature_5M.empty == False and
				main_feature_15M.empty == False and
				main_feature_1H.empty == False and
				main_feature_4H.empty == False and
				main_feature_1D.empty == False
				):
				return main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D

			else:
				main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D = self.Run(
																												symbol = symbol, 
																												dataset_5M = dataset_5M, 
																												dataset_15M = dataset_15M,
																												dataset_1H = dataset_1H,
																												dataset_4H = dataset_4H,
																												dataset_1D = dataset_1D
																												)

				datasetio.Write(type_feature = 'main_features', dataset = main_feature_5M, symbol = symbol, name = '5M')
				datasetio.Write(type_feature = 'main_features', dataset = main_feature_15M, symbol = symbol, name = '15M')
				datasetio.Write(type_feature = 'main_features', dataset = main_feature_1H, symbol = symbol, name = '1H')
				datasetio.Write(type_feature = 'main_features', dataset = main_feature_4H, symbol = symbol, name = '4H')
				datasetio.Write(type_feature = 'main_features', dataset = main_feature_1D, symbol = symbol, name = '1D')

				minmax_scaler_5M = pd.DataFrame(index = [0])
				minmax_scaler_5M['min_' + main_feature_5M.columns] = main_feature_5M.min()
				minmax_scaler_5M['max_' + main_feature_5M.columns] = main_feature_5M.max()

				minmax_scaler_15M = pd.DataFrame(index = [0])
				minmax_scaler_15M['min_' + main_feature_15M.columns] = main_feature_15M.min()
				minmax_scaler_15M['max_' + main_feature_15M.columns] = main_feature_15M.max()

				minmax_scaler_1H = pd.DataFrame(index = [0])
				minmax_scaler_1H['min_' + main_feature_1H.columns] = main_feature_1H.min()
				minmax_scaler_1H['max_' + main_feature_1H.columns] = main_feature_1H.max()

				minmax_scaler_4H = pd.DataFrame(index = [0])
				minmax_scaler_4H['min_' + main_feature_4H.columns] = main_feature_4H.min()
				minmax_scaler_4H['max_' + main_feature_4H.columns] = main_feature_4H.max()

				minmax_scaler_1D = pd.DataFrame(index = [0])
				minmax_scaler_1D['min_' + main_feature_1D.columns] = main_feature_1D.min()
				minmax_scaler_1D['max_' + main_feature_1D.columns] = main_feature_1D.max()

				datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
				datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
				datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
				datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
				datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')

				#Write Main Dataset Min Max Scaler:
				minmax_scaler_5M = pd.DataFrame(index = [0])
				minmax_scaler_5M['min_' + dataset_5M.columns] = dataset_5M.min()
				minmax_scaler_5M['max_' + dataset_5M.columns] = dataset_5M.max()

				minmax_scaler_15M = pd.DataFrame(index = [0])
				minmax_scaler_15M['min_' + dataset_15M.columns] = dataset_15M.min()
				minmax_scaler_15M['max_' + dataset_15M.columns] = dataset_15M.max()

				minmax_scaler_1H = pd.DataFrame(index = [0])
				minmax_scaler_1H['min_' + dataset_1H.columns] = dataset_1H.min()
				minmax_scaler_1H['max_' + dataset_1H.columns] = dataset_1H.max()

				minmax_scaler_4H = pd.DataFrame(index = [0])
				minmax_scaler_4H['min_' + dataset_4H.columns] = dataset_4H.min()
				minmax_scaler_4H['max_' + dataset_4H.columns] = dataset_4H.max()

				minmax_scaler_1D = pd.DataFrame(index = [0])
				minmax_scaler_1D['min_' + dataset_1D.columns] = dataset_1D.min()
				minmax_scaler_1D['max_' + dataset_1D.columns] = dataset_1D.max()

				datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
				datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
				datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
				datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
				datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')
				#//////////////////////////////////////////////////

				return main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D

		elif mode == 'Run':

			datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '5M')
			datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '15M')
			datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '1H')
			datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '4H')
			datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '1D')


			datasetio.Delete(type_feature = 'main_features_minmaxscaler', symbol = symbol, name = '5M')
			datasetio.Delete(type_feature = 'main_features_minmaxscaler', symbol = symbol, name = '15M')
			datasetio.Delete(type_feature = 'main_features_minmaxscaler', symbol = symbol, name = '1H')
			datasetio.Delete(type_feature = 'main_features_minmaxscaler', symbol = symbol, name = '4H')
			datasetio.Delete(type_feature = 'main_features_minmaxscaler', symbol = symbol, name = '1D')

			datasetio.Delete(type_feature = 'main_minmaxscaler', symbol = symbol, name = '5M')
			datasetio.Delete(type_feature = 'main_minmaxscaler', symbol = symbol, name = '15M')
			datasetio.Delete(type_feature = 'main_minmaxscaler', symbol = symbol, name = '1H')
			datasetio.Delete(type_feature = 'main_minmaxscaler', symbol = symbol, name = '4H')
			datasetio.Delete(type_feature = 'main_minmaxscaler', symbol = symbol, name = '1D')

			main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D = self.Run(
																											symbol = symbol, 
																											dataset_5M = dataset_5M, 
																											dataset_15M = dataset_15M,
																											dataset_1H = dataset_1H,
																											dataset_4H = dataset_4H,
																											dataset_1D = dataset_1D
																											)

			datasetio.Write(type_feature = 'main_features', dataset = main_feature_5M, symbol = symbol, name = '5M')
			datasetio.Write(type_feature = 'main_features', dataset = main_feature_15M, symbol = symbol, name = '15M')
			datasetio.Write(type_feature = 'main_features', dataset = main_feature_1H, symbol = symbol, name = '1H')
			datasetio.Write(type_feature = 'main_features', dataset = main_feature_4H, symbol = symbol, name = '4H')
			datasetio.Write(type_feature = 'main_features', dataset = main_feature_1D, symbol = symbol, name = '1D')

			minmax_scaler_5M = pd.DataFrame(index = [0])
			minmax_scaler_5M['min_' + main_feature_5M.columns] = main_feature_5M.min()
			minmax_scaler_5M['max_' + main_feature_5M.columns] = main_feature_5M.max()

			minmax_scaler_15M = pd.DataFrame(index = [0])
			minmax_scaler_15M['min_' + main_feature_15M.columns] = main_feature_15M.min()
			minmax_scaler_15M['max_' + main_feature_15M.columns] = main_feature_15M.max()

			minmax_scaler_1H = pd.DataFrame(index = [0])
			minmax_scaler_1H['min_' + main_feature_1H.columns] = main_feature_1H.min()
			minmax_scaler_1H['max_' + main_feature_1H.columns] = main_feature_1H.max()

			minmax_scaler_4H = pd.DataFrame(index = [0])
			minmax_scaler_4H['min_' + main_feature_4H.columns] = main_feature_4H.min()
			minmax_scaler_4H['max_' + main_feature_4H.columns] = main_feature_4H.max()

			minmax_scaler_1D = pd.DataFrame(index = [0])
			minmax_scaler_1D['min_' + main_feature_1D.columns] = main_feature_1D.min()
			minmax_scaler_1D['max_' + main_feature_1D.columns] = main_feature_1D.max()

			datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
			datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
			datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
			datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
			datasetio.Write(type_feature = 'main_features_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')

			#Write Main Dataset Min Max Scaler:
			minmax_scaler_5M = pd.DataFrame(index = [0])
			minmax_scaler_5M['min_' + dataset_5M.columns] = dataset_5M.min()
			minmax_scaler_5M['max_' + dataset_5M.columns] = dataset_5M.max()

			minmax_scaler_15M = pd.DataFrame(index = [0])
			minmax_scaler_15M['min_' + dataset_15M.columns] = dataset_15M.min()
			minmax_scaler_15M['max_' + dataset_15M.columns] = dataset_15M.max()

			minmax_scaler_1H = pd.DataFrame(index = [0])
			minmax_scaler_1H['min_' + dataset_1H.columns] = dataset_1H.min()
			minmax_scaler_1H['max_' + dataset_1H.columns] = dataset_1H.max()

			minmax_scaler_4H = pd.DataFrame(index = [0])
			minmax_scaler_4H['min_' + dataset_4H.columns] = dataset_4H.min()
			minmax_scaler_4H['max_' + dataset_4H.columns] = dataset_4H.max()

			minmax_scaler_1D = pd.DataFrame(index = [0])
			minmax_scaler_1D['min_' + dataset_1D.columns] = dataset_1D.min()
			minmax_scaler_1D['max_' + dataset_1D.columns] = dataset_1D.max()

			datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
			datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
			datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
			datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
			datasetio.Write(type_feature = 'main_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')
			#//////////////////////////////////////////////////

			return main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D

		elif mode == 'online':

			main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D = self.Run(
																											symbol = symbol, 
																											dataset_5M = dataset_5M, 
																											dataset_15M = dataset_15M,
																											dataset_1H = dataset_1H,
																											dataset_4H = dataset_4H,
																											dataset_1D = dataset_1D
																											)

			return main_feature_5M, main_feature_15M, main_feature_1H, main_feature_4H, main_feature_1D
