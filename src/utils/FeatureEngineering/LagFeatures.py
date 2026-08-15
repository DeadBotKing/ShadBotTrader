from src.utils.FeatureEngineering.Frequencies import Frequencies
from statsmodels.tsa.stattools import acf
from src.utils.Tools.timer import stTime
from .DatasetIO import DatasetIO
import pandas as pd

class LagFeatures():

	def __init__(self):

		self.lags = [1, 2, 3, 4, 5, 6, 7, 8, 9]

	def LagFinder(self, dataset, applyto, number_lags, symbol, name, mode = 'Run'):

		datasetio = DatasetIO()

		if mode == 'Run':
			correlations, _ = acf(
								x = dataset[applyto].dropna(), 
								adjusted = False, 
								nlags = 500, 
								qstat = False, 
								fft = True, 
								alpha = 0.05
								)

			# print('corr = ', correlations)

			self.lags = []
			lag_counter = 0

			for corr in correlations:

				if len(self.lags) > number_lags: break

				if corr > 0.97:

					self.lags.append(lag_counter)
					if lag_counter == 0: self.lags.remove(0)

				lag_counter += 1

			datasetio.Write(type_feature = 'lags_number', dataset = pd.DataFrame(self.lags, columns = ['numbers']), symbol = symbol, name = name)

		elif mode == None:
			self.lags = datasetio.Read(type_feature = 'lags_number', symbol = symbol, name = name)

			if self.lags.empty == False: 
				self.lags = self.lags['numbers'].values.tolist()

			else:
				correlations, _ = acf(
									x = dataset[applyto].dropna(), 
									adjusted = False, 
									nlags = 500, 
									qstat = False, 
									fft = True, 
									alpha = 0.05
									)

				# print('corr = ', correlations)

				self.lags = []
				lag_counter = 0

				for corr in correlations:

					if len(self.lags) > number_lags: break

					if corr > 0.97:

						self.lags.append(lag_counter)
						if lag_counter == 0: self.lags.remove(0)

					lag_counter += 1

				datasetio.Write(type_feature = 'lags_number', dataset = pd.DataFrame(self.lags, columns = ['numbers']), symbol = symbol, name = name)

		elif mode == 'online':
			self.lags = datasetio.Read(type_feature = 'lags_number', symbol = symbol, name = name)['numbers'].values.tolist()

	def LagCreation(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol, number_lags, mode):

		#5M *************:
		dataset_lag_5M = dataset_5M.copy(deep = True).drop(columns = [symbol])
		dataset_lag_5M.index = dataset_lag_5M['time']
		dataset_lag_5M = dataset_lag_5M.drop(columns = ['time'])

		outlier_cutoff = 0.01
		LagedData_5M = pd.DataFrame(index = dataset_lag_5M.index)

		frequences_5M = Frequencies()
		frequences_5M = frequences_5M.Get(dataset = dataset_5M.copy(deep = True).drop(columns = [symbol]), symbol = symbol, mode = None, number_frequencies = 2, name = '5M')

		for freq_counter in range(0, 1):

			freq_5M = frequences_5M['freq_close'][freq_counter]
			dataset_frequented_5M = pd.DataFrame()
			dataset_frequented_5M = dataset_lag_5M.copy(deep = True).resample(str(freq_5M) + 'T').last().dropna(subset=['close'])

			if not self.LagFinder(dataset = dataset_frequented_5M.reset_index().copy(deep = True), applyto = 'close', number_lags = number_lags, symbol = symbol, mode = mode, name = '5M'):
				for clm in dataset_frequented_5M.columns:
					LagedData_5M[f'{clm}_return_{freq_5M}_{1}'] = dataset_frequented_5M.pct_change(1)[clm]
			else:
				LagedData_5M[f'{clm}_return_{freq_5M}_{self.lags[0]}'] = dataset_frequented_5M.pct_change(self.lags[0])[clm]

		LagedData_5M = self.TargetCreation(dataset = LagedData_5M, freq = freq_5M)
		LagedData_5M = LagedData_5M.reset_index().drop(columns = ['time'])
		LagedData_5M = LagedData_5M.fillna(method = 'bfill', axis = 0).fillna(0)
		#////////////////////////////////////////////////////

		#15M *************:
		dataset_lag_15M = dataset_15M.copy(deep = True).drop(columns = [symbol])
		dataset_lag_15M.index = dataset_lag_15M['time']
		dataset_lag_15M = dataset_lag_15M.drop(columns = ['time'])

		outlier_cutoff = 0.01
		LagedData_15M = pd.DataFrame(index = dataset_lag_15M.index)

		frequences_15M = Frequencies()
		frequences_15M = frequences_15M.Get(dataset = dataset_15M.copy(deep = True).drop(columns = [symbol]), symbol = symbol, mode = None, number_frequencies = 2, name = '15M')

		for freq_counter in range(0, 1):

			freq_15M = frequences_15M['freq_close'][freq_counter]
			dataset_frequented_15M = pd.DataFrame()
			dataset_frequented_15M = dataset_lag_15M.copy(deep = True).resample(str(freq_15M) + 'T').last().dropna(subset=['close'])

			if not self.LagFinder(dataset = dataset_frequented_15M.reset_index().copy(deep = True), applyto = 'close', number_lags = number_lags, symbol = symbol, mode = mode, name = '15M'):
				for clm in dataset_frequented_15M.columns:
					LagedData_15M[f'{clm}_return_{freq_15M}_{1}'] = dataset_frequented_15M.pct_change(1)[clm]
			else:
				LagedData_15M[f'{clm}_return_{freq_15M}_{self.lags[0]}'] = dataset_frequented_15M.pct_change(self.lags[0])[clm]

		LagedData_15M = self.TargetCreation(dataset = LagedData_15M, freq = freq_15M)
		LagedData_15M = LagedData_15M.reset_index().drop(columns = ['time'])
		LagedData_15M = LagedData_15M.fillna(method = 'bfill', axis = 0).fillna(0)
		#////////////////////////////////////////////////////


		#1H *************:
		dataset_lag_1H = dataset_1H.copy(deep = True).drop(columns = [symbol])
		dataset_lag_1H.index = dataset_lag_1H['time']
		dataset_lag_1H = dataset_lag_1H.drop(columns = ['time'])

		outlier_cutoff = 0.01
		LagedData_1H = pd.DataFrame(index = dataset_lag_1H.index)

		frequences_1H = Frequencies()
		frequences_1H = frequences_1H.Get(dataset = dataset_1H.copy(deep = True).drop(columns = [symbol]), symbol = symbol, mode = None, number_frequencies = 2, name = '1H')

		for freq_counter in range(0, 1):

			freq_1H = frequences_1H['freq_close'][freq_counter]
			dataset_frequented_1H = pd.DataFrame()
			dataset_frequented_1H = dataset_lag_1H.copy(deep = True).resample(str(freq_1H) + 'H').last().dropna(subset=['close'])

			if not self.LagFinder(dataset = dataset_frequented_1H.reset_index().copy(deep = True), applyto = 'close', number_lags = number_lags, symbol = symbol, mode = mode, name = '1H'):
				for clm in dataset_frequented_1H.columns:
					LagedData_1H[f'{clm}_return_{freq_1H}_{1}'] = dataset_frequented_1H.pct_change(1)[clm]

			else:
				for clm in dataset_frequented_1H.columns:
					LagedData_1H[f'{clm}_return_{freq_1H}_{self.lags[0]}'] = dataset_frequented_1H.pct_change(self.lags[0])[clm]

		LagedData_1H = self.TargetCreation(dataset = LagedData_1H, freq = freq_1H)
		LagedData_1H = LagedData_1H.reset_index().drop(columns = ['time'])
		LagedData_1H = LagedData_1H.fillna(method = 'bfill', axis = 0).fillna(0)
		#////////////////////////////////////////////////////

		#4H *************:
		dataset_lag_4H = dataset_4H.copy(deep = True).drop(columns = [symbol])
		dataset_lag_4H.index = dataset_lag_4H['time']
		dataset_lag_4H = dataset_lag_4H.drop(columns = ['time'])

		outlier_cutoff = 0.01
		LagedData_4H = pd.DataFrame(index = dataset_lag_4H.index)

		frequences_4H = Frequencies()
		frequences_4H = frequences_4H.Get(dataset = dataset_4H.copy(deep = True).drop(columns = [symbol]), symbol = symbol, mode = None, number_frequencies = 2, name = '4H')

		for freq_counter in range(0, 1):

			freq_4H = frequences_4H['freq_close'][freq_counter]
			dataset_frequented_4H = pd.DataFrame()
			dataset_frequented_4H = dataset_lag_4H.copy(deep = True).resample(str(freq_4H) + 'H').last().dropna(subset=['close'])

			if not self.LagFinder(dataset = dataset_frequented_4H.reset_index().copy(deep = True), applyto = 'close', number_lags = number_lags, symbol = symbol, mode = mode, name = '4H'):
				for clm in dataset_frequented_4H.columns:
					LagedData_4H[f'{clm}_return_{freq_4H}_{1}'] = dataset_frequented_4H.pct_change(1)[clm]

			else:
				for clm in dataset_frequented_4H.columns:
					LagedData_4H[f'{clm}_return_{freq_4H}_{self.lags[0]}'] = dataset_frequented_4H.pct_change(self.lags[0])[clm]

		LagedData_4H = self.TargetCreation(dataset = LagedData_4H, freq = freq_4H)
		LagedData_4H = LagedData_4H.reset_index().drop(columns = ['time'])
		LagedData_4H = LagedData_4H.fillna(method = 'bfill', axis = 0).fillna(0)
		#////////////////////////////////////////////////////

		#1D *************:
		dataset_lag_1D = dataset_1D.copy(deep = True).drop(columns = [symbol])
		dataset_lag_1D.index = dataset_lag_1D['time']
		dataset_lag_1D = dataset_lag_1D.drop(columns = ['time'])

		outlier_cutoff = 0.01
		LagedData_1D = pd.DataFrame(index = dataset_lag_1D.index)

		frequences_1D = Frequencies()
		frequences_1D = frequences_1D.Get(dataset = dataset_1D.copy(deep = True).drop(columns = [symbol]), symbol = symbol, mode = None, number_frequencies = 2, name = '1D')

		for freq_counter in range(0, 1):

			freq_1D = frequences_1D['freq_close'][freq_counter]
			dataset_frequented_1D = pd.DataFrame()
			dataset_frequented_1D = dataset_lag_1D.copy(deep = True).resample(str(freq_1D) + 'D').last().dropna(subset=['close'])

			if not self.LagFinder(dataset = dataset_frequented_1D.reset_index().copy(deep = True), applyto = 'close', number_lags = number_lags, symbol = symbol, mode = mode, name = '1D'):
				for clm in dataset_frequented_1D.columns:
					LagedData_1D[f'{clm}_return_{freq_1D}_{1}'] = dataset_frequented_1D.pct_change(1)[clm]

			else:
				for clm in dataset_frequented_1D.columns:
					LagedData_1D[f'{clm}_return_{freq_1D}_{self.lags[0]}'] = dataset_frequented_1D.pct_change(self.lags[0])[clm]

		LagedData_1D = self.TargetCreation(dataset = LagedData_1D, freq = freq_1D)
		LagedData_1D = LagedData_1D.reset_index().drop(columns = ['time'])
		LagedData_1D = LagedData_1D.fillna(method = 'bfill', axis = 0).fillna(0)
		#////////////////////////////////////////////////////

		return LagedData_5M, LagedData_15M, LagedData_1H, LagedData_4H, LagedData_1D


	def MemontumCreation(self, dataset, freq):

		for lag in self.lags:
			dataset[f'momentum_{freq}_{lag}'] = dataset[f'return_{freq}_{lag}'].sub(dataset[f'return_{freq}_{self.lags[0]}'])

		return dataset

	def TargetCreation(self, dataset, freq):

		for clm in dataset.columns:
			column_name = clm.split('_')[0]

			if not self.lags:
				dataset[f'{column_name}_target_{freq}_-{1}'] = dataset[clm].shift(1)
			else:
				dataset[f'{column_name}_target_{freq}_-{self.lags[0]}'] = dataset[clm].shift(self.lags[0])

		for clm in dataset.columns:
			column_name = clm.split('_')[0]

			if not self.lags:
				dataset[f'{column_name}_target_{freq}_{1}'] = dataset[clm].shift(-1)
			else:
				dataset[f'{column_name}_target_{freq}_{self.lags[0]}'] = dataset[clm].shift(-self.lags[0])
		
		return dataset

	def Run(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol = 'XAUUSD_i', number_lags = 1, mode = None):

		lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D = self.LagCreation(
																											dataset_5M = dataset_5M,
																											dataset_15M = dataset_15M,
																											dataset_1H = dataset_1H,
																											dataset_4H = dataset_4H,
																											dataset_1D = dataset_1D,
																											symbol = 'XAUUSD_i',
																											number_lags = number_lags,
																											mode = mode
																											)

		return lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D

	# @stTime
	def Get(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol = 'XAUUSD_i', number_lags = 1, mode = None):

		datasetio = DatasetIO()

		if mode == None:
			lag_feature_5M = datasetio.Read(type_feature = 'lags', symbol = symbol, name = '5M')
			lag_feature_15M = datasetio.Read(type_feature = 'lags', symbol = symbol, name = '15M') 
			lag_feature_1H = datasetio.Read(type_feature = 'lags', symbol = symbol, name = '1H')
			lag_feature_4H = datasetio.Read(type_feature = 'lags', symbol = symbol, name = '4H')
			lag_feature_1D = datasetio.Read(type_feature = 'lags', symbol = symbol, name = '1D')

			if (
				lag_feature_5M.empty == False and
				lag_feature_15M.empty == False and
				lag_feature_1H.empty == False and
				lag_feature_4H.empty == False and
				lag_feature_1D.empty == False
				):
				return lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D

			else:
				lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D = self.Run(
																											dataset_5M = dataset_5M,
																											dataset_15M = dataset_15M,
																											dataset_1H = dataset_1H,
																											dataset_4H = dataset_4H,
																											dataset_1D = dataset_1D,
																											symbol = symbol, 
																											number_lags = number_lags,
																											mode = mode
																											)

				datasetio.Write(type_feature = 'lags', dataset = lag_feature_5M, symbol = symbol, name = '5M')
				datasetio.Write(type_feature = 'lags', dataset = lag_feature_15M, symbol = symbol, name = '15M')
				datasetio.Write(type_feature = 'lags', dataset = lag_feature_1H, symbol = symbol, name = '1H')
				datasetio.Write(type_feature = 'lags', dataset = lag_feature_4H, symbol = symbol, name = '4H')
				datasetio.Write(type_feature = 'lags', dataset = lag_feature_1D, symbol = symbol, name = '1D')

				minmax_scaler_5M = pd.DataFrame(index = [0])
				minmax_scaler_5M['min_' + lag_feature_5M.columns] = lag_feature_5M.min()
				minmax_scaler_5M['max_' + lag_feature_5M.columns] = lag_feature_5M.max()

				minmax_scaler_15M = pd.DataFrame(index = [0])
				minmax_scaler_15M['min_' + lag_feature_15M.columns] = lag_feature_15M.min()
				minmax_scaler_15M['max_' + lag_feature_15M.columns] = lag_feature_15M.max()

				minmax_scaler_1H = pd.DataFrame(index = [0])
				minmax_scaler_1H['min_' + lag_feature_1H.columns] = lag_feature_1H.min()
				minmax_scaler_1H['max_' + lag_feature_1H.columns] = lag_feature_1H.max()

				minmax_scaler_4H = pd.DataFrame(index = [0])
				minmax_scaler_4H['min_' + lag_feature_4H.columns] = lag_feature_4H.min()
				minmax_scaler_4H['max_' + lag_feature_4H.columns] = lag_feature_4H.max()

				minmax_scaler_1D = pd.DataFrame(index = [0])
				minmax_scaler_1D['min_' + lag_feature_1D.columns] = lag_feature_1D.min()
				minmax_scaler_1D['max_' + lag_feature_1D.columns] = lag_feature_1D.max()

				datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
				datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
				datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
				datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
				datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')

				return lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D

		elif mode == 'Run':

			datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '5M')
			datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '15M') 
			datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '1H')
			datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '4H')
			datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '1D')

			datasetio.Delete(type_feature = 'lags_minmaxscaler', symbol = symbol, name = '5M')
			datasetio.Delete(type_feature = 'lags_minmaxscaler', symbol = symbol, name = '15M') 
			datasetio.Delete(type_feature = 'lags_minmaxscaler', symbol = symbol, name = '1H')
			datasetio.Delete(type_feature = 'lags_minmaxscaler', symbol = symbol, name = '4H')
			datasetio.Delete(type_feature = 'lags_minmaxscaler', symbol = symbol, name = '1D')

			lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D = self.Run(
																										dataset_5M = dataset_5M,
																										dataset_15M = dataset_15M,
																										dataset_1H = dataset_1H,
																										dataset_4H = dataset_4H,
																										dataset_1D = dataset_1D,
																										symbol = symbol, 
																										number_lags = number_lags,
																										mode = mode
																										)

			datasetio.Write(type_feature = 'lags', dataset = lag_feature_5M, symbol = symbol, name = '5M')
			datasetio.Write(type_feature = 'lags', dataset = lag_feature_15M, symbol = symbol, name = '15M')
			datasetio.Write(type_feature = 'lags', dataset = lag_feature_1H, symbol = symbol, name = '1H')
			datasetio.Write(type_feature = 'lags', dataset = lag_feature_4H, symbol = symbol, name = '4H')
			datasetio.Write(type_feature = 'lags', dataset = lag_feature_1D, symbol = symbol, name = '1D')

			minmax_scaler_5M = pd.DataFrame(index = [0])
			minmax_scaler_5M['min_' + lag_feature_5M.columns] = lag_feature_5M.min()
			minmax_scaler_5M['max_' + lag_feature_5M.columns] = lag_feature_5M.max()

			minmax_scaler_15M = pd.DataFrame(index = [0])
			minmax_scaler_15M['min_' + lag_feature_15M.columns] = lag_feature_15M.min()
			minmax_scaler_15M['max_' + lag_feature_15M.columns] = lag_feature_15M.max()

			minmax_scaler_1H = pd.DataFrame(index = [0])
			minmax_scaler_1H['min_' + lag_feature_1H.columns] = lag_feature_1H.min()
			minmax_scaler_1H['max_' + lag_feature_1H.columns] = lag_feature_1H.max()

			minmax_scaler_4H = pd.DataFrame(index = [0])
			minmax_scaler_4H['min_' + lag_feature_4H.columns] = lag_feature_4H.min()
			minmax_scaler_4H['max_' + lag_feature_4H.columns] = lag_feature_4H.max()

			minmax_scaler_1D = pd.DataFrame(index = [0])
			minmax_scaler_1D['min_' + lag_feature_1D.columns] = lag_feature_1D.min()
			minmax_scaler_1D['max_' + lag_feature_1D.columns] = lag_feature_1D.max()

			datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
			datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
			datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
			datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
			datasetio.Write(type_feature = 'lags_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')

			return lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D

		elif mode == 'online':

			lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D = self.Run(
																										dataset_5M = dataset_5M,
																										dataset_15M = dataset_15M,
																										dataset_1H = dataset_1H,
																										dataset_4H = dataset_4H,
																										dataset_1D = dataset_1D,
																										symbol = symbol, 
																										number_lags = number_lags,
																										mode = mode
																										)

			return lag_feature_5M, lag_feature_15M, lag_feature_1H, lag_feature_4H, lag_feature_1D