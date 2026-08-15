from src.utils.FeatureEngineering.FourierFeatures import FourierFeatures
from src.utils.FeatureEngineering.BalanceFeature import BalanceFeature
from src.utils.FeatureEngineering.MainFeatures import MainFeatures
from src.utils.FeatureEngineering.MinMaxScaler import MinMaxScaler
from src.utils.FeatureEngineering.LagFeatures import LagFeatures
from src.utils.FeatureEngineering.Patterns import Patterns
from src.utils.FeatureEngineering.PCAMI import PCAMI
from src.utils.Tools.timer import stTime
from .DatasetIO import DatasetIO
from .Config import Config
import pandas as pd
import sys
import os

if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'



class FeatureEngineering:

	def __init__(self):

		self.main_features_flag = True
		self.pca_features_flag = True
		self.lag_features_flag = True
		self.pattern_features_flag = True

		self.fourier_features_flag = {
										'main': True,
										'5M': True,
										'15M': True,
										'1H': True,
										'4H': True,
										'1D': True,
										}

		self.balance_feature_flag = True

	def DataJoiner(
					self, 
					dataset_5M, 
					dataset_15M, 
					dataset_1H,
					dataset_4H,
					dataset_1D,
					feature_engineering_5M, 
					feature_engineering_15M, 
					feature_engineering_1H,  
					feature_engineering_4H,  
					feature_engineering_1D,  
					symbol,
					scale,
					name_feature
					):

		if scale == True: minmax_scaler = MinMaxScaler()

		if scale == True:
			scale_main_5M, scale_main_15M, scale__main_1H, scale__main_4H, scale__main_1D = minmax_scaler(
																										dataset_5M = dataset_5M, 
																										dataset_15M = dataset_15M, 
																										dataset_1H = dataset_1H, 
																										dataset_4H = dataset_4H,
																										dataset_1D = dataset_1D,
																										name_feature = name_feature, 
																										symbol = symbol
																										)
		else:
			scale_main_5M = dataset_5M.copy(deep = True) 
			scale_main_15M = dataset_15M.copy(deep = True)
			scale__main_1H = dataset_1H.copy(deep = True)
			scale__main_4H = dataset_4H.copy(deep = True)
			scale__main_1D = dataset_1D.copy(deep = True)

		feature_engineering_5M = feature_engineering_5M.join(scale_main_5M.copy(deep = True), how = 'right')
		feature_engineering_15M = feature_engineering_15M.join(scale_main_15M.copy(deep = True), how = 'right')
		feature_engineering_1H = feature_engineering_1H.join(scale__main_1H.copy(deep = True), how = 'right')
		feature_engineering_4H = feature_engineering_4H.join(scale__main_4H.copy(deep = True), how = 'right')
		feature_engineering_1D = feature_engineering_1D.join(scale__main_1D.copy(deep = True), how = 'right')

		return feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D



	def Run(
			self, 
			dataset_5M, 
			dataset_15M, 
			dataset_1H, 
			dataset_4H, 
			dataset_1D, 
			symbol = 'XAUUSD_i', 
			mode = None, 
			scale = True
			):

		fourier_features = FourierFeatures()
		balance_feature = BalanceFeature()
		main_features = MainFeatures()
		lag_feature = LagFeatures()
		datasetio = DatasetIO()
		patterns = Patterns()
		pca_mi = PCAMI()

		feature_engineering_5M = pd.DataFrame(index = dataset_5M.index)
		feature_engineering_15M = pd.DataFrame(index = dataset_15M.index)
		feature_engineering_1H = pd.DataFrame(index = dataset_1H.index)
		feature_engineering_4H = pd.DataFrame(index = dataset_4H.index)
		feature_engineering_1D = pd.DataFrame(index = dataset_1D.index)

		feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.DataJoiner(
																																				dataset_5M = dataset_5M, 
																																				dataset_15M = dataset_15M, 
																																				dataset_1H = dataset_1H,
																																				dataset_4H = dataset_4H,
																																				dataset_1D = dataset_1D,
																																				feature_engineering_5M = feature_engineering_5M, 
																																				feature_engineering_15M = feature_engineering_15M, 
																																				feature_engineering_1H = feature_engineering_1H,  
																																				feature_engineering_4H = feature_engineering_4H,  
																																				feature_engineering_1D = feature_engineering_1D,  
																																				symbol = symbol,
																																				scale = scale,
																																				name_feature = 'main'
																																				)

		#Main Features ***********:
		if self.main_features_flag == True:
			main_features_5M, main_features_15M, main_features_1H, main_features_4H, main_features_1D = main_features.Get(
																														dataset_5M = dataset_5M,
																														dataset_15M = dataset_15M,
																														dataset_1H = dataset_1H,
																														dataset_4H = dataset_4H,
																														dataset_1D = dataset_1D,
																														symbol = symbol,
																														mode = mode
																														)
			if 'time' in main_features_5M.columns: main_features_5M = main_features_5M.copy(deep = True).drop(columns = ['time'])
			if 'XAUUSD_i' in main_features_5M.columns: main_features_5M = main_features_5M.copy(deep = True).drop(columns = ['XAUUSD_i'])
			main_features_5M = main_features_5M.fillna(0)

			if 'time' in main_features_15M.columns: main_features_15M = main_features_15M.copy(deep = True).drop(columns = ['time'])
			if 'XAUUSD_i' in main_features_15M.columns: main_features_15M = main_features_15M.copy(deep = True).drop(columns = ['XAUUSD_i'])
			main_features_15M = main_features_15M.fillna(0)

			if 'time' in main_features_1H.columns: main_features_1H = main_features_1H.copy(deep = True).drop(columns = ['time'])
			if 'XAUUSD_i' in main_features_1H.columns: main_features_1H = main_features_1H.copy(deep = True).drop(columns = ['XAUUSD_i'])
			main_features_1H = main_features_1H.fillna(0)

			if 'time' in main_features_4H.columns: main_features_4H = main_features_4H.copy(deep = True).drop(columns = ['time'])
			if 'XAUUSD_i' in main_features_4H.columns: main_features_4H = main_features_4H.copy(deep = True).drop(columns = ['XAUUSD_i'])
			main_features_4H = main_features_4H.fillna(0)

			if 'time' in main_features_1D.columns: main_features_1D = main_features_1D.copy(deep = True).drop(columns = ['time'])
			if 'XAUUSD_i' in main_features_1D.columns: main_features_1D = main_features_1D.copy(deep = True).drop(columns = ['XAUUSD_i'])
			main_features_1D = main_features_1D.fillna(0)


			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.DataJoiner(
																																					dataset_5M = main_features_5M, 
																																					dataset_15M = main_features_15M, 
																																					dataset_1H = main_features_1H,
																																					dataset_4H = main_features_4H,
																																					dataset_1D = main_features_1D,
																																					feature_engineering_5M = feature_engineering_5M, 
																																					feature_engineering_15M = feature_engineering_15M, 
																																					feature_engineering_1H = feature_engineering_1H,  
																																					feature_engineering_4H = feature_engineering_4H,  
																																					feature_engineering_1D = feature_engineering_1D,  
																																					symbol = symbol,
																																					scale = scale,
																																					name_feature = 'main_features'
																																					)
		#///////////////////////////////////////////////

		#PCAMI Features ***************:
		if self.pca_features_flag == True and self.main_features_flag == True:

			if scale == False:
				pca_input_5M, pca_input_15M, pca_input_1H, pca_input_4H, pca_input_1D = self.DataJoiner(
																										dataset_5M = dataset_5M, 
																										dataset_15M = dataset_15M, 
																										dataset_1H = dataset_1H,
																										dataset_4H = dataset_4H,
																										dataset_1D = dataset_1D,
																										feature_engineering_5M = pd.DataFrame(index = dataset_5M.index), 
																										feature_engineering_15M = pd.DataFrame(index = dataset_15M.index), 
																										feature_engineering_1H = pd.DataFrame(index = dataset_1H.index),  
																										feature_engineering_4H = pd.DataFrame(index = dataset_4H.index),
																										feature_engineering_1D = pd.DataFrame(index = dataset_1D.index),
																										symbol = symbol,
																										scale = True,
																										name_feature = 'main'
																										)

				pca_input_5M, pca_input_15M, pca_input_1H, pca_input_4H, pca_input_1D = self.DataJoiner(
																										dataset_5M = main_features_5M, 
																										dataset_15M = main_features_15M, 
																										dataset_1H = main_features_1H,
																										dataset_4H = main_features_4H,
																										dataset_1D = main_features_1D,
																										feature_engineering_5M = pca_input_5M, 
																										feature_engineering_15M = pca_input_15M, 
																										feature_engineering_1H = pca_input_1H,  
																										feature_engineering_4H = pca_input_4H,
																										feature_engineering_1D = pca_input_1D,
																										symbol = symbol,
																										scale = True,
																										name_feature = 'main_features'
																										)
			else:
				pca_input_5M = feature_engineering_5M
				pca_input_15M = feature_engineering_15M
				pca_input_1H = feature_engineering_1H
				pca_input_4H = feature_engineering_4H
				pca_input_1D = feature_engineering_1D

			pca_feature_5M, pca_feature_15M, pca_feature_1H, pca_feature_4H, pca_feature_1D = pca_mi.Get(
																										dataset_5M = pca_input_5M, 
																										dataset_15M = pca_input_15M, 
																										dataset_1H = pca_input_1H, 
																										dataset_4H = pca_input_4H, 
																										dataset_1D = pca_input_1D, 
																										symbol = symbol, 
																										mode = mode
																										)
				
			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.DataJoiner(
																																					dataset_5M = pca_feature_5M, 
																																					dataset_15M = pca_feature_15M, 
																																					dataset_1H = pca_feature_1H,
																																					dataset_4H = pca_feature_4H,
																																					dataset_1D = pca_feature_1D,
																																					feature_engineering_5M = feature_engineering_5M, 
																																					feature_engineering_15M = feature_engineering_15M, 
																																					feature_engineering_1H = feature_engineering_1H,  
																																					feature_engineering_4H = feature_engineering_4H,  
																																					feature_engineering_1D = feature_engineering_1D,  
																																					symbol = symbol,
																																					scale = scale,
																																					name_feature = 'pca'
																																					)
		#///////////////////////////////////////////////


		#Lag Features ****************:
		if self.lag_features_flag == True:
			LagedData_5M, LagedData_15M, LagedData_1H, LagedData_4H, LagedData_1D = lag_feature.Get(
																									dataset_5M = dataset_5M,
																									dataset_15M = dataset_15M,
																									dataset_1H = dataset_1H,
																									dataset_4H = dataset_4H,
																									dataset_1D = dataset_1D,
																									symbol = symbol,
																									number_lags = 1,
																									mode = mode
																									)

			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.DataJoiner(
																																					dataset_5M = LagedData_5M, 
																																					dataset_15M = LagedData_15M, 
																																					dataset_1H = LagedData_1H,
																																					dataset_4H = LagedData_4H,
																																					dataset_1D = LagedData_1D,
																																					feature_engineering_5M = feature_engineering_5M, 
																																					feature_engineering_15M = feature_engineering_15M, 
																																					feature_engineering_1H = feature_engineering_1H,  
																																					feature_engineering_4H = feature_engineering_4H,  
																																					feature_engineering_1D = feature_engineering_1D,  
																																					symbol = symbol,
																																					scale = scale,
																																					name_feature = 'lags'
																																					)
		#///////////////////////////////////////////////

		#Fourier Features ****************:
		if self.fourier_features_flag['main'] == True:

			fourier_features.flag_fourier_5M = self.fourier_features_flag['5M']
			fourier_features.flag_fourier_15M = self.fourier_features_flag['15M']
			fourier_features.flag_fourier_1H = self.fourier_features_flag['1H']
			fourier_features.flag_fourier_4H = self.fourier_features_flag['4H']
			fourier_features.flag_fourier_1D = self.fourier_features_flag['1D']

			fourier_feature_5M, fourier_feature_15M, fourier_feature_1H, fourier_feature_4H, fourier_feature_1D = fourier_features.Get(
																																		dataset_5M = dataset_5M, 
																																		dataset_15M = dataset_15M, 
																																		dataset_1H = dataset_1H, 
																																		dataset_4H = dataset_4H, 
																																		dataset_1D = dataset_1D, 
																																		symbol = symbol, 
																																		mode = mode, 
																																		number_frequencies = 2
																																		)

			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.DataJoiner(
																																					dataset_5M = fourier_feature_5M, 
																																					dataset_15M = fourier_feature_15M, 
																																					dataset_1H = fourier_feature_1H,
																																					dataset_4H = fourier_feature_4H,
																																					dataset_1D = fourier_feature_1D,
																																					feature_engineering_5M = feature_engineering_5M, 
																																					feature_engineering_15M = feature_engineering_15M, 
																																					feature_engineering_1H = feature_engineering_1H,  
																																					feature_engineering_4H = feature_engineering_4H,  
																																					feature_engineering_1D = feature_engineering_1D,  
																																					symbol = symbol,
																																					scale = scale,
																																					name_feature = 'fourier'
																																					)
		#///////////////////////////////////////////////


		#Pattern Features *****************:
		if self.pattern_features_flag == True:
			pattern_feature_5M, pattern_feature_15M, pattern_feature_1H, pattern_feature_4H, pattern_feature_1D = patterns.Get(
																																dataset_5M = dataset_5M, 
																																dataset_15M = dataset_15M, 
																																dataset_1H = dataset_1H, 
																																dataset_4H = dataset_4H, 
																																dataset_1D = dataset_1D, 
																																symbol = symbol,
																																mode = mode
																																)

			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.DataJoiner(
																																					dataset_5M = pattern_feature_5M, 
																																					dataset_15M = pattern_feature_15M, 
																																					dataset_1H = pattern_feature_1H,
																																					dataset_4H = pattern_feature_4H,
																																					dataset_1D = pattern_feature_1D,
																																					feature_engineering_5M = feature_engineering_5M, 
																																					feature_engineering_15M = feature_engineering_15M, 
																																					feature_engineering_1H = feature_engineering_1H,  
																																					feature_engineering_4H = feature_engineering_4H,  
																																					feature_engineering_1D = feature_engineering_1D,  
																																					symbol = symbol,
																																					scale = scale,
																																					name_feature = 'pattern'
																																					)
		#///////////////////////////////////////////////

		#Pattern Features *****************:
		if self.balance_feature_flag == True:
			balance_feature_5M, balance_feature_15M, balance_feature_1H, balance_feature_4H, balance_feature_1D = balance_feature.Get(
																																	dataset_5M = dataset_5M, 
																																	dataset_15M = dataset_15M, 
																																	dataset_1H = dataset_1H, 
																																	dataset_4H = dataset_4H, 
																																	dataset_1D = dataset_1D, 																																
																																	)

			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.DataJoiner(
																																					dataset_5M = balance_feature_5M, 
																																					dataset_15M = balance_feature_15M, 
																																					dataset_1H = balance_feature_1H,
																																					dataset_4H = balance_feature_4H,
																																					dataset_1D = balance_feature_1D,
																																					feature_engineering_5M = feature_engineering_5M, 
																																					feature_engineering_15M = feature_engineering_15M, 
																																					feature_engineering_1H = feature_engineering_1H,  
																																					feature_engineering_4H = feature_engineering_4H,  
																																					feature_engineering_1D = feature_engineering_1D,  
																																					symbol = symbol,
																																					scale = scale,
																																					name_feature = 'pattern'
																																					)
		#///////////////////////////////////////////////

		return feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D

	#@stTime
	def __call__(
				self, 
				dataset_5M, 
				dataset_15M, 
				dataset_1H, 
				dataset_4H, 
				dataset_1D, 
				symbol = 'XAUUSD_i', 
				mode = None, 
				scale = True
				):

		datasetio = DatasetIO()

		if mode == None:

			if scale == True:
				feature_engineering_5M = datasetio.Read(type_feature = 'feature_engineering_scale', symbol = symbol, name = '5M')
				feature_engineering_15M = datasetio.Read(type_feature = 'feature_engineering_scale', symbol = symbol, name = '15M')
				feature_engineering_1H = datasetio.Read(type_feature = 'feature_engineering_scale', symbol = symbol, name = '1H')
				feature_engineering_4H = datasetio.Read(type_feature = 'feature_engineering_scale', symbol = symbol, name = '4H')
				feature_engineering_1D = datasetio.Read(type_feature = 'feature_engineering_scale', symbol = symbol, name = '1D')
			else:
				feature_engineering_5M = datasetio.Read(type_feature = 'feature_engineering', symbol = symbol, name = '5M')
				feature_engineering_15M = datasetio.Read(type_feature = 'feature_engineering', symbol = symbol, name = '15M')
				feature_engineering_1H = datasetio.Read(type_feature = 'feature_engineering', symbol = symbol, name = '1H')
				feature_engineering_4H = datasetio.Read(type_feature = 'feature_engineering', symbol = symbol, name = '4H')
				feature_engineering_1D = datasetio.Read(type_feature = 'feature_engineering', symbol = symbol, name = '1D')

			if (
				feature_engineering_5M.empty == True and
				feature_engineering_15M.empty == True and
				feature_engineering_1H.empty == True and
				feature_engineering_4H.empty == True and
				feature_engineering_1D.empty == True
				):

				feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.Run(
																																					dataset_5M = dataset_5M, 
																																					dataset_15M = dataset_15M, 
																																					dataset_1H = dataset_1H, 
																																					dataset_4H = dataset_4H, 
																																					dataset_1D = dataset_1D, 
																																					symbol = symbol, 
																																					mode = mode, 
																																					scale = scale
																																					)

				if scale == True:
					datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_5M, symbol = symbol, name = '5M')
					datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_15M, symbol = symbol, name = '15M')
					datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_1H, symbol = symbol, name = '1H')
					datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_4H, symbol = symbol, name = '4H')
					datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_1D, symbol = symbol, name = '1D')
				else:
					datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_5M, symbol = symbol, name = '5M')
					datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_15M, symbol = symbol, name = '15M')
					datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_1H, symbol = symbol, name = '1H')
					datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_4H, symbol = symbol, name = '4H')
					datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_1D, symbol = symbol, name = '1D')

			return feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H ,feature_engineering_1D

		elif mode == 'Run':

			if scale == True:
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '5M')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '15M')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '1H')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '4H')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '1D')
			else:
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering', name = '5M')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering', name = '15M')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering', name = '1H')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering', name = '4H')
				datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering', name = '1D')

			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.Run(
																																				dataset_5M = dataset_5M, 
																																				dataset_15M = dataset_15M, 
																																				dataset_1H = dataset_1H, 
																																				dataset_4H = dataset_4H,
																																				dataset_1D = dataset_1D,
																																				symbol = symbol, 
																																				mode = mode, 
																																				scale = scale
																																				)

			if scale == True:
				datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_5M, symbol = symbol, name = '5M')
				datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_15M, symbol = symbol, name = '15M')
				datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_1H, symbol = symbol, name = '1H')
				datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_4H, symbol = symbol, name = '4H')
				datasetio.Write(type_feature = 'feature_engineering_scale', dataset = feature_engineering_1D, symbol = symbol, name = '1D')
			else:
				datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_5M, symbol = symbol, name = '5M')
				datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_15M, symbol = symbol, name = '15M')
				datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_1H, symbol = symbol, name = '1H')
				datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_4H, symbol = symbol, name = '4H')
				datasetio.Write(type_feature = 'feature_engineering', dataset = feature_engineering_1D, symbol = symbol, name = '1D')

			return feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D

		elif mode == 'online':

			feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = self.Run(
																																				dataset_5M = dataset_5M, 
																																				dataset_15M = dataset_15M, 
																																				dataset_1H = dataset_1H, 
																																				dataset_4H = dataset_4H, 
																																				dataset_1D = dataset_1D, 
																																				symbol = symbol, 
																																				mode = mode, 
																																				scale = scale
																																				)
			return feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D