from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.FeatureEngineering import FeatureEngineering
import warnings as warnings
import pandas as pd
warnings.filterwarnings("ignore")

loging = getdata()

dataset_5M = pd.DataFrame()
dataset_15M = pd.DataFrame()
dataset_1H = pd.DataFrame()

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = 'XAUUSD_i', number_5M = 2000, number_15M = 2000, number_1H = 2000)

dataset_5M = dataset_5M['XAUUSD_i']
dataset_15M = dataset_15M['XAUUSD_i']
dataset_1H = dataset_1H['XAUUSD_i']


feature_engineering = FeatureEngineering()

feature_engineering_5M, feature_engineering_15M, feature_engineering_1H = feature_engineering(
																								dataset_5M = dataset_5M, 
																								dataset_15M = dataset_15M, 
																								dataset_1H = dataset_1H, 
																								symbol = 'XAUUSD_i', 
																								mode = None, 
																								scale = False
																								)

# print(feature_engineering_5M, feature_engineering_15M, feature_engineering_1H)
# print(feature_engineering_5M.columns, feature_engineering_15M.columns, feature_engineering_1H.columns)