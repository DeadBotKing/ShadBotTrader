from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.LagFeatures import LagFeatures
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

lag_feature = LagFeatures()

# LagedData_5M, LagedData_15M, LagedData_1H = lag_feature.LagCreation(
# 																	dataset_5M = dataset_5M,
# 																	dataset_15M = dataset_15M,
# 																	dataset_1H = dataset_1H,
# 																	symbol = 'XAUUSD_i',
# 																	number_lags = 1,
# 																	mode = 'online'
# 																	)
# print(LagedData_5M.columns, LagedData_15M.columns, LagedData_1H.columns)

LagedData_5M, LagedData_15M, LagedData_1H = lag_feature.Get(
															dataset_5M = dataset_5M,
															dataset_15M = dataset_15M,
															dataset_1H = dataset_1H,
															symbol = 'XAUUSD_i',
															number_lags = 1,
															mode = 'Run'
															)
print(LagedData_5M, LagedData_15M, LagedData_1H)

import matplotlib.pyplot as plt

figure, (ax0, ax1, ax2) = plt.subplots(3)
ax0.plot(LagedData_5M['open_return_10_1'])
ax1.plot(LagedData_15M['open_return_60_1'])
ax2.plot(LagedData_1H['open_return_17_1'])

plt.show()