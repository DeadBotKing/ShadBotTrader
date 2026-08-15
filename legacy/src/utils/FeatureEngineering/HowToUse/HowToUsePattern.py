from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
import seaborn as sns
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

from src.utils.FeatureEngineering.Patterns import Patterns

patterns = Patterns()
# daily_pattern_5M, daily_pattern_15M, daily_pattern_1H = patterns.ColorCandle(
# 																		dataset_5M = dataset_5M,
# 																		dataset_15M = dataset_15M,
# 																		dataset_1H = dataset_1H
# 																		)

# daily_pattern_5M, daily_pattern_15M, daily_pattern_1H = patterns.DailyPatterns(
# 																				dataset_5M = dataset_5M,
# 																				dataset_15M = dataset_15M,
# 																				dataset_1H = dataset_1H
# 																				)

# daily_pattern_5M, daily_pattern_15M, daily_pattern_1H = patterns.CandlePatterns(
# 																				dataset_5M = dataset_5M,
# 																				dataset_15M = dataset_15M,
# 																				dataset_1H = dataset_1H
# 																				)

# daily_pattern_5M, daily_pattern_15M, daily_pattern_1H = patterns.CandleNumberPatterns(
# 																					dataset_5M = dataset_5M,
# 																					dataset_15M = dataset_15M,
# 																					dataset_1H = dataset_1H
# 																					)

# daily_pattern_5M, daily_pattern_15M, daily_pattern_1H = patterns.DivergencePatterns(
# 																					dataset_5M = dataset_5M,
# 																					dataset_15M = dataset_15M,
# 																					dataset_1H = dataset_1H,
# 																					symbol = 'XAUUSD_i'
# 																					)
import matplotlib.pyplot as plt
print('start ...')
# daily_pattern_5M = patterns.ZigZagPatterns(
# 											dataset_5M = dataset_5M,
# 											percent_zigzag_finder = 0.02,
# 											profit = 0.6,
# 											symbol = 'XAUUSD_i'
# 											)

image_dataset_preparer.percent_zigzag_finder = 5
image_dataset_preparer.profit = 10

zigzag_patterns = patterns.Get(
								mode = 'Run', 
								dataset_5M = dataset_5M, 
								dataset_15M = dataset_15M, 
								dataset_1H = dataset_1H, 
								symbol = 'XAUUSD_i',
								pattern_name = 'zigzag'
								)

print(zigzag_patterns)

# patterns_5M, patterns_15M, patterns_1H = patterns.Get(
# 													mode = None, 
# 													dataset_5M = dataset_5M, 
# 													dataset_15M = dataset_15M, 
# 													dataset_1H = dataset_1H, 
# 													symbol = 'XAUUSD_i'
# 													)


# print('sell = ', len(zigzag_patterns['signal'][zigzag_patterns['signal'] == 'sell']))
# print('buy = ', len(zigzag_patterns['signal'][zigzag_patterns['signal'] == 'buy']))
# print('no_trade = ', len(zigzag_patterns['signal'][zigzag_patterns['signal'] == 'no_trade']))
# plt.show()

# for clm in patterns_5M.columns:
#     if patterns_5M[clm].isnull().any():
#         print('5M = ', patterns_5M[clm])

# for clm in patterns_15M.columns:
#     if patterns_15M[clm].isnull().any():
#         print('15M = ', patterns_15M[clm])

# for clm in patterns_1H.columns:
#     if patterns_1H[clm].isnull().any():
#         print('1H = ', patterns_1H[clm])

# with pd.option_context('display.max_rows', None, 'display.max_columns', None):
# 	print(daily_pattern_5M)
