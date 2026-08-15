from pathlib import Path, PurePosixPath
import os
import sys


if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'



class Config:

	def __init__(cls):
		
		cls.cfg = dict({

						#************** Feature Engineering:
						'path_feature_engineering_scale': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'FeatureEngineeringScaled' + path_slash),
						'path_feature_engineering': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'FeatureEngineering' + path_slash),

						'path_frequency': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Frequencies' + path_slash),

						'path_fourier': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Fouriers' + path_slash),
						'path_fourier_minmaxscaler': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Fouriers' + path_slash + 'MinMaxScaler' + path_slash),

						'path_pattern': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Patterns' + path_slash),
						'path_pattern_minmaxscaler': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Patterns' + path_slash + 'MinMaxScaler' + path_slash),

						'path_main_features': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'MainFeatures' + path_slash),
						'path_main_features_minmaxscaler': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'MainFeatures' + path_slash + 'MinMaxScaler' + path_slash),

						'path_lags': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Lag' + path_slash),
						'path_lags_minmaxscaler': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Lag' + path_slash + 'MinMaxScaler' + path_slash),

						'path_lags_number': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'LagNumber' + path_slash),

						'path_main_minmaxscaler': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'Main' + path_slash + 'MinMaxScaler' + path_slash),

						'path_pca': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'PCA' + path_slash),
						'path_pca_names': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'PCA' + path_slash + 'Names' + path_slash),
						'path_pca_minmaxscaler': os.path.join(Path(__file__).parent , 'Dataset' + path_slash + 'PCA' + path_slash + 'MinMaxScaler' + path_slash),
						#/////////////////////////////

						'show_bar': False,

						})