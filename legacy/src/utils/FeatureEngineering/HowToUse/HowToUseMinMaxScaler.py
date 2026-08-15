from src.utils.FeatureEngineering.MinMaxScaler import MinMaxScaler
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
import pandas as pd
import warnings as warnings
warnings.filterwarnings("ignore")

loging = getdata()

dataset_5M = pd.DataFrame()
dataset_15M = pd.DataFrame()
dataset_1H = pd.DataFrame()

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = 'XAUUSD_i', number_5M = 200, number_15M = 200, number_1H = 200)

dataset_5M = dataset_5M['XAUUSD_i']
dataset_15M = dataset_15M['XAUUSD_i']
dataset_1H = dataset_1H['XAUUSD_i']

minmax_scaler = MinMaxScaler()

scale_main_5M, scale_main_15M, scale__main_1H = minmax_scaler(
															dataset_5M = dataset_5M, 
															dataset_15M = dataset_15M, 
															dataset_1H = dataset_1H, 
															name_feature = 'main', 
															symbol = 'XAUUSD_i'
															)

import matplotlib.pyplot as plt

figure, (ax0, ax1) = plt.subplots(2)
ax0.plot(dataset_5M['close'])
ax1.plot(scale_main_5M['close'])

plt.show()