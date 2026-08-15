from sklearn.feature_selection import mutual_info_regression as MIR
from src.utils.FeatureEngineering.MinMaxScaler import MinMaxScaler
from sklearn.decomposition import PCA
from .DatasetIO import DatasetIO
import pandas as pd
import numpy as np

class PCAMI:

	def PCA(self, dataset):
		
		minmax_scaler = MinMaxScaler()

		pca = PCA(n_components = 'mle', copy = True, svd_solver = 'full')

		X_scale, _, _, _, _ = minmax_scaler(
											dataset_5M = dataset,
											dataset_15M = dataset,
											dataset_1H = dataset,
											dataset_4H = dataset,
											dataset_1D = dataset,
											)

		X_pca = pca.fit_transform(X_scale)

		X_pca = pd.DataFrame(X_pca, columns = pca.get_feature_names_out(input_features=dataset.columns))

		return X_pca, X_scale

	def MakeMIScores(self, input_pca, target):

		minmax_scaler = MinMaxScaler()
		input_pca, _, _, _, _ = minmax_scaler(
											dataset_5M = input_pca,
											dataset_15M = input_pca,
											dataset_1H = input_pca,
											dataset_4H = input_pca,
											dataset_1D = input_pca,
											)

		mi_scores = MIR(input_pca, target, discrete_features = 'auto')
		mi_scores = pd.DataFrame(mi_scores, columns = ['pca'], index = input_pca.columns)

		return mi_scores[mi_scores['pca'] > 0.1]

	def NewFeatureFinder(self, dataset):

		data_pca, data_scale = self.PCA(dataset = dataset)
		mi_dataset = pd.DataFrame()

		for clm in dataset.columns:
			mi_dataset = mi_dataset.append(self.MakeMIScores(input_pca = data_pca, target = data_scale[clm]))

		mi_dataset = mi_dataset.sort_values(by = ['pca'], ascending = False)
		mi_dataset['names'] = mi_dataset.index
		mi_dataset = mi_dataset.drop_duplicates(subset = ['names'], keep = 'first')
		mi_dataset = mi_dataset[mi_dataset['pca'] >= 0.2]
		mi_dataset = mi_dataset.drop(columns = ['pca']).reset_index(drop = True)

		return mi_dataset

	def Run(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol):

		datasetio = DatasetIO()

		#Names :
		datasetio.Delete(type_feature = 'pca_names', symbol = symbol, name = '5M')
		datasetio.Delete(type_feature = 'pca_names', symbol = symbol, name = '15M')
		datasetio.Delete(type_feature = 'pca_names', symbol = symbol, name = '1H')
		datasetio.Delete(type_feature = 'pca_names', symbol = symbol, name = '4H')
		datasetio.Delete(type_feature = 'pca_names', symbol = symbol, name = '1D')

		pca_names_5M = self.NewFeatureFinder(dataset = dataset_5M[len(dataset_5M) - 200 : ])
		pca_names_15M = self.NewFeatureFinder(dataset = dataset_15M[len(dataset_15M) - 200 : ])
		pca_names_1H = self.NewFeatureFinder(dataset = dataset_1H[len(dataset_1H) - 200 : ])
		pca_names_4H = self.NewFeatureFinder(dataset = dataset_4H[len(dataset_4H) - 200 : ])
		pca_names_1D = self.NewFeatureFinder(dataset = dataset_1D[len(dataset_1D) - 200 : ])

		pca_names = pd.DataFrame(index = pca_names_5M.index)
		pca_names['names'] = np.nan
		counter = 0
		for elm in pca_names_5M['names'].values:
			if (
				elm in pca_names_15M['names'].values and
				elm in pca_names_1H['names'].values and
				elm in pca_names_4H['names'].values and
				elm in pca_names_1D['names'].values
				):
				pca_names['names'][counter] = elm
				counter += 1

		pca_names = pca_names.dropna()

		datasetio.Write(type_feature = 'pca_names', dataset = pca_names, symbol = symbol, name = '5M')
		datasetio.Write(type_feature = 'pca_names', dataset = pca_names, symbol = symbol, name = '15M')
		datasetio.Write(type_feature = 'pca_names', dataset = pca_names, symbol = symbol, name = '1H')
		datasetio.Write(type_feature = 'pca_names', dataset = pca_names, symbol = symbol, name = '4H')
		datasetio.Write(type_feature = 'pca_names', dataset = pca_names, symbol = symbol, name = '1D')
		#////////////////////////////////////////

		#PCA's:
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '5M')
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '15M')
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '1H')
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '4H')
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '1D')

		data_pca_5M, _ = self.PCA(dataset = dataset_5M)
		data_pca_5M = data_pca_5M[pca_names['names'].values]

		data_pca_15M, _ = self.PCA(dataset = dataset_15M)
		data_pca_15M = data_pca_15M[pca_names['names'].values]

		data_pca_1H, _ = self.PCA(dataset = dataset_1H)
		data_pca_1H = data_pca_1H[pca_names['names'].values]

		data_pca_4H, _ = self.PCA(dataset = dataset_4H)
		data_pca_4H = data_pca_4H[pca_names['names'].values]

		data_pca_1D, _ = self.PCA(dataset = dataset_1D)
		data_pca_1D = data_pca_1D[pca_names['names'].values]

		datasetio.Write(type_feature = 'pca', dataset = data_pca_5M, symbol = symbol, name = '5M')
		datasetio.Write(type_feature = 'pca', dataset = data_pca_15M, symbol = symbol, name = '15M')
		datasetio.Write(type_feature = 'pca', dataset = data_pca_1H, symbol = symbol, name = '1H')
		datasetio.Write(type_feature = 'pca', dataset = data_pca_4H, symbol = symbol, name = '4H')
		datasetio.Write(type_feature = 'pca', dataset = data_pca_1D, symbol = symbol, name = '1D')
		#/////////////////////////////////////////

		#MinMaxScaler:
		datasetio.Delete(type_feature = 'pca_minmaxscaler', symbol = symbol, name = '5M')
		datasetio.Delete(type_feature = 'pca_minmaxscaler', symbol = symbol, name = '15M')
		datasetio.Delete(type_feature = 'pca_minmaxscaler', symbol = symbol, name = '1H')
		datasetio.Delete(type_feature = 'pca_minmaxscaler', symbol = symbol, name = '4H')
		datasetio.Delete(type_feature = 'pca_minmaxscaler', symbol = symbol, name = '1D')

		minmax_scaler_5M = pd.DataFrame(index = [0])
		minmax_scaler_5M['min_' + data_pca_5M.columns] = data_pca_5M.min()
		minmax_scaler_5M['max_' + data_pca_5M.columns] = data_pca_5M.max()

		minmax_scaler_15M = pd.DataFrame(index = [0])
		minmax_scaler_15M['min_' + data_pca_15M.columns] = data_pca_15M.min()
		minmax_scaler_15M['max_' + data_pca_15M.columns] = data_pca_15M.max()

		minmax_scaler_1H = pd.DataFrame(index = [0])
		minmax_scaler_1H['min_' + data_pca_1H.columns] = data_pca_1H.min()
		minmax_scaler_1H['max_' + data_pca_1H.columns] = data_pca_1H.max()

		minmax_scaler_4H = pd.DataFrame(index = [0])
		minmax_scaler_4H['min_' + data_pca_4H.columns] = data_pca_4H.min()
		minmax_scaler_4H['max_' + data_pca_4H.columns] = data_pca_4H.max()

		minmax_scaler_1D = pd.DataFrame(index = [0])
		minmax_scaler_1D['min_' + data_pca_1D.columns] = data_pca_1D.min()
		minmax_scaler_1D['max_' + data_pca_1D.columns] = data_pca_1D.max()

		datasetio.Write(type_feature = 'pca_minmaxscaler', dataset = minmax_scaler_5M, symbol = symbol, name = '5M')
		datasetio.Write(type_feature = 'pca_minmaxscaler', dataset = minmax_scaler_15M, symbol = symbol, name = '15M')
		datasetio.Write(type_feature = 'pca_minmaxscaler', dataset = minmax_scaler_1H, symbol = symbol, name = '1H')
		datasetio.Write(type_feature = 'pca_minmaxscaler', dataset = minmax_scaler_4H, symbol = symbol, name = '4H')
		datasetio.Write(type_feature = 'pca_minmaxscaler', dataset = minmax_scaler_1D, symbol = symbol, name = '1D')
		#//////////////////////////////////////

		return data_pca_5M, data_pca_15M, data_pca_1H, data_pca_4H, data_pca_1D


	def Get(self, dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D, symbol, mode):

		datasetio = DatasetIO()

		if mode == 'Run':
			pca_feature_5M, pca_feature_15M, pca_feature_1H, pca_feature_4H, pca_feature_1D = self.Run(
																										dataset_5M = dataset_5M, 
																										dataset_15M = dataset_15M, 
																										dataset_1H = dataset_1H, 
																										dataset_4H = dataset_4H, 
																										dataset_1D = dataset_1D, 
																										symbol = symbol
																										)

			return pca_feature_5M, pca_feature_15M, pca_feature_1H, pca_feature_4H, pca_feature_1D

		elif mode == None:

			pca_feature_5M = datasetio.Read(type_feature = 'pca', symbol = symbol, name = '5M')
			pca_feature_15M = datasetio.Read(type_feature = 'pca', symbol = symbol, name = '15M')
			pca_feature_1H = datasetio.Read(type_feature = 'pca', symbol = symbol, name = '1H')
			pca_feature_4H = datasetio.Read(type_feature = 'pca', symbol = symbol, name = '4H')
			pca_feature_1D = datasetio.Read(type_feature = 'pca', symbol = symbol, name = '1D')

			if (
				pca_feature_5M.empty == True and
				pca_feature_15M.empty == True and
				pca_feature_1H.empty == True and
				pca_feature_4H.empty == True and
				pca_feature_1D.empty == True
				):

				pca_feature_5M, pca_feature_15M, pca_feature_1H, pca_feature_4H, pca_feature_1D = self.Run(
																											dataset_5M = dataset_5M, 
																											dataset_15M = dataset_15M, 
																											dataset_1H = dataset_1H, 
																											dataset_4H = dataset_4H, 
																											dataset_1D = dataset_1D, 
																											symbol = symbol
																											)

			return pca_feature_5M, pca_feature_15M, pca_feature_1H, pca_feature_4H, pca_feature_1D

		elif mode == 'online':

			pca_names_5M = datasetio.Read(type_feature = 'pca_names', symbol = symbol, name = '5M')
			pca_names_15M = datasetio.Read(type_feature = 'pca_names', symbol = symbol, name = '15M')
			pca_names_1H = datasetio.Read(type_feature = 'pca_names', symbol = symbol, name = '1H')
			pca_names_4H = datasetio.Read(type_feature = 'pca_names', symbol = symbol, name = '4H')
			pca_names_1D = datasetio.Read(type_feature = 'pca_names', symbol = symbol, name = '1D')

			feature_pca_5M, _ = self.PCA(dataset = dataset_5M)
			feature_pca_5M = feature_pca_5M[pca_names_5M['names'].values]

			feature_pca_15M, _ = self.PCA(dataset = dataset_15M)
			feature_pca_15M = feature_pca_15M[pca_names_15M['names'].values]

			feature_pca_1H, _ = self.PCA(dataset = dataset_1H)
			feature_pca_1H = feature_pca_1H[pca_names_1H['names'].values]

			feature_pca_4H, _ = self.PCA(dataset = dataset_4H)
			feature_pca_4H = feature_pca_4H[pca_names_4H['names'].values]

			feature_pca_1D, _ = self.PCA(dataset = dataset_1D)
			feature_pca_1D = feature_pca_1D[pca_names_1D['names'].values]

			return feature_pca_5M, feature_pca_15M, feature_pca_1H, feature_pca_4H, feature_pca_1D