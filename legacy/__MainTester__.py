from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.FeatureEngineering import FeatureEngineering
from src.utils.DatasetPreparer.Image.ImageDatasetPreparer import ImageDatasetPreparer
from src.utils.MLModelGenerator.Image.Predictor import Predictor
import tensorflow as tf

from src.utils.Tools.DataChanger import DataChanger

import mplfinance as mpf_5M

import matplotlib.pyplot as plt

import pandas as pd
import numpy as np

import shutil

import cv2

import os

symbol = 'XAUUSD_i'
number_data_5M = 'all'
number_data_1H = 'all'
start_point = 6000
coef_money = 20
money = 100
spred = 0.0004
percent = 0
tp_pr_eq = 0
st_pr_eq = 0
plot_signals = True

valid_percent = 0.2

feature_names = []
target_name = 'high'
target_type = 'min'
feature_names_str = 'All_feature_' + target_type

class MinLayer(tf.keras.layers.Layer):

    def __init__(self, shape, batch_size, units, name, **kwargs):
    	super().__init__(name = name)
    	super(MinLayer, self).__init__(**kwargs)

    	self.batch_size = batch_size
    	self.shape = shape
    	self.my_input_shape = [batch_size, self.shape[0], self.shape[1]]
    	self.units = units

    def call(self, inputs):
    	return tf.math.reduce_min(inputs, keepdims = True)

    def get_config(self):
    	config = super().get_config()
    	config.update({
			    		'batch_size': self.batch_size,
			    		'units': self.units,
			    		'shape': self.shape,
		    		})
    	return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)

class MaxLayer(tf.keras.layers.Layer):

    def __init__(self, shape, batch_size, units, name, **kwargs):
    	super().__init__(name = name)
    	super(MaxLayer, self).__init__(**kwargs)

    	self.batch_size = batch_size
    	self.shape = shape
    	self.my_input_shape = [batch_size, self.shape[0], self.shape[1]]
    	self.units = units

    def call(self, inputs):
    	return tf.math.reduce_max(inputs, keepdims = True)

    def get_config(self):
    	config = super().get_config()
    	config.update({
			    		'batch_size': self.batch_size,
			    		'units': self.units,
			    		'shape': self.shape,
		    		})
    	return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)


def window_dataset_predict(
							series, 
							window_size = 200, 
							batch_size = 1,
							shift = 1,
							target_name = 'close',
							feature_names_shouldnt_scale = '',
							price_feature_names_general = [],
							feature_names = []
							):

	dataset = tf.data.Dataset.from_tensor_slices(series)

	dataset = dataset.window(int(window_size ) + 1, shift = shift, drop_remainder=True)

	dataset = dataset.flat_map(lambda window: window.batch(int(window_size ) + 1))

	target = np.where(series.columns == target_name)[0][0]

	feature_names_copy = feature_names.copy()
	feature_names_copy.remove(target_name)
	feature_names_list = []

	for elm in feature_names_copy:
		feature_names_list.append(np.where(series.columns == elm)[0][0])

	feature_names_shouldnt_scale_list = []

	for elm in feature_names_shouldnt_scale:
		
		if elm in series.columns:
			feature_names_shouldnt_scale_list.append(np.where(series.columns == elm)[0][0])
		else:
			feature_names_shouldnt_scale_list = []

	def MinMax(dataset, feature_names_list, feature_names_shouldnt_scale_list, price_feature_names_general):
		
		input_list = []

		for feat in feature_names_list:

			if False:#(feat in feature_names_shouldnt_scale_list ):

				input_list.append(
									tf.cast(
											dataset[ : -1, feat],
											tf.float64
											)
								)
			
			else:
				input_list.append(
								tf.cast(
										(((dataset[ : -1, feat] - tf.math.reduce_min(dataset[ : -1, feat]))/
										(tf.math.reduce_max(dataset[ : -1, feat]) - tf.math.reduce_min(dataset[ : -1, feat]))) * 4) - 2,
										
										tf.float64
										)
								)

		input_list = tf.transpose(input_list)
		input_model = tf.stack(input_list)
		return input_model

	dataset = dataset.map(
							lambda window: (
											MinMax(
													dataset = window, 
													feature_names_list = feature_names_list, 
													feature_names_shouldnt_scale_list = feature_names_shouldnt_scale_list,
													price_feature_names_general = price_feature_names_general
													)
											)
							)

	dataset = dataset.batch(batch_size).prefetch(1)
	return dataset


def BuyChecker(dataset_5M_real, tp, st, candle_index, money, coef_money, spred):

	if (
		dataset_5M_real['high'][candle_index] * (1 + spred) >= tp or
		dataset_5M_real['low'][candle_index] <= st
		):
		flag = 'no_flag'
		tp_pr = 0
		st_pr = 0

		return money, flag, tp_pr, st_pr, candle_index

	if (len(np.where(((dataset_5M_real['high'][(candle_index):-1].values) >= tp))[0]) > 1):
		index_tp =	candle_index + min(
										np.where(
													(
														(dataset_5M_real['high'][(candle_index):-1].values) >= tp
													)
												)[0] 
										)

	elif (len(np.where(((dataset_5M_real['high'][(candle_index):-1].values) >= tp))[0]) == 1):
		index_tp =	candle_index + np.where(
												(
													(dataset_5M_real['high'][(candle_index):-1].values) >= tp
												)
											)[0][0] 

	else:
		index_tp = -1
		tp_pr = 0

	if (len(np.where(((dataset_5M_real['low'][(candle_index):-1].values) <= st))[0]) > 1):
		index_st =	candle_index + min(
									np.where(
												(
													(dataset_5M_real['low'][(candle_index):-1].values) <= st
												)
											)[0]
									)

	elif (len(np.where(((dataset_5M_real['low'][(candle_index):-1].values) <= st))[0]) == 1):
		index_st =	candle_index + np.where(
											(
												(dataset_5M_real['low'][(candle_index):-1].values) <= st
											)
										)[0][0]

	else:
		index_st = -1
		st_pr = 0

	loc_end_5M_price = candle_index
	if (
		index_tp < index_st and
		index_tp != -1
		):

		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_tp]))/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['high'][index_tp] - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		if dataset_5M_real['high'][index_tp] > tp: tp_pr = ((tp - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		flag = 'tp'

	elif (
		index_tp != -1 and
		index_st == -1
		):
		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_tp]))/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['high'][index_tp] - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		if dataset_5M_real['high'][index_tp] > tp: tp_pr = ((tp - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100


		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		flag = 'tp'

	elif (
		index_st < index_tp and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_st])/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_st]) - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100

		if dataset_5M_real['low'][index_st] < st: st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - st)/dataset_5M_real['low'][loc_end_5M_price]) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		flag = 'st'

	elif (
		index_tp == -1 and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_st])/dataset_5M_real['low'][loc_end_5M_price]) * 100
		tp_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_st]) - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100
		
		if dataset_5M_real['low'][index_st] < st: st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - st)/dataset_5M_real['low'][loc_end_5M_price]) * 100

		my_money = money
		coef_money = self.elements['Tester_coef_money']

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		flag = 'st'

	if index_st == index_tp:

		if index_st != -1:
			st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_st])/dataset_5M_real['low'][loc_end_5M_price]) * 100
			tp_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_st]) - dataset_5M_real['high'][loc_end_5M_price]*(1 + spred))/(dataset_5M_real['high'][loc_end_5M_price] * (1 + spred))) * 100
			
			if dataset_5M_real['low'][index_st] < st: st_pr = ((dataset_5M_real['low'][loc_end_5M_price] - st)/dataset_5M_real['low'][loc_end_5M_price]) * 100

			my_money = money
			coef_money = self.elements['Tester_coef_money']

			if my_money >=100:
				lot = int(my_money/100) * coef_money
			else:
				lot = coef_money

			if lot > 2000: lot = 2000

			my_money = my_money - (lot * st_pr)

			money = my_money

			candle_index = index_st

			flag = 'st'

		else:
			flag = 'no_flag'
			tp_pr = 0
			st_pr = 0

	return money, flag, tp_pr, st_pr, candle_index

def SellChecker(dataset_5M_real, tp, st, candle_index, money, coef_money, spred):

	loc_end_5M_price = candle_index

	if (
		dataset_5M_real['high'][loc_end_5M_price] * (1 + spred) >= st or
		dataset_5M_real['low'][loc_end_5M_price] <= tp 
		):

		flag = 'no_flag'
		tp_pr = 0
		st_pr = 0

		return money, flag, tp_pr, st_pr, candle_index

	

	#*************** Finding Take Profit:

	if (len(np.where(((dataset_5M_real['low'][(loc_end_5M_price):-1].values * (1 + spred)) <= tp))[0]) > 1):
		index_tp =	loc_end_5M_price + min(
									np.where(
												(
													(dataset_5M_real['low'][(loc_end_5M_price):-1].values) * (1 + spred) <= tp
												)
											)[0] 
									)

	elif (len(np.where(((dataset_5M_real['low'][(loc_end_5M_price):-1].values * (1 + spred)) <= tp))[0]) == 1):
		index_tp =	loc_end_5M_price + np.where(
											(
												(dataset_5M_real['low'][(loc_end_5M_price):-1].values * (1 + spred)) <= tp
											)
										)[0][0] 

	else:
		index_tp = -1
		tp_pr = 0
	#///////////////////////////////

	#************ Finding Stop Loss:

	if (len(np.where(((dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st))[0]) > 1):
		index_st =	loc_end_5M_price + min(
									np.where(
												(
													(dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st
												)
											)[0]
									)

	elif (len(np.where(((dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st))[0]) == 1):
		index_st =	loc_end_5M_price + np.where(
											(
												(dataset_5M_real['high'][(loc_end_5M_price):-1].values * (1 + spred)) >= st
											)
										)[0][0]

	else:
		index_st = -1
		st_pr = 0

	if (
		index_tp < index_st and
		index_tp != -1
		):

		st_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_tp]) - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_tp])/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		if dataset_5M_real['low'][index_tp] < tp: tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - tp)/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		# print('tp = ', top_prim, ' ', down_prim)

		flag = 'tp'

	elif (
		index_tp != -1 and
		index_st == -1
		):
		st_pr = ((np.max(dataset_5M_real['high'][loc_end_5M_price:index_tp]) - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - dataset_5M_real['low'][index_tp])/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		if dataset_5M_real['low'][index_tp] < tp: tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - tp)/(dataset_5M_real['low'][loc_end_5M_price])) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money + (lot * tp_pr)

		money = my_money

		candle_index = index_tp

		# print('tp = ', top_prim, ' ', down_prim)

		flag = 'tp'

	elif (
		index_st < index_tp and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['high'][index_st] - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_st]))/(dataset_5M_real['low'][loc_end_5M_price])) * 100
		
		if dataset_5M_real['high'][index_st] > st: st_pr = ((st - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		if lot > 2000: lot = 2000

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		# print('st = ', signals['pattern_day'][loc_end_5M], ' ', signals['time_high_front'][loc_end_5M].hour)

		flag = 'st'

	elif (
		index_tp == -1 and
		index_st != -1
		):
		st_pr = ((dataset_5M_real['high'][index_st] - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
		tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_st]))/(dataset_5M_real['low'][loc_end_5M_price])) * 100
		
		if dataset_5M_real['high'][index_st] > st: st_pr = ((st - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100

		my_money = money

		if my_money >=100:
			lot = int(my_money/100) * coef_money
		else:
			lot = coef_money

		my_money = my_money - (lot * st_pr)

		money = my_money

		candle_index = index_st

		# print('st = ', signals['pattern_day'][loc_end_5M], ' ', signals['time_high_front'][loc_end_5M].hour)

		flag = 'st'

	if index_st == index_tp:

		if index_st != -1:
			st_pr = ((dataset_5M_real['high'][index_st] - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
			tp_pr = ((dataset_5M_real['low'][loc_end_5M_price] - np.min(dataset_5M_real['low'][loc_end_5M_price:index_st]))/(dataset_5M_real['low'][loc_end_5M_price])) * 100
			
			if dataset_5M_real['high'][index_st] > st: st_pr = ((st - dataset_5M_real['high'][loc_end_5M_price])/dataset_5M_real['high'][loc_end_5M_price]) * 100
			
			my_money = money

			if my_money >=100:
				lot = int(my_money/100) * coef_money
			else:
				lot = coef_money

			if lot > 2000: lot = 2000

			my_money = my_money - (lot * st_pr)

			money = my_money

			candle_index = index_st

			# print('st = ', signals['pattern_day'][loc_end_5M], ' ', signals['time_high_front'][loc_end_5M].hour)

			flag = 'st'

		else:
			flag = 'no_flag'
			tp_pr = 0
			st_pr = 0

	return money, flag, tp_pr, st_pr, candle_index

loging = getdata()

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = symbol, number_5M = 'all', number_15M = 'all', number_1H = 'all')
dataset_5M = dataset_5M[symbol]
dataset_15M = dataset_15M[symbol]
dataset_1H = dataset_1H[symbol]

dataset_5M_real, _, _ = loging.readall(symbol = symbol, number_5M = 'all', number_15M = 0, number_1H = 0)
dataset_5M_real = dataset_5M_real[symbol]

feature_engineering = FeatureEngineering()

feature_engineering_5M, feature_engineering_15M, feature_engineering_1H = feature_engineering(
                                                                                                dataset_5M = dataset_5M, 
                                                                                                dataset_15M = dataset_15M, 
                                                                                                dataset_1H = dataset_1H, 
                                                                                                symbol = symbol, 
                                                                                                mode = None, 
                                                                                                scale = False
                                                                                                )
        
feature_engineering_5M = feature_engineering_5M.drop(columns = ['time', symbol])
feature_engineering_15M = feature_engineering_15M.drop(columns = ['time', symbol])
feature_engineering_1H = feature_engineering_1H.drop(columns = ['time', symbol])

image_size = len(feature_engineering_5M.columns)
if image_size < 225: image_size = 200

data_changer = DataChanger()
image_dataset_preparer = ImageDatasetPreparer()
predictor = Predictor()


model_max_1H = tf.keras.models.load_model(
										'model_' + feature_names_str.split(target_type)[0] + 'max_' + '1H' + '.h5', 
										custom_objects = {'MaxLayer': MaxLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_max_layer')}
										)

model_min_1H = tf.keras.models.load_model(
										'model_' + feature_names_str.split(target_type)[0] + 'min_' + '1H' + '.h5', 
										custom_objects = {'MinLayer': MinLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_min_layer')}
										)	

model_max_5M = tf.keras.models.load_model(
										'model_' + feature_names_str.split(target_type)[0] + 'max_' + '5M' + '.h5', 
										custom_objects = {'MaxLayer': MaxLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_max_layer')}
										)

model_min_5M = tf.keras.models.load_model(
										'model_' + feature_names_str.split(target_type)[0] + 'min_' + '5M' + '.h5', 
										custom_objects = {'MinLayer': MinLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_min_layer')}
										)

feature_engineering_1H_series = feature_engineering_1H.drop(columns = [
																	'pattern_week', 
																	'number',
																	'pattern_day',
																	'color_candle'
																	])

feature_engineering_5M_series = feature_engineering_5M.drop(columns = [
																	'pattern_week', 
																	'number',
																	'pattern_day',
																	'color_candle'
																	])
feature_names_1H = []
feature_names_1H.append(target_name)
feature_names_1H.extend(feature_engineering_1H_series.columns)

feature_names_5M = []
feature_names_5M.append(target_name)
feature_names_5M.extend(feature_engineering_5M_series.columns)

percent_feature_names_1H = []
for clm in feature_engineering_1H.columns:
	if 'target' in clm:
		percent_feature_names_1H.append(clm)
	if 'return' in clm:
		percent_feature_names_1H.append(clm)

feature_names_shouldnt_scale_1H = []
feature_names_shouldnt_scale_1H.extend(percent_feature_names_1H)

percent_feature_names_5M = []
for clm in feature_engineering_5M.columns:
	if 'target' in clm:
		percent_feature_names_5M.append(clm)
	if 'return' in clm:
		percent_feature_names_5M.append(clm)

feature_names_shouldnt_scale_5M = []
feature_names_shouldnt_scale_5M.extend(percent_feature_names_5M)

candle_index = start_point
counter_index = start_point

number_tp = 0
number_st = 0

if os.path.exists('MainTester.csv'):
	output = pd.read_csv('MainTester.csv').drop(columns = ['Unnamed: 0'])
	start_point = output['candle_index'].iloc[-1] + 1
	
	number_tp = output['number_tp'].iloc[-1]
	number_st = output['number_st'].iloc[-1] 
	money = output['money'].iloc[-1]
	tp_final = output['tp_final'].iloc[-1]
	st_final = output['st_final'].iloc[-1]
	percent = output['percent'].iloc[-1]
	tp = output['tp'].iloc[-1]
	st = output['st'].iloc[-1]

else:
	start_point = 24000
	output = pd.DataFrame(columns = [
									'candle_index', 
									'time', 
									# 'percent_predict',
									'Day',
									'signal', 
									'flag', 
									'number_tp', 
									'number_st', 
									'money', 
									'tp_final', 
									'st_final', 
									'percent', 
									'tp', 
									'st',
									])


print('Start ....')

for index_candle in feature_engineering_5M.index:

	# index_candle = candle_index

	if index_candle <= start_point: 
		candle_index = index_candle
		continue

	# print(candle_index)
	# print(index_candle)

	flag = 'no_flag'

	if True:

		dataset_5M_split, dataset_15M_split, dataset_1H_split = data_changer.SpliterSyncPR(
																							dataset_5M = dataset_5M,
																							dataset_15M = dataset_15M,
																							dataset_1H = dataset_1H,
																							loc_end_5M = candle_index,
																							length_5M = image_size,
																							length_15M = image_size,
																							length_1H = image_size,
                                                                                            reset_index = False,
																							)

		if dataset_1H_split['index'].iloc[-1] <= 500:
			candle_index += 1
			continue

		dataset_5M_split.index = dataset_5M_split['index']

		# print(dataset_5M_split)

		feature_engineering_split_5M = feature_engineering_5M.loc[dataset_5M_split['index'].iloc[0] : dataset_5M_split['index'].iloc[-1]]
		feature_engineering_split_15M = feature_engineering_15M.loc[dataset_15M_split['index'][0] : dataset_15M_split['index'].iloc[-1]]
		feature_engineering_split_1H = feature_engineering_1H.loc[dataset_1H_split['index'][0] : dataset_1H_split['index'].iloc[-1]]

		signal_image = image_dataset_preparer.RunOnline(
						                                  dataset_5M = feature_engineering_split_5M,
						                                  dataset_15M = feature_engineering_split_15M,
						                                  dataset_1H = feature_engineering_split_1H
						                                  )

		# signal_straight, percent_straight = predictor(model_name = 'final_image_model_full_image_model_straight', signal_image = signal_image)
		signal_complex, percent_complex = predictor(model_name = 'final_image_model_full_image_model_complex', signal_image = signal_image)
		# signal_double, percent_double = predictor(model_name = 'final_image_model_double_full_image_model', signal_image = signal_image)

		# print('signal_straight: ', signal_straight, percent_straight)
		# print('signal_complex: ', signal_complex, percent_complex)
		# print('signal_double: ', signal_double, percent_double)
		if (
			# signal_straight == 'buy' and #percent_straight >= 0.925 and#0.925 and
			signal_complex == 'buy' and percent_complex >= 0.9
			# signal_double == 'buy' #and percent_double >= 0.97 #0.97
			):

			signal_buy_no_trade, percent_buy_no_trade = predictor(model_name = 'final_image_model_buy_no_trade', signal_image = signal_image)

			if signal_buy_no_trade == 'buy' and percent_buy_no_trade >= 0.9:#0.97:

				signal_buy_sell, percent_buy_sell = predictor(model_name = 'final_image_model_buy_sell', signal_image = signal_image)

				if signal_buy_sell == 'buy' and percent_buy_sell >= 0.9:#0.99:

					signal = 'buy'

				else:
					signal = 'no_trade'

			else:
				signal = 'no_trade'


		elif (
				# signal_straight == 'sell' and #percent_straight >= 0.95 #0.95 and
				signal_complex == 'sell' and percent_complex >= 0.9
				# signal_double == 'sell' #and percent_double >= 0.97 #0.97
			):

			signal_sell_no_trade, percent_sell_no_trade = predictor(model_name = 'final_image_model_sell_no_trade', signal_image = signal_image)

			if signal_sell_no_trade == 'sell' and percent_sell_no_trade >= 0.9:#0.99:

				signal_buy_sell, percent_buy_sell = predictor(model_name = 'final_image_model_buy_sell', signal_image = signal_image)

				if signal_buy_sell == 'sell' and percent_buy_sell >= 0.9:#0.99:

					signal = 'sell'

				else:
					signal = 'no_trade'

			else:
				signal = 'no_trade'

		else:
			signal = 'no_trade'

		

	else:# Exception as ex:
		print('predict Error: ', ex)
		signal = 'no_trade'
		resist = 0
		protect = 0
		mpf_5M.figure().clear()
	
	# print('signal: ', signal)

	if signal == 'buy':

		time_series_1H = pd.DataFrame(feature_engineering_1H, columns = feature_names_1H)
		time_series_5M = pd.DataFrame(feature_engineering_5M, columns = feature_names_5M)

		dataset_5M_split_serie, _, dataset_1H_split_serie = data_changer.SpliterSyncPR(
																						dataset_5M = dataset_5M,
																						dataset_15M = dataset_15M,
																						dataset_1H = dataset_1H,
																						loc_end_5M = candle_index,
																						length_5M = 500,
																						length_15M = 10,
																						length_1H = 500,
					                                                                    reset_index = False,
																						)
		
		if dataset_1H_split_serie['index'].iloc[-1] <= 500:
			candle_index += 1
			continue
		
		
		data_predict_1H = window_dataset_predict(
											series = time_series_1H.loc[dataset_1H_split_serie['index'].iloc[-1] - 500: dataset_1H_split_serie['index'].iloc[-1]], 
											window_size = 500, 
											batch_size = 1,
											shift = 1,
											target_name = target_name,
											feature_names = feature_names_1H,
											feature_names_shouldnt_scale = percent_feature_names_1H,
											price_feature_names_general = ''
											)

		predict_serie_min_1H = model_min_1H.predict(data_predict_1H, verbose = 0)
		predict_serie_min_1H = predict_serie_min_1H[-1, -1, 0] + 0.5
		predict_serie_max_1H = model_max_1H.predict(data_predict_1H, verbose = 0)
		predict_serie_max_1H = predict_serie_max_1H[-1, -1, 0] + 0.5

		data_predict_5M = window_dataset_predict(
											series = time_series_5M.loc[dataset_5M_split_serie['index'].iloc[-1] - 500: dataset_5M_split_serie['index'].iloc[-1]], 
											window_size = 500, 
											batch_size = 1,
											shift = 1,
											target_name = target_name,
											feature_names = feature_names_5M,
											feature_names_shouldnt_scale = percent_feature_names_5M,
											price_feature_names_general = ''
											)

		predict_serie_min_5M = model_min_5M.predict(data_predict_5M, verbose = 0)
		predict_serie_min_5M = predict_serie_min_5M[-1, -1, 0]
		predict_serie_max_5M = model_max_5M.predict(data_predict_5M, verbose = 0)
		predict_serie_max_5M = predict_serie_max_5M[-1, -1, 0]

		tp_1H = dataset_1H_split_serie['high'].iloc[-1] * (predict_serie_max_1H + spred)
		st_1H = dataset_1H_split_serie['low'].iloc[-1] * (predict_serie_min_1H - spred)

		tp_5M = dataset_5M_split_serie['high'].iloc[-1] * (predict_serie_max_5M + spred)
		st_5M = dataset_5M_split_serie['low'].iloc[-1] * (predict_serie_min_5M - spred)

		tp = (tp_1H + tp_5M)/2
		st = (st_1H + st_5M)/2

		if st >= dataset_5M_split_serie['low'].iloc[-1]:
			st = dataset_5M_split_serie['low'].iloc[-1] * 0.9992

		print('Buy: ', 'High: ', dataset_5M_split_serie['high'].iloc[-1], 'Tp: ', tp, 'Low: ', dataset_5M_split_serie['low'].iloc[-1], 'St: ', st)

		try:
			money, flag, tp_pr, st_pr, candle_index_last = BuyChecker(dataset_5M_real, tp, st, dataset_5M_split['index'].iloc[-1], money, coef_money, spred)

			# index_candle = candle_index_last
			# plt.plot(dataset_5M[symbol]['low'][candle_index: candle_index_last + 1000], c = 'r')
			# plt.axvline(x = candle_index, linestyle = '-.', c = 'g')

			# plt.plot(dataset_5M_real['high'][candle_index: candle_index_last + 4000], c = 'r')
			# plt.plot(dataset_5M_real['low'][candle_index: candle_index_last + 4000], c = 'g')
			# # plt.show()
			# plt.title(label = signal)

			# plt.savefig('SimulatePics/buy/' + flag + '/' + signal + '_' + str(candle_index), dpi=600, bbox_inches='tight')

			# plt.figure().clear()
			# plt.close('all')
			# plt.cla()
			# plt.clf()
			# plt.show()
		except Exception as ex:
			print('Buy: ', ex) 
			flag = 'no_flag' 
			tp_pr = 0
			st_pr = 0

		if plot_signals == True:
			if not os.path.exists('SimulatePics/buy/' + flag + '/'):
				os.makedirs('SimulatePics/buy/' + flag + '/')
			daily_5M = pd.DataFrame(dataset_5M_real.loc[dataset_5M_split['index'].iloc[0]: candle_index_last + 10])
			daily_5M.index.name = 'Time'
			daily_5M.index = dataset_5M_real['time'][daily_5M.index]
			daily_5M.head(3)
			daily_5M.tail(3)

			mc_5M = mpf_5M.make_marketcolors(
										base_mpf_style='yahoo',
										up='green',
										down='red',
										#vcedge = {'up': 'green', 'down': 'red'}, 
										vcdopcod = True,
										alpha = 0.0001
										)

			mco_5M = [mc_5M]*len(daily_5M)

			mpf_5M.plot(
					daily_5M,
					type='candle',
					volume=True,
					style='yahoo',
					figscale=1,
					hlines=dict(hlines=[tp,st],colors=['black','purple'],linestyle='dotted'),
					vlines=dict(vlines=[dataset_5M_real['time'][dataset_5M_split['index'].iloc[-1]], dataset_5M_real['time'][candle_index_last]],colors=['orange', 'yellow'], linestyle='dotted'),
					savefig=dict(fname='SimulatePics/buy/' + flag + '/' + str(candle_index) + '_5M_candle_' + flag,dpi=600,pad_inches=0.25),
					marketcolor_overrides=mco_5M,
					#alines=dict(alines=two_points,colors=['orange'],linestyle='-.'),
					)

		# if flag != 'no_flag':
		# 	plt.show()
		# 	plt.axhline(y = tp, c = 'r')
		# 	plt.axhline(y = st, c = 'r')
		# 	plt.savefig('SimulatePics/buy/' + str(candle_index) + '_5M', dpi=600, bbox_inches='tight')
		
	elif signal == 'sell':

		time_series_1H = pd.DataFrame(feature_engineering_1H, columns = feature_names_1H)
		time_series_5M = pd.DataFrame(feature_engineering_5M, columns = feature_names_5M)

		dataset_5M_split_serie, _, dataset_1H_split_serie = data_changer.SpliterSyncPR(
																						dataset_5M = dataset_5M,
																						dataset_15M = dataset_15M,
																						dataset_1H = dataset_1H,
																						loc_end_5M = candle_index,
																						length_5M = 500,
																						length_15M = 10,
																						length_1H = 500,
					                                                                    reset_index = False,
																						)
		
		if dataset_1H_split_serie['index'].iloc[-1] <= 500:
			candle_index += 1
			continue
		
		
		data_predict_1H = window_dataset_predict(
											series = time_series_1H.loc[dataset_1H_split_serie['index'].iloc[-1] - 500: dataset_1H_split_serie['index'].iloc[-1]], 
											window_size = 500, 
											batch_size = 1,
											shift = 1,
											target_name = target_name,
											feature_names = feature_names_1H,
											feature_names_shouldnt_scale = percent_feature_names_1H,
											price_feature_names_general = ''
											)

		predict_serie_min_1H = model_min_1H.predict(data_predict_1H, verbose = 0)
		predict_serie_min_1H = predict_serie_min_1H[-1, -1, 0] + 0.5
		predict_serie_max_1H = model_max_1H.predict(data_predict_1H, verbose = 0)
		predict_serie_max_1H = predict_serie_max_1H[-1, -1, 0] + 0.5

		data_predict_5M = window_dataset_predict(
											series = time_series_5M.loc[dataset_5M_split_serie['index'].iloc[-1] - 500: dataset_5M_split_serie['index'].iloc[-1]], 
											window_size = 500, 
											batch_size = 1,
											shift = 1,
											target_name = target_name,
											feature_names = feature_names_5M,
											feature_names_shouldnt_scale = percent_feature_names_5M,
											price_feature_names_general = ''
											)

		predict_serie_min_5M = model_min_5M.predict(data_predict_5M, verbose = 0)
		predict_serie_min_5M = predict_serie_min_5M[-1, -1, 0]
		predict_serie_max_5M = model_max_5M.predict(data_predict_5M, verbose = 0)
		predict_serie_max_5M = predict_serie_max_5M[-1, -1, 0]

		st_1H = dataset_1H_split_serie['high'].iloc[-1] * (predict_serie_max_1H + spred)
		tp_1H = dataset_1H_split_serie['low'].iloc[-1] * (predict_serie_min_1H - spred)

		st_5M = dataset_5M_split_serie['high'].iloc[-1] * (predict_serie_max_5M + spred)
		tp_5M = dataset_5M_split_serie['low'].iloc[-1] * (predict_serie_min_5M - spred)

		tp = (tp_1H + tp_5M)/2
		st = (st_1H + st_5M)/2

		if st <= dataset_5M_split_serie['high'].iloc[-1]:
			st = dataset_5M_split_serie['high'].iloc[-1] * 1.0008

		print('Sell: ', 'High: ', dataset_5M_split_serie['high'].iloc[-1], 'Tp: ', tp, 'Low: ', dataset_5M_split_serie['low'].iloc[-1], 'St: ', st)

		try:
			money, flag, tp_pr, st_pr, candle_index_last = SellChecker(dataset_5M_real, tp, st, dataset_5M_split['index'].iloc[-1], money, coef_money, spred)

			# plt.plot(dataset_5M[symbol]['low'][candle_index: candle_index_last + 1000], c = 'r')
			# plt.axvline(x = candle_index, linestyle = '-.', c = 'g')

			# plt.plot(dataset_5M_real['high'][candle_index: candle_index_last + 4000], c = 'r')
			# plt.plot(dataset_5M_real['low'][candle_index: candle_index_last + 4000], c = 'g')
			# # plt.show()
			# plt.title(label = signal)

			# plt.savefig('SimulatePics/buy/' + flag + '/' + signal + '_' + str(candle_index), dpi=600, bbox_inches='tight')

			# plt.figure().clear()
			# plt.close('all')
			# plt.cla()
			# plt.clf()
			# plt.show()
		except Exception as ex:
			print('Sell: ', ex) 
			flag = 'no_flag' 
			tp_pr = 0
			st_pr = 0

		if plot_signals == True:
			if not os.path.exists('SimulatePics/sell/' + flag + '/'):
				os.makedirs('SimulatePics/sell/' + flag + '/')
			daily_5M = pd.DataFrame(dataset_5M_real.loc[dataset_5M_split['index'].iloc[0]: candle_index_last + 10])
			daily_5M.index.name = 'Time'
			daily_5M.index = dataset_5M_real['time'][daily_5M.index]
			daily_5M.head(3)
			daily_5M.tail(3)

			mc_5M = mpf_5M.make_marketcolors(
										base_mpf_style='yahoo',
										up='green',
										down='red',
										#vcedge = {'up': 'green', 'down': 'red'}, 
										vcdopcod = True,
										alpha = 0.0001
										)

			mco_5M = [mc_5M]*len(daily_5M)

			mpf_5M.plot(
					daily_5M,
					type='candle',
					volume=True,
					style='yahoo',
					figscale=1,
					hlines=dict(hlines=[tp,st],colors=['black','purple'],linestyle='dotted'),
					vlines=dict(vlines=[dataset_5M_real['time'][dataset_5M_split['index'].iloc[-1]], dataset_5M_real['time'][candle_index_last]],colors=['orange', 'yellow'],linestyle='dotted'),
					savefig=dict(fname='SimulatePics/sell/' + flag + '/' + str(candle_index) + '_5M_candle_' + flag,dpi=600,pad_inches=0.25),
					marketcolor_overrides=mco_5M,
					#alines=dict(alines=two_points,colors=['orange'],linestyle='-.'),
					)

		# if flag != 'no_flag':
		# 	plt.show()
		# 	plt.axhline(y = tp, c = 'r')
		# 	plt.axhline(y = st, c = 'r')
		# 	plt.savefig('SimulatePics/sell/' + str(candle_index) + '_5M', dpi=600, bbox_inches='tight')

		# mpf_5M.figure().clear()
		# plt.figure().clear()
		# plt.close('all')
		# plt.cla()
		# plt.clf()

	if flag == 'tp':
		percent += tp_pr
		tp_pr_eq += tp_pr
		number_tp += 1

		# signal_image = signal_image * 255

		# cv2.imwrite(
		# 				(
		# 				'SimulatePics/' + signal + '/' + signal + '_' + str(candle_index) + '.jpg'
		# 				)
		# 			, signal_image , [int(cv2.IMWRITE_JPEG_QUALITY), 100]
		# 			)

		output = output.append(
								{
								'candle_index': candle_index,
								'time': dataset_5M_split['time'].iloc[-1],
								# 'percent_predict': signal_predict[0][np.argmax(signal_predict)],
								'Day': dataset_5M_real['time'][candle_index].day_name(),
								'signal': signal,
								# 'indicator': indicator,
								'flag': flag,
								'number_tp': number_tp,
								'number_st': number_st,
								'money': money,
								'tp_final': tp_pr_eq,
								'st_final': st_pr_eq,
								'percent': percent,
								'tp': tp_pr,
								'st': st_pr,
								},
								ignore_index = True
								)
		# candle_index = candle_index_last
		print()
		with pd.option_context('display.max_rows', None, 'display.max_columns', None):
			print(output.iloc[-1])
		print()

		if os.path.exists('MainTester.csv'):
			os.remove('MainTester.csv')
		output.to_csv('MainTester.csv')

	elif flag == 'st':
		percent -= st_pr
		st_pr_eq += st_pr
		number_st += 1

		# signal_image = signal_image * 255

		# if tp_pr < 0.2:
		# 	cv2.imwrite(
		# 					(
		# 					'SimulatePics/' + 'no_trade' + '/' + 'no_trade' + '_' + str(candle_index) + '.jpg'
		# 					)
		# 				, signal_image , [int(cv2.IMWRITE_JPEG_QUALITY), 100]
		# 				)

		# 	cv2.imwrite(
		# 					(
		# 					'SimulatePics/' + 'no_trade_' + signal + '/' + 'no_trade_' + signal + '_' + str(candle_index) + '.jpg'
		# 					)
		# 				, signal_image , [int(cv2.IMWRITE_JPEG_QUALITY), 100]
		# 				)

		output = output.append(
								{
								'candle_index': candle_index,
								'time': dataset_5M_split['time'].iloc[-1],
								# 'percent_predict': signal_predict[0][np.argmax(signal_predict)],
								'Day': dataset_5M_real['time'][candle_index].day_name(),
								'signal': signal,
								# 'indicator': indicator,
								'flag': flag,
								'number_tp': number_tp,
								'number_st': number_st,
								'money': money,
								'tp_final': tp_pr_eq,
								'st_final': st_pr_eq,
								'percent': percent,
								'tp': tp_pr,
								'st': st_pr,
								},
								ignore_index = True
								)
		# candle_index = candle_index_last
		print()
		with pd.option_context('display.max_rows', None, 'display.max_columns', None):
			print(output.iloc[-1])
		print()

		if os.path.exists('MainTester.csv'):
			os.remove('MainTester.csv')
		output.to_csv('MainTester.csv')

	# if money <= 4: break

	candle_index += 1

# if os.path.exists('MainTester.csv'):
# 	os.remove('MainTester.csv')
# output.to_csv('MainTester.csv')


print('* Final Money = ', money)
print('********** tp = ', tp_pr_eq)
print('********** st = ', st_pr_eq)
print('Fanal percent = ', percent)


# candle_index                     22926
# time               2021-03-19 09:15:00
# percent_predict               0.754421
# Day                             Friday
# signal                             buy
# flag                                st
# number_tp                          106
# number_st                          167
# money                       218.431162
# tp_final                       39.7505
# st_final                     32.367006
# percent                       7.383494
# tp                            0.079865
# st                                 0.2
# Name: 272, dtype: object

# candle_index                   8720
# time            2021-01-06 05:55:00
# Day                       Wednesday
# signal                          buy
# flag                             tp
# number_tp                        17
# number_st                        32
# money                     109.88805
# tp_final                   6.518992
# st_final                    6.02459
# percent                    0.494403
# tp                         0.359856
# st                         0.040682


