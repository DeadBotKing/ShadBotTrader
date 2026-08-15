from .DatasetIO import DatasetIO

class Deleter:
	def __call__(self):
		datasetio = DatasetIO()

		#Main Feature:
		datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '5M')
		datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '15M')
		datasetio.Delete(type_feature = 'main_features', symbol = symbol, name = '1H')
		#///////////////////////

		#PCAMI Feature:
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '5M')
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '15M')
		datasetio.Delete(type_feature = 'pca', symbol = symbol, name = '1H')
		#///////////////////////

		#Lag Features:
		datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '5M')
		datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '15M') 
		datasetio.Delete(type_feature = 'lags', symbol = symbol, name = '1H')
		#///////////////////////

		#Patterns:
		datasetio.Delete(type_feature = 'pattern', name = '5M', symbol = symbol)
		datasetio.Delete(type_feature = 'pattern', name = '15M', symbol = symbol)
		datasetio.Delete(type_feature = 'pattern', name = '1H', symbol = symbol)
		#///////////////////////

		#Fourier Features:
		datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '5M')
		datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '15M')
		datasetio.Delete(symbol = symbol, type_feature = 'fourier', name = '1H')
		#///////////////////////

		#Feature Engineering:
		datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '5M')
		datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '15M')
		datasetio.Delete(symbol = symbol, type_feature = 'feature_engineering_scale', name = '1H')
		#///////////////////////
