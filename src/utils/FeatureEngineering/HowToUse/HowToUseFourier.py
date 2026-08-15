from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.FourierFeatures import FourierFeatures
import pandas as pd
import sys
# import seaborn as sns
import warnings as warnings
warnings.filterwarnings("ignore")

loging = getdata()

dataset_5M = pd.DataFrame()
dataset_15M = pd.DataFrame()
dataset_1H = pd.DataFrame()
dataset_4H = pd.DataFrame()
dataset_1D = pd.DataFrame()

dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D = loging.readall(
																				symbol = 'XAUUSD_i', 
																				number_5M = 0, 
																				number_15M = 0, 
																				number_1H = 0,
																				number_4H = 0,
																				number_1D = 'all'
																				)

dataset_5M = dataset_5M['XAUUSD_i']
dataset_15M = dataset_15M['XAUUSD_i']
dataset_1H = dataset_1H['XAUUSD_i']
dataset_4H = dataset_4H['XAUUSD_i']
dataset_1D = dataset_1D['XAUUSD_i']

fourier_features = FourierFeatures()

fourier_features.flag_fourier_5M = False
fourier_features.flag_fourier_15M = False
fourier_features.flag_fourier_1H = False
fourier_features.flag_fourier_4H = False
fourier_features.flag_fourier_1D = True

fourier_5M, fourier_15M, fourier_1H, fourier_4H, fourier_1D	= fourier_features.Get(
																					dataset_5M = dataset_5M, 
																					dataset_15M = dataset_15M, 
																					dataset_1H = dataset_1H,
																					dataset_4H = dataset_4H,
																					dataset_1D = dataset_1D, 
																					symbol = 'XAUUSD_i', 
																					mode = 'Run', 
																					number_frequencies = 2
																					)

print(fourier_1D)

import matplotlib.pyplot as plt

plt.plot((((dataset_1D['open'] - dataset_1D['open'].min()) / (dataset_1D['open'].max() - dataset_1D['open'].min())) * 2) - 1, c = 'black')
plt.plot(fourier_1D['cos_1_open'])
plt.plot(fourier_1D['sin_1_open'])
plt.show()