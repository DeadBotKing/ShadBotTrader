from mlxtend.preprocessing import minmax_scaling
from .DatasetIO import DatasetIO
from .Config import Config
import pandas as pd

class MinMaxScaler:

	def Run(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, name_feature, symbol = 'XAUUSD_i'):

		if name_feature != '':
			datasetio = DatasetIO()
			data_minmax_5M = datasetio.Read(type_feature = name_feature + '_minmaxscaler', symbol = symbol, name = '5M')
			data_minmax_15M = datasetio.Read(type_feature = name_feature + '_minmaxscaler', symbol = symbol, name = '15M')
			data_minmax_1H = datasetio.Read(type_feature = name_feature + '_minmaxscaler', symbol = symbol, name = '1H')
			data_minmax_4H = datasetio.Read(type_feature = name_feature + '_minmaxscaler', symbol = symbol, name = '4H')
			data_minmax_1D = datasetio.Read(type_feature = name_feature + '_minmaxscaler', symbol = symbol, name = '1D')
		else:
			data_minmax_5M = pd.DataFrame()
			data_minmax_15M = pd.DataFrame()
			data_minmax_1H = pd.DataFrame()
			data_minmax_4H = pd.DataFrame()
			data_minmax_1D = pd.DataFrame()
			

		dataset_5M_ = dataset_5M.copy(deep = True)
		dataset_15M_ = dataset_15M.copy(deep = True)
		dataset_1H_ = dataset_1H.copy(deep = True)
		dataset_4H_ = dataset_4H.copy(deep = True)
		dataset_1D_ = dataset_1D.copy(deep = True)

		if symbol in dataset_5M.columns: dataset_5M_ = dataset_5M.copy(deep = True).drop(columns = [symbol])
		if symbol in dataset_15M.columns: dataset_15M_ = dataset_15M.copy(deep = True).drop(columns = [symbol])
		if symbol in dataset_1H.columns: dataset_1H_ = dataset_1H.copy(deep = True).drop(columns = [symbol])
		if symbol in dataset_4H.columns: dataset_4H_ = dataset_4H.copy(deep = True).drop(columns = [symbol])
		if symbol in dataset_1D.columns: dataset_1D_ = dataset_1D.copy(deep = True).drop(columns = [symbol])

		if 'time' in dataset_5M_.columns: dataset_5M_ = dataset_5M_.copy(deep = True).drop(columns = ['time'])
		if 'time' in dataset_15M_.columns: dataset_15M_ = dataset_15M_.copy(deep = True).drop(columns = ['time'])
		if 'time' in dataset_1H_.columns: dataset_1H_ = dataset_1H_.copy(deep = True).drop(columns = ['time'])
		if 'time' in dataset_4H_.columns: dataset_4H_ = dataset_4H_.copy(deep = True).drop(columns = ['time'])
		if 'time' in dataset_1D_.columns: dataset_1D_ = dataset_1D_.copy(deep = True).drop(columns = ['time'])

		scale_5M = pd.DataFrame()
		scale_15M = pd.DataFrame()
		scale_1H = pd.DataFrame()
		scale_4H = pd.DataFrame()
		scale_1D = pd.DataFrame()

		if (
			data_minmax_5M.empty == False and
			data_minmax_15M.empty == False and
			data_minmax_1H.empty == False and
			data_minmax_4H.empty == False and
			data_minmax_1D.empty == False and
			name_feature != ''
			):
			#5M ***********************:
			scale_5M = (
						(dataset_5M_[dataset_5M_.columns] - data_minmax_5M['min_' + dataset_5M_.columns].iloc[0].values) /
						(data_minmax_5M['max_' + dataset_5M_.columns].iloc[0].values - data_minmax_5M['min_' + dataset_5M_.columns].iloc[0].values)
						)

			if (dataset_5M_[dataset_5M_.columns].min().values < data_minmax_5M['min_' + dataset_5M_.columns].iloc[0].values).any():
				scale_5M = pd.DataFrame()
			#///////////////////////////////////

			#15M *******************:
			scale_15M = (
						(dataset_15M_[dataset_15M_.columns] - data_minmax_15M['min_' + dataset_15M_.columns].iloc[0].values) /
						(data_minmax_15M['max_' + dataset_15M_.columns].iloc[0].values - data_minmax_15M['min_' + dataset_15M_.columns].iloc[0].values)
						)

			if (dataset_15M_[dataset_15M_.columns].min().values < data_minmax_15M['min_' + dataset_15M_.columns].iloc[0].values).any():
				scale_15M = pd.DataFrame()
			#//////////////////////////////////

			#1H *************:
			scale_1H = (
						(dataset_1H_[dataset_1H_.columns] - data_minmax_1H['min_' + dataset_1H_.columns].iloc[0].values) /
						(data_minmax_1H['max_' + dataset_1H_.columns].iloc[0].values - data_minmax_1H['min_' + dataset_1H_.columns].iloc[0].values)
						)

			if (dataset_1H_[dataset_1H_.columns].min().values < data_minmax_1H['min_' + dataset_1H_.columns].iloc[0].values).any():
				scale_1H = pd.DataFrame()
			#///////////////////////////////////

			#4H *************:
			scale_4H = (
						(dataset_4H_[dataset_4H_.columns] - data_minmax_4H['min_' + dataset_4H_.columns].iloc[0].values) /
						(data_minmax_4H['max_' + dataset_4H_.columns].iloc[0].values - data_minmax_4H['min_' + dataset_4H_.columns].iloc[0].values)
						)

			if (dataset_4H_[dataset_4H_.columns].min().values < data_minmax_4H['min_' + dataset_4H_.columns].iloc[0].values).any():
				scale_4H = pd.DataFrame()
			#///////////////////////////////////

			#1D *************:
			scale_1D = (
						(dataset_1D_[dataset_1D_.columns] - data_minmax_1D['min_' + dataset_1D_.columns].iloc[0].values) /
						(data_minmax_1D['max_' + dataset_1D_.columns].iloc[0].values - data_minmax_1D['min_' + dataset_1D_.columns].iloc[0].values)
						)

			if (dataset_1D_[dataset_1D_.columns].min().values < data_minmax_1D['min_' + dataset_1D_.columns].iloc[0].values).any():
				scale_1D = pd.DataFrame()
			#///////////////////////////////////

		
		if scale_5M.empty == True: scale_5M = minmax_scaling(dataset_5M_, columns = dataset_5M_.columns)
		if scale_15M.empty == True: scale_15M = minmax_scaling(dataset_15M_, columns = dataset_15M_.columns)
		if scale_1H.empty == True: scale_1H = minmax_scaling(dataset_1H_, columns = dataset_1H_.columns)
		if scale_4H.empty == True: scale_4H = minmax_scaling(dataset_4H_, columns = dataset_4H_.columns)
		if scale_1D.empty == True: scale_1D = minmax_scaling(dataset_1D_, columns = dataset_1D_.columns)

		return scale_5M, scale_15M, scale_1H, scale_4H, scale_1D

	def __call__(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, name_feature = '', symbol = 'XAUUSD_i'):
		return self.Run(
						dataset_5M = dataset_5M, 
						dataset_15M = dataset_15M, 
						dataset_1H = dataset_1H, 
						dataset_4H = dataset_4H,
						dataset_1D = dataset_1D, 
						name_feature = name_feature, 
						symbol = symbol
						)

