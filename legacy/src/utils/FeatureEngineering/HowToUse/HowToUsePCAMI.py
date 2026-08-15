from src.utils.FeatureEngineering.PCAMI import PCAMI
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.MainFeatures import MainFeatures
import pandas as pd
import numpy as np
import warnings as warnings
warnings.filterwarnings("ignore")

loging = getdata()

dataset_5M = pd.DataFrame()
dataset_15M = pd.DataFrame()
dataset_1H = pd.DataFrame()

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = 'XAUUSD_i', number_5M = 'all', number_15M = 'all', number_1H = 'all')

dataset_5M = dataset_5M['XAUUSD_i']
dataset_15M = dataset_15M['XAUUSD_i']
dataset_1H = dataset_1H['XAUUSD_i']

main_features = MainFeatures()
main_features_5M, main_features_15M, main_features_1H = main_features.Get(
																		dataset_5M = dataset_5M,
																		dataset_15M = dataset_15M,
																		dataset_1H = dataset_1H,
																		symbol = 'XAUUSD_i',
																		mode = None
																		)

pca_dataset_5M = dataset_5M.copy(deep = True).drop(columns = ['time', 'XAUUSD_i'])
pca_dataset_5M = pca_dataset_5M.join(main_features_5M, how = 'right')
pca_dataset_5M = pca_dataset_5M.fillna(0)

pca_dataset_15M = dataset_15M.copy(deep = True).drop(columns = ['time', 'XAUUSD_i'])
pca_dataset_15M = pca_dataset_15M.join(main_features_15M, how = 'right')
pca_dataset_15M = pca_dataset_15M.fillna(0)

pca_dataset_1H = dataset_1H.copy(deep = True).drop(columns = ['time', 'XAUUSD_i'])
pca_dataset_1H = pca_dataset_1H.join(main_features_1H, how = 'right')
pca_dataset_1H = pca_dataset_1H.fillna(0)


pca_mi = PCAMI()

# data_pca, data_scale = pca_mi.PCA(dataset = pca_dataset)
# mi_dataset = pd.DataFrame()

# for clm in pca_dataset.columns:

# 	mi_dataset = mi_dataset.append(pca_mi.MakeMIScores(input_x = data_pca, target = data_scale[clm]))

# mi_dataset = mi_dataset.sort_values(by = ['pca'], ascending = False)
# mi_dataset['names'] = mi_dataset.index
# mi_dataset = mi_dataset.drop_duplicates(subset = ['names'], keep = 'first')
# mi_dataset = mi_dataset[mi_dataset['pca'] >= 0.2]

# new_feature_names = pca_mi.NewFeatureFinder(dataset = pca_dataset)

pca_feature_5M, pca_feature_15M, pca_feature_1H = pca_mi.Get(
															dataset_5M = pca_dataset_5M, 
															dataset_15M = pca_dataset_15M, 
															dataset_1H = pca_dataset_1H, 
															symbol = 'XAUUSD_i', 
															mode = None
															)

print(pca_feature_5M)