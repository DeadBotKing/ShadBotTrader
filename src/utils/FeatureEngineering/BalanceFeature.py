from src.utils.FeatureEngineering.Patterns import Patterns
from src.utils.Tools.timer import stTime
from intersect import intersection
from sklearn.cluster import KMeans
import pandas as pd
import numpy as np

class BalanceFeature:

	def __init__(self):

		self.flag_5M = False
		self.flag_15M = False
		self.flag_1H = False
		self.flag_4H = False
		self.flag_1D = True

	# @stTime
	def Prices(
				self, 
				dataset_5M, 
				dataset_15M, 
				dataset_1H, 
				dataset_4H, 
				dataset_1D, 
				color_pattern_5M, 
				color_pattern_15M, 
				color_pattern_1H,
				color_pattern_4H,
				color_pattern_1D
				):

		#5M ******************************:
		if self.flag_5M == True:

			kmeans_prices = KMeans(
								algorithm = "elkan",
								n_clusters = int(len(dataset_5M.index)/50), 
								copy_x = True,
								random_state = 0,
								init = 'k-means++',
								verbose = 0,
								n_init = 10,
								max_iter = 300,
								tol = 0.0001
								)

			green_candles_5M = pd.DataFrame(index = dataset_5M.index)
			green_candles_5M['close'] = dataset_5M['close'][color_pattern_5M['color_candle'] == 1]
			green_candles_5M['volume'] = dataset_5M['volume'][color_pattern_5M['color_candle'] == 1]

			duplicated_green_price_1_5M = green_candles_5M['close'][green_candles_5M['close'].duplicated() == True]
			duplicated_green_price_1_5M = duplicated_green_price_1_5M.dropna()

			if duplicated_green_price_1_5M.empty == False:
				for dup_price in duplicated_green_price_1_5M.values:
					index_green_duplicate_5M = dataset_5M.index[dataset_5M['close'] == dup_price]
					green_candles_5M['volume'][index_green_duplicate_5M] = green_candles_5M['volume'][index_green_duplicate_5M].sum()

			red_candles_5M = pd.DataFrame(index = dataset_5M.index)
			red_candles_5M['close'] = dataset_5M['close'][color_pattern_5M['color_candle'] == 0]
			red_candles_5M['volume'] = dataset_5M['volume'][color_pattern_5M['color_candle'] == 0]

			duplicated_red_price_1_5M = red_candles_5M['close'][red_candles_5M['close'].duplicated() == True]
			duplicated_red_price_1_5M = duplicated_red_price_1_5M.dropna()

			if duplicated_red_price_1_5M.empty == False:
				for dup_price in duplicated_red_price_1_5M.values:
					index_red_duplicate_5M = dataset_5M.index[dataset_5M['close'] == dup_price]
					red_candles_5M['volume'][index_red_duplicate_5M] = red_candles_5M['volume'][index_red_duplicate_5M].sum()

			green_candles_5M = green_candles_5M.dropna().sort_values(by = ['volume'])
			green_candles_5M.index = green_candles_5M['volume']
			red_candles_5M = red_candles_5M.dropna().sort_values(by = ['volume'])
			red_candles_5M.index = red_candles_5M['volume']

			print(green_candles_5M.index)
			print(red_candles_5M.index)



			volume_balance_5M, price_balance_5M = intersection(
																green_candles_5M.index,
																green_candles_5M['close'], 
																red_candles_5M.index, 
																red_candles_5M['close']
																)

			balace_volumes_5M = kmeans_prices.fit(volume_balance_5M.reshape(-1, 1))
			volume_balance_5M = balace_volumes_5M.cluster_centers_
			b_volumes_5M = kmeans_prices.predict(dataset_5M['volume'].to_numpy().reshape(-1, 1))

			balace_prices_5M = kmeans_prices.fit(price_balance_5M.reshape(-1, 1))
			price_balance_5M = balace_prices_5M.cluster_centers_
			b_prices_5M = kmeans_prices.predict(dataset_5M['close'].to_numpy().reshape(-1, 1))

			balance_feature_5M = pd.DataFrame(index = dataset_5M.index)
			balance_feature_5M['price_balance'] = price_balance_5M[b_prices_5M]
			balance_feature_5M['volume_balance'] = volume_balance_5M[b_volumes_5M]

			balance_feature_5M['diff_price_balance'] = dataset_5M['close'] - balance_feature_5M['price_balance']
			balance_feature_5M['diff_volume_balance'] = dataset_5M['volume'] - balance_feature_5M['volume_balance']

		else:
			balance_feature_5M = pd.DataFrame()
		#///////////////////////////////////////////////////////////////////

		#15M ******************************:
		if self.flag_15M == True:

			kmeans_prices = KMeans(
								algorithm = "elkan",
								n_clusters = int(len(dataset_15M.index)/50), 
								copy_x = True,
								random_state = 0,
								init = 'k-means++',
								verbose = 0,
								n_init = 10,
								max_iter = 300,
								tol = 0.0001
								)

			green_candles_15M = pd.DataFrame(index = dataset_15M.index)
			green_candles_15M['close'] = dataset_15M['close'][color_pattern_15M['color_candle'] == 1]
			green_candles_15M['volume'] = dataset_15M['volume'][color_pattern_15M['color_candle'] == 1]

			duplicated_green_price_1_15M = green_candles_15M['close'][green_candles_15M['close'].duplicated() == True]
			duplicated_green_price_1_15M = duplicated_green_price_1_15M.dropna()

			if duplicated_green_price_1_15M.empty == False:
				for dup_price in duplicated_green_price_1_15M.values:
					index_green_duplicate_15M = dataset_15M.index[dataset_15M['close'] == dup_price]
					green_candles_15M['volume'][index_green_duplicate_15M] = green_candles_15M['volume'][index_green_duplicate_15M].sum()

			red_candles_15M = pd.DataFrame(index = dataset_15M.index)
			red_candles_15M['close'] = dataset_15M['close'][color_pattern_15M['color_candle'] == 0]
			red_candles_15M['volume'] = dataset_15M['volume'][color_pattern_15M['color_candle'] == 0]

			duplicated_red_price_1_15M = red_candles_15M['close'][red_candles_15M['close'].duplicated() == True]
			duplicated_red_price_1_15M = duplicated_red_price_1_15M.dropna()

			if duplicated_red_price_1_15M.empty == False:
				for dup_price in duplicated_red_price_1_15M.values:
					index_red_duplicate_15M = dataset_15M.index[dataset_15M['close'] == dup_price]
					red_candles_15M['volume'][index_red_duplicate_15M] = red_candles_15M['volume'][index_red_duplicate_15M].sum()

			green_candles_15M = green_candles_15M.dropna().sort_values(by = ['volume'])
			green_candles_15M.index = green_candles_15M['volume']
			red_candles_15M = red_candles_15M.dropna().sort_values(by = ['volume'])
			red_candles_15M.index = red_candles_15M['volume']

			volume_balance_15M, price_balance_15M = intersection(
																green_candles_15M.index,
																green_candles_15M['close'], 
																red_candles_15M.index, 
																red_candles_15M['close']
																)

			balace_volumes_15M = kmeans_prices.fit(volume_balance_15M.reshape(-1, 1))
			volume_balance_15M = balace_volumes_15M.cluster_centers_
			b_volumes_15M = kmeans_prices.predict(dataset_15M['volume'].to_numpy().reshape(-1, 1))

			balace_prices_15M = kmeans_prices.fit(price_balance_15M.reshape(-1, 1))
			price_balance_15M = balace_prices_15M.cluster_centers_
			b_prices_15M = kmeans_prices.predict(dataset_15M['close'].to_numpy().reshape(-1, 1))

			balance_feature_15M = pd.DataFrame(index = dataset_15M.index)
			balance_feature_15M['price_balance'] = price_balance_15M[b_prices_15M]
			balance_feature_15M['volume_balance'] = volume_balance_15M[b_volumes_15M]

			balance_feature_15M['diff_price_balance'] = dataset_15M['close'] - balance_feature_15M['price_balance']
			balance_feature_15M['diff_volume_balance'] = dataset_15M['volume'] - balance_feature_15M['volume_balance']

		else:
			balance_feature_15M = pd.DataFrame()
		#///////////////////////////////////////////////////////////////////


		#1H ******************************:
		if self.flag_1H == True:

			kmeans_prices = KMeans(
								algorithm = "elkan",
								n_clusters = int(len(dataset_1H.index)/50), 
								copy_x = True,
								random_state = 0,
								init = 'k-means++',
								verbose = 0,
								n_init = 10,
								max_iter = 300,
								tol = 0.0001
								)

			green_candles_1H = pd.DataFrame(index = dataset_1H.index)
			green_candles_1H['close'] = dataset_1H['close'][color_pattern_1H['color_candle'] == 1]
			green_candles_1H['volume'] = dataset_1H['volume'][color_pattern_1H['color_candle'] == 1]

			duplicated_green_price_1_1H = green_candles_1H['close'][green_candles_1H['close'].duplicated() == True]
			duplicated_green_price_1_1H = duplicated_green_price_1_1H.dropna()

			if duplicated_green_price_1_1H.empty == False:
				for dup_price in duplicated_green_price_1_1H.values:
					index_green_duplicate_1H = dataset_1H.index[dataset_1H['close'] == dup_price]
					green_candles_1H['volume'][index_green_duplicate_1H] = green_candles_1H['volume'][index_green_duplicate_1H].sum()

			red_candles_1H = pd.DataFrame(index = dataset_1H.index)
			red_candles_1H['close'] = dataset_1H['close'][color_pattern_1H['color_candle'] == 0]
			red_candles_1H['volume'] = dataset_1H['volume'][color_pattern_1H['color_candle'] == 0]

			duplicated_red_price_1_1H = red_candles_1H['close'][red_candles_1H['close'].duplicated() == True]
			duplicated_red_price_1_1H = duplicated_red_price_1_1H.dropna()

			if duplicated_red_price_1_1H.empty == False:
				for dup_price in duplicated_red_price_1_1H.values:
					index_red_duplicate_1H = dataset_1H.index[dataset_1H['close'] == dup_price]
					red_candles_1H['volume'][index_red_duplicate_1H] = red_candles_1H['volume'][index_red_duplicate_1H].sum()

			green_candles_1H = green_candles_1H.dropna().sort_values(by = ['volume'])
			green_candles_1H.index = green_candles_1H['volume']
			red_candles_1H = red_candles_1H.dropna().sort_values(by = ['volume'])
			red_candles_1H.index = red_candles_1H['volume']

			volume_balance_1H, price_balance_1H = intersection(
																green_candles_1H.index,
																green_candles_1H['close'], 
																red_candles_1H.index, 
																red_candles_1H['close']
																)

			balace_volumes_1H = kmeans_prices.fit(volume_balance_1H.reshape(-1, 1))
			volume_balance_1H = balace_volumes_1H.cluster_centers_
			b_volumes_1H = kmeans_prices.predict(dataset_1H['volume'].to_numpy().reshape(-1, 1))

			balace_prices_1H = kmeans_prices.fit(price_balance_1H.reshape(-1, 1))
			price_balance_1H = balace_prices_1H.cluster_centers_
			b_prices_1H = kmeans_prices.predict(dataset_1H['close'].to_numpy().reshape(-1, 1))

			balance_feature_1H = pd.DataFrame(index = dataset_1H.index)
			balance_feature_1H['price_balance'] = price_balance_1H[b_prices_1H]
			balance_feature_1H['volume_balance'] = volume_balance_1H[b_volumes_1H]

			balance_feature_1H['diff_price_balance'] = dataset_1H['close'] - balance_feature_1H['price_balance']
			balance_feature_1H['diff_volume_balance'] = dataset_1H['volume'] - balance_feature_1H['volume_balance']

		else:
			balance_feature_1H = pd.DataFrame()
		#///////////////////////////////////////////////////////////////////

		#4H ******************************:
		if self.flag_4H == True:

			kmeans_prices = KMeans(
								algorithm = "elkan",
								n_clusters = int(len(dataset_4H.index)/50), 
								copy_x = True,
								random_state = 0,
								init = 'k-means++',
								verbose = 0,
								n_init = 10,
								max_iter = 300,
								tol = 0.0001
								)

			green_candles_4H = pd.DataFrame(index = dataset_4H.index)
			green_candles_4H['close'] = dataset_4H['close'][color_pattern_4H['color_candle'] == 1]
			green_candles_4H['volume'] = dataset_4H['volume'][color_pattern_4H['color_candle'] == 1]

			duplicated_green_price_1_4H = green_candles_4H['close'][green_candles_4H['close'].duplicated() == True]
			duplicated_green_price_1_4H = duplicated_green_price_1_4H.dropna()

			if duplicated_green_price_1_4H.empty == False:
				for dup_price in duplicated_green_price_1_4H.values:
					index_green_duplicate_4H = dataset_4H.index[dataset_4H['close'] == dup_price]
					green_candles_4H['volume'][index_green_duplicate_4H] = green_candles_4H['volume'][index_green_duplicate_4H].sum()

			red_candles_4H = pd.DataFrame(index = dataset_4H.index)
			red_candles_4H['close'] = dataset_4H['close'][color_pattern_4H['color_candle'] == 0]
			red_candles_4H['volume'] = dataset_4H['volume'][color_pattern_4H['color_candle'] == 0]

			duplicated_red_price_1_4H = red_candles_4H['close'][red_candles_4H['close'].duplicated() == True]
			duplicated_red_price_1_4H = duplicated_red_price_1_4H.dropna()

			if duplicated_red_price_1_4H.empty == False:
				for dup_price in duplicated_red_price_1_4H.values:
					index_red_duplicate_4H = dataset_4H.index[dataset_4H['close'] == dup_price]
					red_candles_4H['volume'][index_red_duplicate_4H] = red_candles_4H['volume'][index_red_duplicate_4H].sum()

			green_candles_4H = green_candles_4H.dropna().sort_values(by = ['volume'])
			green_candles_4H.index = green_candles_4H['volume']
			red_candles_4H = red_candles_4H.dropna().sort_values(by = ['volume'])
			red_candles_4H.index = red_candles_4H['volume']

			volume_balance_4H, price_balance_4H = intersection(
																green_candles_4H.index,
																green_candles_4H['close'], 
																red_candles_4H.index, 
																red_candles_4H['close']
																)

			balace_volumes_4H = kmeans_prices.fit(volume_balance_4H.reshape(-1, 1))
			volume_balance_4H = balace_volumes_4H.cluster_centers_
			b_volumes_4H = kmeans_prices.predict(dataset_4H['volume'].to_numpy().reshape(-1, 1))

			balace_prices_4H = kmeans_prices.fit(price_balance_4H.reshape(-1, 1))
			price_balance_4H = balace_prices_4H.cluster_centers_
			b_prices_4H = kmeans_prices.predict(dataset_4H['close'].to_numpy().reshape(-1, 1))

			balance_feature_4H = pd.DataFrame(index = dataset_4H.index)
			balance_feature_4H['price_balance'] = price_balance_4H[b_prices_4H]
			balance_feature_4H['volume_balance'] = volume_balance_4H[b_volumes_4H]

			balance_feature_4H['diff_price_balance'] = dataset_4H['close'] - balance_feature_4H['price_balance']
			balance_feature_4H['diff_volume_balance'] = dataset_4H['volume'] - balance_feature_4H['volume_balance']

		else:
			balance_feature_4H = pd.DataFrame()
		#///////////////////////////////////////////////////////////////////

		#1D ******************************:
		if self.flag_1D == True:

			kmeans_prices = KMeans(
								algorithm = "elkan",
								n_clusters = int(len(dataset_1D.index)/50), 
								copy_x = True,
								random_state = 0,
								init = 'k-means++',
								verbose = 0,
								n_init = 10,
								max_iter = 300,
								tol = 0.0001
								)

			green_candles_1D = pd.DataFrame(index = dataset_1D.index)
			green_candles_1D['close'] = dataset_1D['close'][color_pattern_1D['color_candle'] == 1]
			green_candles_1D['volume'] = dataset_1D['volume'][color_pattern_1D['color_candle'] == 1]

			duplicated_green_price_1_1D = green_candles_1D['close'][green_candles_1D['close'].duplicated() == True]
			duplicated_green_price_1_1D = duplicated_green_price_1_1D.dropna()

			if duplicated_green_price_1_1D.empty == False:
				for dup_price in duplicated_green_price_1_1D.values:
					index_green_duplicate_1D = dataset_1D.index[dataset_1D['close'] == dup_price]
					green_candles_1D['volume'][index_green_duplicate_1D] = green_candles_1D['volume'][index_green_duplicate_1D].sum()

			red_candles_1D = pd.DataFrame(index = dataset_1D.index)
			red_candles_1D['close'] = dataset_1D['close'][color_pattern_1D['color_candle'] == 0]
			red_candles_1D['volume'] = dataset_1D['volume'][color_pattern_1D['color_candle'] == 0]

			duplicated_red_price_1_1D = red_candles_1D['close'][red_candles_1D['close'].duplicated() == True]
			duplicated_red_price_1_1D = duplicated_red_price_1_1D.dropna()

			if duplicated_red_price_1_1D.empty == False:
				for dup_price in duplicated_red_price_1_1D.values:
					index_red_duplicate_1D = dataset_1D.index[dataset_1D['close'] == dup_price]
					red_candles_1D['volume'][index_red_duplicate_1D] = red_candles_1D['volume'][index_red_duplicate_1D].sum()

			green_candles_1D = green_candles_1D.dropna().sort_values(by = ['volume'])
			green_candles_1D.index = green_candles_1D['volume']
			red_candles_1D = red_candles_1D.dropna().sort_values(by = ['volume'])
			red_candles_1D.index = red_candles_1D['volume']

			volume_balance_1D, price_balance_1D = intersection(
																green_candles_1D.index,
																green_candles_1D['close'], 
																red_candles_1D.index, 
																red_candles_1D['close']
																)

			balace_volumes_1D = kmeans_prices.fit(volume_balance_1D.reshape(-1, 1))
			volume_balance_1D = balace_volumes_1D.cluster_centers_
			b_volumes_1D = kmeans_prices.predict(dataset_1D['volume'].to_numpy().reshape(-1, 1))

			balace_prices_1D = kmeans_prices.fit(price_balance_1D.reshape(-1, 1))
			price_balance_1D = balace_prices_1D.cluster_centers_
			b_prices_1D = kmeans_prices.predict(dataset_1D['close'].to_numpy().reshape(-1, 1))

			balance_feature_1D = pd.DataFrame(index = dataset_1D.index)
			balance_feature_1D['price_balance'] = price_balance_1D[b_prices_1D]
			balance_feature_1D['volume_balance'] = volume_balance_1D[b_volumes_1D]

			balance_feature_1D['diff_price_balance'] = dataset_1D['close'] - balance_feature_1D['price_balance']
			balance_feature_1D['diff_volume_balance'] = dataset_1D['volume'] - balance_feature_1D['volume_balance']

		else:
			balance_feature_1D = pd.DataFrame()
		#///////////////////////////////////////////////////////////////////

		

		return balance_feature_5M, balance_feature_15M, balance_feature_1H, balance_feature_4H, balance_feature_1D

	# @stTime
	def Extension(
					self, 
					dataset_5M, 
					dataset_15M, 
					dataset_1H, 
					dataset_4H, 
					dataset_1D, 
					color_pattern_5M, 
					color_pattern_15M, 
					color_pattern_1H,
					color_pattern_4H,
					color_pattern_1D,
					):

		#5M *******************:
		green_candles_5M = pd.DataFrame(index = dataset_5M.index)
		green_candles_5M['close'] = dataset_5M['close'][color_pattern_5M['color_candle'] == 1]
		green_candles_5M['volume'] = dataset_5M['volume'][color_pattern_5M['color_candle'] == 1]

		green_candles_5M['index'] = green_candles_5M.index

		real_dataset_5M = green_candles_5M.dropna().reset_index()
		shifted_dataset_5M = green_candles_5M.dropna().shift(1).fillna(0).reset_index()

		extension_prices_5M = (real_dataset_5M['close'] - shifted_dataset_5M['close'])/((real_dataset_5M['close'] + shifted_dataset_5M['close'])/2)
		extension_volumes_5M = (real_dataset_5M['volume'] - shifted_dataset_5M['volume'])/((real_dataset_5M['volume'] + shifted_dataset_5M['volume'])/2)
		
		real_dataset_5M['extension'] = extension_volumes_5M/extension_prices_5M
		real_dataset_5M.index = real_dataset_5M['index']
		green_candles_5M['extension'] = real_dataset_5M['extension']
		green_candles_5M['extension'] = green_candles_5M['extension'].fillna(0).replace(np.inf, 1)
		green_candles_5M['extension'] = green_candles_5M['extension'].replace(-np.inf, -1)

		red_candles_5M = pd.DataFrame(index = dataset_5M.index)
		red_candles_5M['close'] = dataset_5M['close'][color_pattern_5M['color_candle'] == 0]
		red_candles_5M['volume'] = dataset_5M['volume'][color_pattern_5M['color_candle'] == 0]

		red_candles_5M['index'] = red_candles_5M.index

		real_dataset_5M = red_candles_5M.dropna().reset_index()
		shifted_dataset_5M = red_candles_5M.dropna().shift(1).fillna(0).reset_index()

		extension_prices_5M = (real_dataset_5M['close'] - shifted_dataset_5M['close'])/((real_dataset_5M['close'] + shifted_dataset_5M['close'])/2)
		extension_volumes_5M = (real_dataset_5M['volume'] - shifted_dataset_5M['volume'])/((real_dataset_5M['volume'] + shifted_dataset_5M['volume'])/2)
		
		real_dataset_5M['extension'] = extension_volumes_5M/extension_prices_5M
		real_dataset_5M.index = real_dataset_5M['index']
		red_candles_5M['extension'] = real_dataset_5M['extension']
		red_candles_5M['extension'] = red_candles_5M['extension'].fillna(0).replace(np.inf, 1)
		red_candles_5M['extension'] = red_candles_5M['extension'].replace(-np.inf, -1)

		extension_feature_5M = pd.DataFrame(index = dataset_5M.index)
		extension_feature_5M['extension_green'] = green_candles_5M['extension']
		extension_feature_5M['extension_red'] = red_candles_5M['extension']
		#///////////////////////////////////////////////


		#15M *******************:
		green_candles_15M = pd.DataFrame(index = dataset_15M.index)
		green_candles_15M['close'] = dataset_15M['close'][color_pattern_15M['color_candle'] == 1]
		green_candles_15M['volume'] = dataset_15M['volume'][color_pattern_15M['color_candle'] == 1]

		green_candles_15M['index'] = green_candles_15M.index

		real_dataset_15M = green_candles_15M.dropna().reset_index()
		shifted_dataset_15M = green_candles_15M.dropna().shift(1).fillna(0).reset_index()

		extension_prices_15M = (real_dataset_15M['close'] - shifted_dataset_15M['close'])/((real_dataset_15M['close'] + shifted_dataset_15M['close'])/2)
		extension_volumes_15M = (real_dataset_15M['volume'] - shifted_dataset_15M['volume'])/((real_dataset_15M['volume'] + shifted_dataset_15M['volume'])/2)
		
		real_dataset_15M['extension'] = extension_volumes_15M/extension_prices_15M
		real_dataset_15M.index = real_dataset_15M['index']
		green_candles_15M['extension'] = real_dataset_15M['extension']
		green_candles_15M['extension'] = green_candles_15M['extension'].fillna(0).replace(np.inf, 1)
		green_candles_15M['extension'] = green_candles_15M['extension'].replace(-np.inf, -1)

		red_candles_15M = pd.DataFrame(index = dataset_15M.index)
		red_candles_15M['close'] = dataset_15M['close'][color_pattern_15M['color_candle'] == 0]
		red_candles_15M['volume'] = dataset_15M['volume'][color_pattern_15M['color_candle'] == 0]

		red_candles_15M['index'] = red_candles_15M.index

		real_dataset_15M = red_candles_15M.dropna().reset_index()
		shifted_dataset_15M = red_candles_15M.dropna().shift(1).fillna(0).reset_index()

		extension_prices_15M = (real_dataset_15M['close'] - shifted_dataset_15M['close'])/((real_dataset_15M['close'] + shifted_dataset_15M['close'])/2)
		extension_volumes_15M = (real_dataset_15M['volume'] - shifted_dataset_15M['volume'])/((real_dataset_15M['volume'] + shifted_dataset_15M['volume'])/2)
		
		real_dataset_15M['extension'] = extension_volumes_15M/extension_prices_15M
		real_dataset_15M.index = real_dataset_15M['index']
		red_candles_15M['extension'] = real_dataset_15M['extension']
		red_candles_15M['extension'] = red_candles_15M['extension'].fillna(0).replace(np.inf, 1)
		red_candles_15M['extension'] = red_candles_15M['extension'].replace(-np.inf, -1)

		extension_feature_15M = pd.DataFrame(index = dataset_15M.index)
		extension_feature_15M['extension_green'] = green_candles_15M['extension']
		extension_feature_15M['extension_red'] = red_candles_15M['extension']
		#///////////////////////////////////////////////


		#1H *******************:
		green_candles_1H = pd.DataFrame(index = dataset_1H.index)
		green_candles_1H['close'] = dataset_1H['close'][color_pattern_1H['color_candle'] == 1]
		green_candles_1H['volume'] = dataset_1H['volume'][color_pattern_1H['color_candle'] == 1]

		green_candles_1H['index'] = green_candles_1H.index

		real_dataset_1H = green_candles_1H.dropna().reset_index()
		shifted_dataset_1H = green_candles_1H.dropna().shift(1).fillna(0).reset_index()

		extension_prices_1H = (real_dataset_1H['close'] - shifted_dataset_1H['close'])/((real_dataset_1H['close'] + shifted_dataset_1H['close'])/2)
		extension_volumes_1H = (real_dataset_1H['volume'] - shifted_dataset_1H['volume'])/((real_dataset_1H['volume'] + shifted_dataset_1H['volume'])/2)
		
		real_dataset_1H['extension'] = extension_volumes_1H/extension_prices_1H
		real_dataset_1H.index = real_dataset_1H['index']
		green_candles_1H['extension'] = real_dataset_1H['extension']
		green_candles_1H['extension'] = green_candles_1H['extension'].fillna(0).replace(np.inf, 1)
		green_candles_1H['extension'] = green_candles_1H['extension'].replace(-np.inf, -1)

		red_candles_1H = pd.DataFrame(index = dataset_1H.index)
		red_candles_1H['close'] = dataset_1H['close'][color_pattern_1H['color_candle'] == 0]
		red_candles_1H['volume'] = dataset_1H['volume'][color_pattern_1H['color_candle'] == 0]

		red_candles_1H['index'] = red_candles_1H.index

		real_dataset_1H = red_candles_1H.dropna().reset_index()
		shifted_dataset_1H = red_candles_1H.dropna().shift(1).fillna(0).reset_index()

		extension_prices_1H = (real_dataset_1H['close'] - shifted_dataset_1H['close'])/((real_dataset_1H['close'] + shifted_dataset_1H['close'])/2)
		extension_volumes_1H = (real_dataset_1H['volume'] - shifted_dataset_1H['volume'])/((real_dataset_1H['volume'] + shifted_dataset_1H['volume'])/2)
		
		real_dataset_1H['extension'] = extension_volumes_1H/extension_prices_1H
		real_dataset_1H.index = real_dataset_1H['index']
		red_candles_1H['extension'] = real_dataset_1H['extension']
		red_candles_1H['extension'] = red_candles_1H['extension'].fillna(0).replace(np.inf, 1)
		red_candles_1H['extension'] = red_candles_1H['extension'].replace(-np.inf, -1)

		extension_feature_1H = pd.DataFrame(index = dataset_1H.index)
		extension_feature_1H['extension_green'] = green_candles_1H['extension']
		extension_feature_1H['extension_red'] = red_candles_1H['extension']
		#///////////////////////////////////////////////

		#4H *******************:
		green_candles_4H = pd.DataFrame(index = dataset_4H.index)
		green_candles_4H['close'] = dataset_4H['close'][color_pattern_4H['color_candle'] == 1]
		green_candles_4H['volume'] = dataset_4H['volume'][color_pattern_4H['color_candle'] == 1]

		green_candles_4H['index'] = green_candles_4H.index

		real_dataset_4H = green_candles_4H.dropna().reset_index()
		shifted_dataset_4H = green_candles_4H.dropna().shift(1).fillna(0).reset_index()

		extension_prices_4H = (real_dataset_4H['close'] - shifted_dataset_4H['close'])/((real_dataset_4H['close'] + shifted_dataset_4H['close'])/2)
		extension_volumes_4H = (real_dataset_4H['volume'] - shifted_dataset_4H['volume'])/((real_dataset_4H['volume'] + shifted_dataset_4H['volume'])/2)
		
		real_dataset_4H['extension'] = extension_volumes_4H/extension_prices_4H
		real_dataset_4H.index = real_dataset_4H['index']
		green_candles_4H['extension'] = real_dataset_4H['extension']
		green_candles_4H['extension'] = green_candles_4H['extension'].fillna(0).replace(np.inf, 1)
		green_candles_4H['extension'] = green_candles_4H['extension'].replace(-np.inf, -1)

		red_candles_4H = pd.DataFrame(index = dataset_4H.index)
		red_candles_4H['close'] = dataset_4H['close'][color_pattern_4H['color_candle'] == 0]
		red_candles_4H['volume'] = dataset_4H['volume'][color_pattern_4H['color_candle'] == 0]

		red_candles_4H['index'] = red_candles_4H.index

		real_dataset_4H = red_candles_4H.dropna().reset_index()
		shifted_dataset_4H = red_candles_4H.dropna().shift(1).fillna(0).reset_index()

		extension_prices_4H = (real_dataset_4H['close'] - shifted_dataset_4H['close'])/((real_dataset_4H['close'] + shifted_dataset_4H['close'])/2)
		extension_volumes_4H = (real_dataset_4H['volume'] - shifted_dataset_4H['volume'])/((real_dataset_4H['volume'] + shifted_dataset_4H['volume'])/2)
		
		real_dataset_4H['extension'] = extension_volumes_4H/extension_prices_4H
		real_dataset_4H.index = real_dataset_4H['index']
		red_candles_4H['extension'] = real_dataset_4H['extension']
		red_candles_4H['extension'] = red_candles_4H['extension'].fillna(0).replace(np.inf, 1)
		red_candles_4H['extension'] = red_candles_4H['extension'].replace(-np.inf, -1)

		extension_feature_4H = pd.DataFrame(index = dataset_4H.index)
		extension_feature_4H['extension_green'] = green_candles_4H['extension']
		extension_feature_4H['extension_red'] = red_candles_4H['extension']
		#///////////////////////////////////////////////

		#1D *******************:
		green_candles_1D = pd.DataFrame(index = dataset_1D.index)
		green_candles_1D['close'] = dataset_1D['close'][color_pattern_1D['color_candle'] == 1]
		green_candles_1D['volume'] = dataset_1D['volume'][color_pattern_1D['color_candle'] == 1]

		green_candles_1D['index'] = green_candles_1D.index

		real_dataset_1D = green_candles_1D.dropna().reset_index()
		shifted_dataset_1D = green_candles_1D.dropna().shift(1).fillna(0).reset_index()

		extension_prices_1D = (real_dataset_1D['close'] - shifted_dataset_1D['close'])/((real_dataset_1D['close'] + shifted_dataset_1D['close'])/2)
		extension_volumes_1D = (real_dataset_1D['volume'] - shifted_dataset_1D['volume'])/((real_dataset_1D['volume'] + shifted_dataset_1D['volume'])/2)
		
		real_dataset_1D['extension'] = extension_volumes_1D/extension_prices_1D
		real_dataset_1D.index = real_dataset_1D['index']
		green_candles_1D['extension'] = real_dataset_1D['extension']
		green_candles_1D['extension'] = green_candles_1D['extension'].fillna(0).replace(np.inf, 1)
		green_candles_1D['extension'] = green_candles_1D['extension'].replace(-np.inf, -1)

		red_candles_1D = pd.DataFrame(index = dataset_1D.index)
		red_candles_1D['close'] = dataset_1D['close'][color_pattern_1D['color_candle'] == 0]
		red_candles_1D['volume'] = dataset_1D['volume'][color_pattern_1D['color_candle'] == 0]

		red_candles_1D['index'] = red_candles_1D.index

		real_dataset_1D = red_candles_1D.dropna().reset_index()
		shifted_dataset_1D = red_candles_1D.dropna().shift(1).fillna(0).reset_index()

		extension_prices_1D = (real_dataset_1D['close'] - shifted_dataset_1D['close'])/((real_dataset_1D['close'] + shifted_dataset_1D['close'])/2)
		extension_volumes_1D = (real_dataset_1D['volume'] - shifted_dataset_1D['volume'])/((real_dataset_1D['volume'] + shifted_dataset_1D['volume'])/2)
		
		real_dataset_1D['extension'] = extension_volumes_1D/extension_prices_1D
		real_dataset_1D.index = real_dataset_1D['index']
		red_candles_1D['extension'] = real_dataset_1D['extension']
		red_candles_1D['extension'] = red_candles_1D['extension'].fillna(0).replace(np.inf, 1)
		red_candles_1D['extension'] = red_candles_1D['extension'].replace(-np.inf, -1)

		extension_feature_1D = pd.DataFrame(index = dataset_1D.index)
		extension_feature_1D['extension_green'] = green_candles_1D['extension']
		extension_feature_1D['extension_red'] = red_candles_1D['extension']
		#///////////////////////////////////////////////

		return extension_feature_5M, extension_feature_15M, extension_feature_1H, extension_feature_4H, extension_feature_1D

	def Power(
				self, 
				dataset_5M, 
				dataset_15M, 
				dataset_1H, 
				dataset_4H, 
				dataset_1D, 
				color_pattern_5M, 
				color_pattern_15M, 
				color_pattern_1H,
				color_pattern_4H,
				color_pattern_1D
				):

		#5M *******************:
		green_candles_5M = pd.DataFrame(index = dataset_5M.index)
		green_candles_5M = dataset_5M[color_pattern_5M['color_candle'] == 1]

		close_open_diff = abs(green_candles_5M['close'] - green_candles_5M['open'])
		high_low_close_open_diff = abs(green_candles_5M['high'] - green_candles_5M['low'] - close_open_diff)

		power_feature_5M = pd.DataFrame(index = dataset_5M.index)
		power_feature_5M['power_green'] = close_open_diff/high_low_close_open_diff
		power_feature_5M['power_green'] = power_feature_5M['power_green'].fillna(0).replace(np.inf, 1)
		power_feature_5M['power_green'] = power_feature_5M['power_green'].replace(-np.inf, 0)

		red_candles_5M = pd.DataFrame(index = dataset_5M.index)
		red_candles_5M = dataset_5M[color_pattern_5M['color_candle'] == 0]

		close_open_diff = abs(red_candles_5M['close'] - red_candles_5M['open'])
		high_low_close_open_diff = abs(red_candles_5M['high'] - red_candles_5M['low'] - close_open_diff)

		power_feature_5M['power_red'] = close_open_diff/high_low_close_open_diff
		power_feature_5M['power_red'] = power_feature_5M['power_red'].fillna(0).replace(np.inf, 1)
		power_feature_5M['power_red'] = power_feature_5M['power_red'].replace(-np.inf, 0)
		#////////////////////////////////////////////////////////////


		#15M *******************:
		green_candles_15M = pd.DataFrame(index = dataset_15M.index)
		green_candles_15M = dataset_15M[color_pattern_15M['color_candle'] == 1]

		close_open_diff = abs(green_candles_15M['close'] - green_candles_15M['open'])
		high_low_close_open_diff = abs(green_candles_15M['high'] - green_candles_15M['low'] - close_open_diff)

		power_feature_15M = pd.DataFrame(index = dataset_15M.index)
		power_feature_15M['power_green'] = close_open_diff/high_low_close_open_diff
		power_feature_15M['power_green'] = power_feature_15M['power_green'].fillna(0).replace(np.inf, 1)
		power_feature_15M['power_green'] = power_feature_15M['power_green'].replace(-np.inf, 0)

		red_candles_15M = pd.DataFrame(index = dataset_15M.index)
		red_candles_15M = dataset_15M[color_pattern_15M['color_candle'] == 0]

		close_open_diff = abs(red_candles_15M['close'] - red_candles_15M['open'])
		high_low_close_open_diff = abs(red_candles_15M['high'] - red_candles_15M['low'] - close_open_diff)

		power_feature_15M['power_red'] = close_open_diff/high_low_close_open_diff
		power_feature_15M['power_red'] = power_feature_15M['power_red'].fillna(0).replace(np.inf, 1)
		power_feature_15M['power_red'] = power_feature_15M['power_red'].replace(-np.inf, 0)
		#////////////////////////////////////////////////////////////


		#1H *******************:
		green_candles_1H = pd.DataFrame(index = dataset_1H.index)
		green_candles_1H = dataset_1H[color_pattern_1H['color_candle'] == 1]

		close_open_diff = abs(green_candles_1H['close'] - green_candles_1H['open'])
		high_low_close_open_diff = abs(green_candles_1H['high'] - green_candles_1H['low'] - close_open_diff)

		power_feature_1H = pd.DataFrame(index = dataset_1H.index)
		power_feature_1H['power_green'] = close_open_diff/high_low_close_open_diff
		power_feature_1H['power_green'] = power_feature_1H['power_green'].fillna(0).replace(np.inf, 1)
		power_feature_1H['power_green'] = power_feature_1H['power_green'].replace(-np.inf, 0)

		red_candles_1H = pd.DataFrame(index = dataset_1H.index)
		red_candles_1H = dataset_1H[color_pattern_1H['color_candle'] == 0]

		close_open_diff = abs(red_candles_1H['close'] - red_candles_1H['open'])
		high_low_close_open_diff = abs(red_candles_1H['high'] - red_candles_1H['low'] - close_open_diff)

		power_feature_1H['power_red'] = close_open_diff/high_low_close_open_diff
		power_feature_1H['power_red'] = power_feature_1H['power_red'].fillna(0).replace(np.inf, 1)
		power_feature_1H['power_red'] = power_feature_1H['power_red'].replace(-np.inf, 0)
		#////////////////////////////////////////////////////////////

		#4H *******************:
		green_candles_4H = pd.DataFrame(index = dataset_4H.index)
		green_candles_4H = dataset_4H[color_pattern_4H['color_candle'] == 1]

		close_open_diff = abs(green_candles_4H['close'] - green_candles_4H['open'])
		high_low_close_open_diff = abs(green_candles_4H['high'] - green_candles_4H['low'] - close_open_diff)

		power_feature_4H = pd.DataFrame(index = dataset_4H.index)
		power_feature_4H['power_green'] = close_open_diff/high_low_close_open_diff
		power_feature_4H['power_green'] = power_feature_4H['power_green'].fillna(0).replace(np.inf, 1)
		power_feature_4H['power_green'] = power_feature_4H['power_green'].replace(-np.inf, 0)

		red_candles_4H = pd.DataFrame(index = dataset_4H.index)
		red_candles_4H = dataset_4H[color_pattern_4H['color_candle'] == 0]

		close_open_diff = abs(red_candles_4H['close'] - red_candles_4H['open'])
		high_low_close_open_diff = abs(red_candles_4H['high'] - red_candles_4H['low'] - close_open_diff)

		power_feature_4H['power_red'] = close_open_diff/high_low_close_open_diff
		power_feature_4H['power_red'] = power_feature_4H['power_red'].fillna(0).replace(np.inf, 1)
		power_feature_4H['power_red'] = power_feature_4H['power_red'].replace(-np.inf, 0)
		#////////////////////////////////////////////////////////////

		#1D *******************:
		green_candles_1D = pd.DataFrame(index = dataset_1D.index)
		green_candles_1D = dataset_1D[color_pattern_1D['color_candle'] == 1]

		close_open_diff = abs(green_candles_1D['close'] - green_candles_1D['open'])
		high_low_close_open_diff = abs(green_candles_1D['high'] - green_candles_1D['low'] - close_open_diff)

		power_feature_1D = pd.DataFrame(index = dataset_1D.index)
		power_feature_1D['power_green'] = close_open_diff/high_low_close_open_diff
		power_feature_1D['power_green'] = power_feature_1D['power_green'].fillna(0).replace(np.inf, 1)
		power_feature_1D['power_green'] = power_feature_1D['power_green'].replace(-np.inf, 0)

		red_candles_1D = pd.DataFrame(index = dataset_1D.index)
		red_candles_1D = dataset_1D[color_pattern_1D['color_candle'] == 0]

		close_open_diff = abs(red_candles_1D['close'] - red_candles_1D['open'])
		high_low_close_open_diff = abs(red_candles_1D['high'] - red_candles_1D['low'] - close_open_diff)

		power_feature_1D['power_red'] = close_open_diff/high_low_close_open_diff
		power_feature_1D['power_red'] = power_feature_1D['power_red'].fillna(0).replace(np.inf, 1)
		power_feature_1D['power_red'] = power_feature_1D['power_red'].replace(-np.inf, 0)
		#////////////////////////////////////////////////////////////

		return power_feature_5M, power_feature_15M, power_feature_1H, power_feature_4H, power_feature_1D

	def Run(
			self, 
			dataset_5M, 
			dataset_15M, 
			dataset_1H,
			dataset_4H,
			dataset_1D
			):

		patterns = Patterns()
		color_pattern_5M, color_pattern_15M, color_pattern_1H, color_pattern_4H, color_pattern_1D = patterns.ColorCandle(
																														dataset_5M = dataset_5M,
																														dataset_15M = dataset_15M,
																														dataset_1H = dataset_1H,
																														dataset_4H = dataset_4H,
																														dataset_1D = dataset_1D
																														)

		price_feature_5M, price_feature_15M, price_feature_1H, price_feature_4H, price_feature_1D = self.Prices(
																												dataset_5M = dataset_5M,
																												dataset_15M = dataset_15M,
																												dataset_1H = dataset_1H,
																												dataset_4H = dataset_4H,
																												dataset_1D = dataset_1D,
																												color_pattern_5M = color_pattern_5M,
																												color_pattern_15M = color_pattern_15M,
																												color_pattern_1H = color_pattern_1H,
																												color_pattern_4H = color_pattern_4H,
																												color_pattern_1D = color_pattern_1D
																												)

		extension_feature_5M, extension_feature_15M, extension_feature_1H, extension_feature_4H, extension_feature_1D = self.Extension(
																																		dataset_5M = dataset_5M,
																																		dataset_15M = dataset_15M,
																																		dataset_1H = dataset_1H,
																																		dataset_4H = dataset_4H,
																																		dataset_1D = dataset_1D,
																																		color_pattern_5M = color_pattern_5M,
																																		color_pattern_15M = color_pattern_15M,
																																		color_pattern_1H = color_pattern_1H,
																																		color_pattern_4H = color_pattern_4H,
																																		color_pattern_1D = color_pattern_1D
																																		)

		power_feature_5M, power_feature_15M, power_feature_1H, power_feature_4H, power_feature_1D = self.Power(
																												dataset_5M = dataset_5M,
																												dataset_15M = dataset_15M,
																												dataset_1H = dataset_1H,
																												dataset_4H = dataset_4H,
																												dataset_1D = dataset_1D,
																												color_pattern_5M = color_pattern_5M,
																												color_pattern_15M = color_pattern_15M,
																												color_pattern_1H = color_pattern_1H,
																												color_pattern_4H = color_pattern_4H,
																												color_pattern_1D = color_pattern_1D
																												)

		balance_feature_5M = pd.DataFrame(index = dataset_5M.index)
		balance_feature_5M = balance_feature_5M.join(price_feature_5M, how = 'right')
		balance_feature_5M = balance_feature_5M.join(extension_feature_5M, how = 'right')
		balance_feature_5M = balance_feature_5M.join(power_feature_5M, how = 'right')

		balance_feature_15M = pd.DataFrame(index = dataset_15M.index)
		balance_feature_15M = balance_feature_15M.join(price_feature_15M, how = 'right')
		balance_feature_15M = balance_feature_15M.join(extension_feature_15M, how = 'right')
		balance_feature_15M = balance_feature_15M.join(power_feature_15M, how = 'right')

		balance_feature_1H = pd.DataFrame(index = dataset_1H.index)
		balance_feature_1H = balance_feature_1H.join(price_feature_1H, how = 'right')
		balance_feature_1H = balance_feature_1H.join(extension_feature_1H, how = 'right')
		balance_feature_1H = balance_feature_1H.join(power_feature_1H, how = 'right')

		balance_feature_4H = pd.DataFrame(index = dataset_4H.index)
		balance_feature_4H = balance_feature_4H.join(price_feature_4H, how = 'right')
		balance_feature_4H = balance_feature_4H.join(extension_feature_4H, how = 'right')
		balance_feature_4H = balance_feature_4H.join(power_feature_4H, how = 'right')

		balance_feature_1D = pd.DataFrame(index = dataset_1D.index)
		balance_feature_1D = balance_feature_1D.join(price_feature_1D, how = 'right')
		balance_feature_1D = balance_feature_1D.join(extension_feature_1D, how = 'right')
		balance_feature_1D = balance_feature_1D.join(power_feature_1D, how = 'right')

		return balance_feature_5M, balance_feature_15M, balance_feature_1H, balance_feature_4H, balance_feature_1D

	@stTime
	def Get(
			self, 
			dataset_5M, 
			dataset_15M, 
			dataset_1H,
			dataset_4H,
			dataset_1D
			):

		return self.Run(
						dataset_5M = dataset_5M,
						dataset_15M = dataset_15M,
						dataset_1H = dataset_1H,
						dataset_4H = dataset_4H,
						dataset_1D = dataset_1D
						)
		