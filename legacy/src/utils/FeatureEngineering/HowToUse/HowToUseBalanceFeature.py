from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.BalanceFeature import BalanceFeature
from src.utils.FeatureEngineering.Patterns import Patterns
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

balance_feature = BalanceFeature()

# patterns = Patterns()
# color_pattern_5M, color_pattern_15M, color_pattern_1H = patterns.ColorCandle(
# 																			dataset_5M = dataset_5M,
# 																			dataset_15M = dataset_15M,
# 																			dataset_1H = dataset_1H
# 																			)

# price_feature_5M, price_feature_15M, price_feature_1H = balance_feature.Prices(
# 																				dataset_5M = dataset_5M,
# 																				dataset_15M = dataset_15M,
# 																				dataset_1H = dataset_1H,
# 																				color_pattern_5M = color_pattern_5M,
# 																				color_pattern_15M = color_pattern_15M,
# 																				color_pattern_1H = color_pattern_1H
# 																				)

# extension_feature_5M, extension_feature_15M, extension_feature_1H = balance_feature.Extension(
# 																							dataset_5M = dataset_5M,
# 																							dataset_15M = dataset_15M,
# 																							dataset_1H = dataset_1H,
# 																							color_pattern_5M = color_pattern_5M,
# 																							color_pattern_15M = color_pattern_15M,
# 																							color_pattern_1H = color_pattern_1H
# 																							)

# power_feature_5M, power_feature_15M, power_feature_1H = balance_feature.Power(
# 																				dataset_5M = dataset_5M,
# 																				dataset_15M = dataset_15M,
# 																				dataset_1H = dataset_1H,
# 																				color_pattern_5M = color_pattern_5M,
# 																				color_pattern_15M = color_pattern_15M,
# 																				color_pattern_1H = color_pattern_1H
# 																				)

balance_feature_5M, balance_feature_15M, balance_feature_1H = balance_feature.Get(
																				dataset_5M = dataset_5M,
																				dataset_15M = dataset_15M,
																				dataset_1H = dataset_1H
																				)

import matplotlib.pyplot as plt
from mlxtend.preprocessing import minmax_scaling

scale_green_5M = minmax_scaling(balance_feature_5M, columns = ['extension_green'])
scale_red_5M = minmax_scaling(balance_feature_5M, columns = ['extension_red'])

power_feature_5M = minmax_scaling(balance_feature_5M, columns = ['power_green', 'power_red'])

scale_green_15M = minmax_scaling(balance_feature_15M, columns = ['extension_green'])
scale_red_15M = minmax_scaling(balance_feature_15M, columns = ['extension_red'])

scale_green_1H = minmax_scaling(balance_feature_1H, columns = ['extension_green'])
scale_red_1H = minmax_scaling(balance_feature_1H, columns = ['extension_red'])

figure, ([ax00, ax10, ax20], [ax01, ax11, ax21], [ax02, ax12, ax22], [ax03, ax13, ax23]) = plt.subplots(nrows = 4, ncols = 3)

ax00.set_title(label = '5M')
ax00.plot(dataset_5M['close'])
ax00.plot(balance_feature_5M['price_balance'], c = 'r')
ax01.plot(scale_green_5M, c = 'g')
ax01.plot(scale_red_5M, c = 'r')
ax02.plot(balance_feature_5M['diff_price_balance'])
ax03.plot(balance_feature_5M['power_green'], color = 'g')
ax03.plot(balance_feature_5M['power_red'], color = 'r')

ax10.set_title(label = '15M')
ax10.plot(dataset_15M['close'])
ax10.plot(balance_feature_15M['price_balance'], c = 'r')
ax11.plot(scale_green_15M, c = 'g')
ax11.plot(scale_red_15M, c = 'r')
ax12.plot(balance_feature_15M['diff_price_balance'])
ax13.plot(balance_feature_15M['power_green'], color = 'g')
ax13.plot(balance_feature_15M['power_red'], color = 'r')

ax20.set_title(label = '1H')
ax20.plot(dataset_1H['close'])
ax20.plot(balance_feature_1H['price_balance'], c = 'r')
ax21.plot(scale_green_1H, c = 'g')
ax21.plot(scale_red_1H, c = 'r')
ax22.plot(balance_feature_1H['diff_price_balance'])
ax23.plot(balance_feature_1H['power_green'], color = 'g')
ax23.plot(balance_feature_1H['power_red'], color = 'r')

plt.show()
# with pd.option_context('display.max_rows', None, 'display.max_columns', None):
