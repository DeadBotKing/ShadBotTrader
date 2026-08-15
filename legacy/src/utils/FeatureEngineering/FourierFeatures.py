from src.utils.Tools.timer import stTime
from .Frequencies import Frequencies
from .DatasetIO import DatasetIO
from progress.bar import Bar
from .Config import Config
import pandas as pd
import numpy as np

#Functions:

#FreqReader()
#FeaturePerparer()
#Run()
#Get()

#/////////////////////

class FourierFeatures():

	def __init__(self):

		self.flag_fourier_5M = True
		self.flag_fourier_15M = True
		self.flag_fourier_1H = True
		self.flag_fourier_4H = True
		self.flag_fourier_1D = True


	def FreqReader(self, dataset, symbol, mode, number_frequencies, name):

		frequences = Frequencies()
		frequences = frequences.Get(dataset = dataset, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = name)
		
		return frequences

	
	def FeaturesPerparer(self, dataset, column, frequencies, symbol):

		fourier_feature = pd.DataFrame()
		features = {}

		for freq in frequencies['freq_' + column].dropna():

			# time = np.arange(len(dataset.index), dtype=np.float32)

			degree = (dataset[column] - dataset[column].min()) / (dataset[column].max() - dataset[column].min())
			k = 2 * np.pi * (freq) * degree
			
			features.update({
					        f"sin_{int(freq)}_{column}": np.sin(k),
					        f"cos_{int(freq)}_{column}": np.cos(k),
		    				})
		features = pd.DataFrame(features, index = dataset.index)

		return features

	
	def Run(self, dataset, symbol, mode, number_frequencies, name):

		dataset = dataset.copy(deep = True).drop(columns = [symbol, 'volume'])

		frequencies = self.FreqReader(dataset = dataset, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = name)

		if (
			frequencies.empty == True and
			mode == None
			):

			frequencies = self.FreqReader(dataset = dataset, symbol = symbol, mode = 'Run', name = name)

		bar_config = Config()
		if bar_config.cfg['show_bar']:
			bar = Bar(symbol + ' ' + 'Fourier Features Finding: ', max = int(len(dataset.columns)))

		fourier_feature = pd.DataFrame(np.zeros(len(dataset.index)))

		for column in dataset.columns:

			if 'time' in column: continue

			feature_prepared = self.FeaturesPerparer(
														dataset = dataset,
														column = column,
														frequencies = frequencies,
														symbol = symbol
													)

			fourier_feature = fourier_feature.join(feature_prepared, how = 'right')

			if bar_config.cfg['show_bar']:
				bar.next()
		
		fourier_feature = fourier_feature.drop(columns = [0])
		
		return fourier_feature

	# @stTime
	def Get(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol = 'XAUUSD_i', mode = None, number_frequencies = 3):

		datasetio = DatasetIO()

		if mode == 'Run':

			if self.flag_fourier_5M == True:
				datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '5M')
				pattern_fourier_5M = self.Run(dataset = dataset_5M, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '5M')
				datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_5M, symbol = symbol, name = '5M')

				minmax_scaler_5M = pd.DataFrame(index = [0])
				minmax_scaler_5M['min_' + pattern_fourier_5M.columns] = pattern_fourier_5M.min()
				minmax_scaler_5M['max_' + pattern_fourier_5M.columns] = pattern_fourier_5M.max()
				datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')

			else:
				pattern_fourier_5M = pd.DataFrame()


			if self.flag_fourier_15M == True:
				datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '15M')
				pattern_fourier_15M = self.Run(dataset = dataset_15M, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '15M')
				datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_15M, symbol = symbol, name = '15M')

				minmax_scaler_15M = pd.DataFrame(index = [0])
				minmax_scaler_15M['min_' + pattern_fourier_15M.columns] = pattern_fourier_15M.min()
				minmax_scaler_15M['max_' + pattern_fourier_15M.columns] = pattern_fourier_15M.max()
				datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')

			else:
				pattern_fourier_15M = pd.DataFrame()


			if self.flag_fourier_1H == True:
				datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '1H')
				pattern_fourier_1H = self.Run(dataset = dataset_1H, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '1H')
				datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_1H, symbol = symbol, name = '1H')

				minmax_scaler_1H = pd.DataFrame(index = [0])
				minmax_scaler_1H['min_' + pattern_fourier_1H.columns] = pattern_fourier_1H.min()
				minmax_scaler_1H['max_' + pattern_fourier_1H.columns] = pattern_fourier_1H.max()
				datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')

			else:
				pattern_fourier_1H = pd.DataFrame()


			if self.flag_fourier_4H == True:
				datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '4H')
				pattern_fourier_4H = self.Run(dataset = dataset_4H, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '4H')
				datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_4H, symbol = symbol, name = '4H')

				minmax_scaler_4H = pd.DataFrame(index = [0])
				minmax_scaler_4H['min_' + pattern_fourier_4H.columns] = pattern_fourier_4H.min()
				minmax_scaler_4H['max_' + pattern_fourier_4H.columns] = pattern_fourier_4H.max()
				datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')

			else:
				pattern_fourier_4H = pd.DataFrame()


			if self.flag_fourier_1D == True:
				datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '1D')
				pattern_fourier_1D = self.Run(dataset = dataset_1D, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '1D')
				datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_1D, symbol = symbol, name = '1D')

				minmax_scaler_1D = pd.DataFrame(index = [0])
				minmax_scaler_1D['min_' + pattern_fourier_1D.columns] = pattern_fourier_1D.min()
				minmax_scaler_1D['max_' + pattern_fourier_1D.columns] = pattern_fourier_1D.max()
				datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')

			else:
				pattern_fourier_1D = pd.DataFrame()


			return pattern_fourier_5M, pattern_fourier_15M, pattern_fourier_1H, pattern_fourier_4H, pattern_fourier_1D

		elif mode == None:

			fourier_feature_5M = datasetio.Read(type_feature = 'fourier', symbol = symbol, name = '5M')
			fourier_feature_15M = datasetio.Read(type_feature = 'fourier', symbol = symbol, name = '15M')
			fourier_feature_1H = datasetio.Read(type_feature = 'fourier', symbol = symbol, name = '1H')
			fourier_feature_4H = datasetio.Read(type_feature = 'fourier', symbol = symbol, name = '4H')
			fourier_feature_1D = datasetio.Read(type_feature = 'fourier', symbol = symbol, name = '1D')
			
			if (
				fourier_feature_5M.empty == False and
				fourier_feature_15M.empty == False and
				fourier_feature_1H.empty == False and
				fourier_feature_4H.empty == False and
				fourier_feature_1D.empty == False
				):
				return fourier_feature_5M, fourier_feature_15M, fourier_feature_1H, fourier_feature_4H, fourier_feature_1D

			else:
				if self.flag_fourier_5M == True:
					datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '5M')
					pattern_fourier_5M = self.Run(dataset = dataset_5M, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '5M')
					datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_5M, symbol = symbol, name = '5M')

					minmax_scaler_5M = pd.DataFrame(index = [0])
					minmax_scaler_5M['min_' + pattern_fourier_5M.columns] = pattern_fourier_5M.min()
					minmax_scaler_5M['max_' + pattern_fourier_5M.columns] = pattern_fourier_5M.max()
					datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')

				else:
					pattern_fourier_5M = pd.DataFrame()


				if self.flag_fourier_15M == True:
					datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '15M')
					pattern_fourier_15M = self.Run(dataset = dataset_15M, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '15M')
					datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_15M, symbol = symbol, name = '15M')

					minmax_scaler_15M = pd.DataFrame(index = [0])
					minmax_scaler_15M['min_' + pattern_fourier_15M.columns] = pattern_fourier_15M.min()
					minmax_scaler_15M['max_' + pattern_fourier_15M.columns] = pattern_fourier_15M.max()
					datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')

				else:
					pattern_fourier_15M = pd.DataFrame()


				if self.flag_fourier_1H == True:
					datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '1H')
					pattern_fourier_1H = self.Run(dataset = dataset_1H, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '1H')
					datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_1H, symbol = symbol, name = '1H')

					minmax_scaler_1H = pd.DataFrame(index = [0])
					minmax_scaler_1H['min_' + pattern_fourier_1H.columns] = pattern_fourier_1H.min()
					minmax_scaler_1H['max_' + pattern_fourier_1H.columns] = pattern_fourier_1H.max()
					datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')

				else:
					pattern_fourier_1H = pd.DataFrame()


				if self.flag_fourier_4H == True:
					datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '4H')
					pattern_fourier_4H = self.Run(dataset = dataset_4H, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '4H')
					datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_4H, symbol = symbol, name = '4H')

					minmax_scaler_4H = pd.DataFrame(index = [0])
					minmax_scaler_4H['min_' + pattern_fourier_4H.columns] = pattern_fourier_4H.min()
					minmax_scaler_4H['max_' + pattern_fourier_4H.columns] = pattern_fourier_4H.max()
					datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')

				else:
					pattern_fourier_4H = pd.DataFrame()


				if self.flag_fourier_1D == True:
					datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '1D')
					pattern_fourier_1D = self.Run(dataset = dataset_1D, symbol = symbol, mode = mode, number_frequencies = number_frequencies, name = '1D')
					datasetio.Write(type_feature = 'fourier', dataset = pattern_fourier_1D, symbol = symbol, name = '1D')

					minmax_scaler_1D = pd.DataFrame(index = [0])
					minmax_scaler_1D['min_' + pattern_fourier_1D.columns] = pattern_fourier_1D.min()
					minmax_scaler_1D['max_' + pattern_fourier_1D.columns] = pattern_fourier_1D.max()
					datasetio.Write(type_feature = 'fourier_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')

				else:
					pattern_fourier_1D = pd.DataFrame()

				return pattern_fourier_5M, pattern_fourier_15M, pattern_fourier_1H, pattern_fourier_4H, pattern_fourier_1D

		elif mode == 'online':

			if self.flag_fourier_5M == True:
				pattern_fourier_5M = self.Run(dataset = dataset_5M, symbol = symbol, mode = None, number_frequencies = number_frequencies, name = '5M')
			else:
				pattern_fourier_5M = pd.DataFrame()

			if self.flag_fourier_15M == True:
				pattern_fourier_15M = self.Run(dataset = dataset_15M, symbol = symbol, mode = None, number_frequencies = number_frequencies, name = '15M')
			else:
				pattern_fourier_15M = pd.DataFrame()
			
			if self.flag_fourier_1H == True:				
				pattern_fourier_1H = self.Run(dataset = dataset_1H, symbol = symbol, mode = None, number_frequencies = number_frequencies, name = '1H')
			else:
				pattern_fourier_1H = pd.DataFrame()

			if self.flag_fourier_4H == True:
				pattern_fourier_4H = self.Run(dataset = dataset_4H, symbol = symbol, mode = None, number_frequencies = number_frequencies, name = '4H')
			else:
				pattern_fourier_4H = pd.DataFrame()

			if self.flag_fourier_1D == True:
				pattern_fourier_1D = self.Run(dataset = dataset_1D, symbol = symbol, mode = None, number_frequencies = number_frequencies, name = '1D')
			else:
				pattern_fourier_1D = pd.DataFrame()

			return pattern_fourier_5M, pattern_fourier_15M, pattern_fourier_1H, pattern_fourier_4H, pattern_fourier_1D