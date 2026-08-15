from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.MainFeatures import MainFeatures
import pandas as pd
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


# print(
# 		main_features.AlphaFactorNoiseFilter(
# 											dataset_5M = dataset_5M,
# 											dataset_15M = dataset_15M,
# 											dataset_1H = dataset_1H
# 											)
# 		)

# with pd.option_context('display.max_rows', None, 'display.max_columns', None):
# print(	
# 		main_features.AlphaFactorOsilators(
# 											dataset_5M = dataset_5M,
# 											dataset_15M = dataset_15M,
# 											dataset_1H = dataset_1H,
# 											symbol = 'XAUUSD_i'
# 											)
# 		)

# print(	
# 		main_features.AlphaFactorBBAND(
# 										dataset_5M = dataset_5M,
# 										dataset_15M = dataset_15M,
# 										dataset_1H = dataset_1H
# 										)
# 		)

# print(	
# 		main_features.AlphaFactorATR(
# 										dataset_5M = dataset_5M,
# 										dataset_15M = dataset_15M,
# 										dataset_1H = dataset_1H
# 										)
# 		)

# print(	
# 		main_features.AlphaFactorSMA(
# 										dataset_5M = dataset_5M,
# 										dataset_15M = dataset_15M,
# 										dataset_1H = dataset_1H
# 										)
# 		)

# print(	
# 		main_features.AlphaFactorEMA(
# 										dataset_5M = dataset_5M,
# 										dataset_15M = dataset_15M,
# 										dataset_1H = dataset_1H
# 										)
# 		)

	
# ichi_5m, ichi_15m , ichi_1h = main_features.AlphaFactorIchimokou(
# 											dataset_5M = dataset_5M,
# 											dataset_15M = dataset_15M,
# 											dataset_1H = dataset_1H
# 											)
# with pd.option_context('display.max_rows', None, 'display.max_columns', None):
main_features_5M, main_features_15M, main_features_1H = main_features.Get(
																		dataset_5M = dataset_5M,
																		dataset_15M = dataset_15M,
																		dataset_1H = dataset_1H,
																		symbol = 'XAUUSD_i',
																		mode = 'Run'
																		)

print(main_features_5M, main_features_15M, main_features_1H)
