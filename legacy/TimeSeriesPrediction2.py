import pandas as pd
import tensorflow as tf
# import tensorflow_transform as tft
import tensorflow_datasets as tfds
import tensorflow_hub as hub
import numpy as np
from mlxtend.preprocessing import minmax_scaling
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.FeatureEngineering import FeatureEngineering
from src.utils.FeatureEngineering.DatasetIO import DatasetIO
from src.utils.FeatureEngineering.Patterns import Patterns
import shutil
import logging
import sys
import os

logger = tf.get_logger()
logger.setLevel(logging.ERROR)

# sys.exit()

tf.random.set_seed(1000)
np.random.seed(1000)

def to_windows(dataset, length, shift):
	dataset = dataset.window(int(length), shift = shift, drop_remainder = True)
	return dataset.flat_map(lambda window_ds: window_ds.batch(int(length)))

def to_seq2seq_dataset(
						series, 
						window_size = 56, 
						batch_size = 32, 
						shuffle = False, 
						seed = None,
						size_target = 12,
						shift = 1, 
						target_name = 'close',
						target_type = 'max',
						feature_names = [],
						feature_names_shouldnt_scale = []
						):
	
	dataset = to_windows(tf.data.Dataset.from_tensor_slices(series), size_target + 1, shift)
	dataset = to_windows(dataset, window_size, shift)

	# for x in dataset:
	# 	print('x = ', x.numpy())
	# 	# print('y = ', y.numpy())
	# 	print('shape x = ', tf.shape(x))
	# 	# print('shape y = ', tf.shape(y))

	target = np.where(series.columns == target_name)[0][0]
	feature_names_copy = feature_names.copy()
	#feature_names_copy.remove(target_name)
	feature_names_list = []

	print('feat copy = ', len(feature_names_copy))

	for elm in feature_names_copy:
		feature_names_list.append(np.where(series.columns == elm)[0][0])

	feature_names_shouldnt_scale_list = []

	for elm in feature_names_shouldnt_scale:
		
		if elm in series.columns:
			feature_names_shouldnt_scale_list.append(np.where(series.columns == elm)[0][0])

	# @tf.function
	def MinMax_Feature(dataset, feature_names_list, size_target, feature_names_shouldnt_scale_list):

		input_list = []

		for feat in feature_names_list:

			if (feat in feature_names_shouldnt_scale_list):

				input_list.append(
									tf.cast(
											(
												(
													dataset[: , 0 , feat]
												) * 4.0
											) - 2.0,
											tf.float64
											)
								)
			else:

				input_list.append(
									tf.cast(
												(
													(
														(dataset[: , 0 , feat] - tf.math.reduce_min(dataset[: , 0 , feat]))/
														(tf.math.reduce_max(dataset[: , 0 , feat]) - tf.math.reduce_min(dataset[: , 0 , feat]))
													) * 4.0
												) - 2.0,
											tf.float64
											)
								)

		# (tf.math.reduce_max(dataset[: , 0 , feat]) - tf.math.reduce_min(dataset[: , 0 , feat]))

		input_list = tf.transpose(input_list)
		input_model = tf.stack(input_list)
		return input_model

	@tf.function
	def MinMax_Target(dataset, target, target_type, size_target, window_size):

		input_list = []


		input_list.append(
							tf.cast(
										(
			    							(
			    								(dataset[:, 1: , target] - tf.math.reduce_min(dataset[:, 0 , target]))/
			    								(tf.math.reduce_max(dataset[:, 0 , target]) - tf.math.reduce_min(dataset[:, 0 , target]))
			    							)
			    						)[ : , -1],
									tf.float64
									)
    					)
		# (tf.math.reduce_max(dataset[:, 0 , target]) - tf.math.reduce_min(dataset[:, 0 , target]))
		target_out = tf.stack(input_list[0])
		return target_out

	dataset = dataset.map(
							lambda window: (
											MinMax_Feature(
															dataset = window, 
															feature_names_list = feature_names_list, 
															size_target = size_target,
															feature_names_shouldnt_scale_list = feature_names_shouldnt_scale_list
															), 
											MinMax_Target(
															dataset = window, 
															target = target,
															target_type = target_type,
															size_target = size_target,
															window_size = window_size
															)
											)
							)

	# if True:#shuffle:
	# 	dataset = dataset.shuffle(420 * batch_size)#, seed = seed)

	# print('*********************************************')
	# counter = 0
	# import matplotlib.pyplot as plt
	# for x, y in dataset:
	# 	if counter >= 0:
	# 	# 	print('counter = ', counter)
	# 		print('x = ', x.numpy())
	# 		print('y = ', y.numpy())
	# 		print('shape x = ', tf.shape(x))
	# 		print('shape y = ', tf.shape(y))

	# 		# plt.plot(x[: , target].numpy())
	# 		plt.plot(x.numpy())
	# 		plt.plot(range(size_target, window_size + size_target), y[:].numpy(), linestyle = '--', c = 'black')
	# 		plt.show()
		
	# 	counter += 1

	return dataset.batch(batch_size).prefetch(1)

class GatedActivationUnit(tf.keras.layers.Layer):

	def __init__(self, activation="tanh", **kwargs):

		super(GatedActivationUnit, self).__init__(**kwargs)
		self.activation = tf.keras.activations.get(activation)

	def call(self, inputs):
		n_filters = inputs.shape[-1] // 2
		linear_output = self.activation(inputs[..., :n_filters])
		gate = tf.keras.activations.sigmoid(inputs[..., n_filters:])
		return self.activation(linear_output) * gate

	def get_config(self):
		config = super().get_config()
		config.update(
						{
						'activation': self.activation,
						}
						)
		return config

	@classmethod
	def from_config(cls, config):
		return cls(**config)


# kernel_regularizer = tf.keras.regularizers.L2(1.8e-2)
kernel_regularizer = None #tf.keras.regularizers.L2(1.5e-5)
activity_regularizer = None #tf.keras.regularizers.L2(1.5e-5)
bias_regularizer = None #tf.keras.regularizers.L2(1.0e-9)

def wavenet_residual_block(inputs, n_filters, dilation_rate):

	z = tf.keras.layers.Conv1D(
								filters = n_filters * 2, 
								kernel_size = 5, 
								padding = "causal",
								dilation_rate = dilation_rate,
								# kernel_regularizer = kernel_regularizer,
								# activity_regularizer = activity_regularizer,
								# bias_regularizer = bias_regularizer,
								)(inputs)

	# z = tf.keras.layers.Dropout(0.05)(z)

	z = GatedActivationUnit()(z)
	z = tf.keras.layers.Conv1D(
								filters = n_filters, 
								kernel_size = 5,
								padding = 'causal',
								# kernel_regularizer = None,#tf.keras.regularizers.L1L2(l1 = 1.5e-5, l2 = 1.5e-5),#kernel_regularizer,
								# activity_regularizer = tf.keras.regularizers.L1L2(l1 = 1.5e-4, l2 = 1.5e-7),#activity_regularizer,
								# bias_regularizer = bias_regularizer,
								)(z)

	return tf.keras.layers.Add()([z, inputs]), z


loging = getdata()

symbol = 'XAUUSD_i'

RUN_FLAG = False

if RUN_FLAG == True:
	dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D = loging.readall(
																				symbol = symbol, 
																				number_5M = 'all', 
																				number_15M = 'all', 
																				number_1H = 'all',
																				number_4H = 'all',
																				number_1D = 'all'
																				)

	dataset_5M = dataset_5M[symbol]
	dataset_15M = dataset_15M[symbol] #pd.DataFrame() # dataset_15M[symbol]
	dataset_1H = dataset_1H[symbol] #pd.DataFrame()# dataset_1H[symbol]
	dataset_4H = dataset_4H[symbol] #pd.DataFrame()# dataset_4H[symbol]
	dataset_1D = dataset_1D[symbol] #pd.DataFrame()# dataset_1D[symbol]

	feature_engineering = FeatureEngineering()

	feature_engineering.fourier_features_flag['main'] = True
	feature_engineering.fourier_features_flag['5M'] = True
	feature_engineering.fourier_features_flag['15M'] = True
	feature_engineering.fourier_features_flag['1H'] = False
	feature_engineering.fourier_features_flag['4H'] = False
	feature_engineering.fourier_features_flag['1D'] = True

	_, _, _, _, feature_engineering_1D = feature_engineering(
			                                                    dataset_5M = dataset_5M, 
			                                                    dataset_15M = dataset_15M, 
			                                                    dataset_1H = dataset_1H, 
			                                                    dataset_4H = dataset_4H, 
			                                                    dataset_1D = dataset_1D, 
			                                                    symbol = symbol, 
			                                                    mode = 'Run', 
			                                                    scale = False
			                                                )

	dataset_5M = dataset_1D[symbol]
	dataset_15M = pd.DataFrame()
	dataset_1H = pd.DataFrame()
	dataset_4H = pd.DataFrame()
	dataset_1D = pd.DataFrame()

else:
	_, _, _, _, dataset_1D = loging.readall(
												symbol = symbol, 
												number_5M = 0, 
												number_15M = 0, 
												number_1H = 0,
												number_4H = 0,
												number_1D = 'all'
											)


	dataset_5M = dataset_1D[symbol]
	dataset_15M = pd.DataFrame()
	dataset_1H = pd.DataFrame()
	dataset_4H = pd.DataFrame()
	dataset_1D = pd.DataFrame()

	feature_engineering = FeatureEngineering()

	feature_engineering.fourier_features_flag['main'] = True
	feature_engineering.fourier_features_flag['5M'] = False
	feature_engineering.fourier_features_flag['15M'] = False
	feature_engineering.fourier_features_flag['1H'] = False
	feature_engineering.fourier_features_flag['4H'] = False
	feature_engineering.fourier_features_flag['1D'] = True

	_, _, _, _, feature_engineering_1D = feature_engineering(
			                                                    dataset_5M = dataset_5M, 
			                                                    dataset_15M = dataset_15M, 
			                                                    dataset_1H = dataset_1H, 
			                                                    dataset_4H = dataset_4H, 
			                                                    dataset_1D = dataset_1D, 
			                                                    symbol = symbol, 
			                                                    mode = None, 
			                                                    scale = False
			                                                    )


if symbol in feature_engineering_1D.columns:

	# feature_engineering_4H = feature_engineering_4H.drop(columns = [symbol])
	feature_engineering_1D = feature_engineering_1D.drop(columns = [symbol])
	# feature_engineering_1D = feature_engineering_1D.drop(columns = ['number'])


# dataset_4h = feature_engineering_4H.copy(deep = True)
# dataset_4h.index = pd.to_datetime(dataset_4h['time'], utc = True)

# dataset_1d = feature_engineering_1D.copy(deep = True)
# dataset_1d['time'] = pd.to_datetime(dataset_1d['time'], utc = True)
# dataset_1d.index = dataset_1d['time']
# dataset_1d = dataset_1d.drop(columns = ['number'])
# feature_engineering_1D = feature_engineering_1D.drop(columns = ['number'])

# dataset = pd.DataFrame()

# for clm in feature_engineering_4H.columns:
# 	dataset[clm + '_4H'] = dataset_4h[clm]

# for clm in feature_engineering_1D.columns:
# 	dataset[clm + '_1D'] = dataset_1d[clm]

# dataset = dataset.fillna(method = 'ffill', axis = 0).fillna(0)
# dataset.index = range(0 , len(dataset['close_4H']))

dataset = feature_engineering_1D


for clm in dataset.columns:
	if 'time' in clm:
		dataset = dataset.drop(columns = [clm])

	if clm == 'price_balance':
		dataset = dataset.drop(columns = [clm])

	if clm == 'volume_balance':
		dataset = dataset.drop(columns = [clm])

	# if 'volume' in clm:
	# 	dataset = dataset.drop(columns = [clm])

feature_engineering_5M = dataset

print(feature_engineering_5M)
# import matplotlib.pyplot as plt

# plt.plot(feature_engineering_5M['open_return_51_1'])
# plt.plot(feature_engineering_5M['open_target_51_1'])
# plt.show()

timeframe = '1D'
target_name = 'low'#_' + timeframe
target_type = 'price_sin_' + target_name
window_size = 500
size_target = 1
shift = 1

if target_name == 'high':
	un_target_name = 'low'
elif target_name == 'low':
	un_target_name = 'high'

feature_names = []

feature_names.append(target_name)
feature_names.extend(feature_engineering_5M.columns)

for feat_name in feature_names:
	if un_target_name in feat_name:
		feature_names.remove(feat_name)

name = 'high'
feature_names_high = []

feature_names_high.append(name)
feature_names_high.extend(feature_engineering_5M.columns)
for name in feature_names_high:
	if 'low' in name:
		feature_names_high.remove(name)

name = 'low'
feature_names_low = []

feature_names_low.append(name)
feature_names_low.extend(feature_engineering_5M.columns)
for name in feature_names_low:
	if 'high' in name:
		feature_names_low.remove(name)

# feature_names.extend(['high_4H'])

print('max = ', feature_engineering_5M[target_name].max())
print('min = ', feature_engineering_5M[target_name].min())
print('diff = ', feature_engineering_5M[target_name].max() - feature_engineering_5M[target_name].min())

diff_max_min = feature_engineering_5M[target_name].max() - feature_engineering_5M[target_name].min()


feature_names_str = 'All_feature_' + target_type

feature_names_shouldnt_scale_list = []
for clm in feature_engineering_5M.columns:

	if 'sin' in clm:
		feature_engineering_5M[clm] = (feature_engineering_5M[clm] + 1.0)/2.0
		feature_names_shouldnt_scale_list.append(clm)

	if 'cos' in clm:
		feature_engineering_5M[clm] = (feature_engineering_5M[clm] + 1.0)/2.0
		feature_names_shouldnt_scale_list.append(clm)

	if 'color' in clm:
		feature_names_shouldnt_scale_list.append(clm)

	if 'StochAstic' in clm:
		feature_engineering_5M[clm] = (feature_engineering_5M[clm]/100.0)
		feature_names_shouldnt_scale_list.append(clm)

	if 'rsi' in clm:
		feature_engineering_5M[clm] = (feature_engineering_5M[clm]/100.0)
		feature_names_shouldnt_scale_list.append(clm)

	# if 'atr' in clm:
	# 	feature_engineering_5M[clm] = (feature_engineering_5M[clm]/100.0)
	# 	feature_names_shouldnt_scale_list.append(clm)

	# if 'target' in clm:
	# 	print('min ', clm, ' =', feature_engineering_5M[clm].min())
	# 	print('max ', clm, ' =', feature_engineering_5M[clm].max())
	# 	# feature_engineering_5M[clm] = (feature_engineering_5M[clm]/100.0)
	# 	feature_names_shouldnt_scale_list.append(clm)


# import matplotlib.pyplot as plt
# plt.plot(feature_engineering_5M['extension_green'])
# plt.show()
	


feature_names_shouldnt_scale = []
feature_names_shouldnt_scale.extend(feature_names_shouldnt_scale_list)

print()
print()
print('**********************************')
print('percent_price = ', len(feature_engineering_5M.columns))
print(feature_engineering_5M.columns)
print(feature_names_high)
print(feature_names_low)
print(len(feature_names_high))
print(len(feature_names_low))
print('//////////////////////////////////')
print()
print()

# feature_names = [target_name]
# for clm in feature_engineering_5M.columns:
# 	if 'diff' in clm:
# 		feature_names.append(clm)

feature_engineering_5M_high = pd.DataFrame(feature_engineering_5M, columns = feature_names_high)
feature_engineering_5M_low = pd.DataFrame(feature_engineering_5M, columns = feature_names_low)

print('feature_engineering_5M_high = ', len(feature_engineering_5M_high.columns))
print('feature_engineering_5M_low = ', len(feature_engineering_5M_low.columns))

feature_engineering_5M = pd.DataFrame(feature_engineering_5M, columns = feature_names)

total = len(feature_engineering_5M.index)
start_point = total

#24781
#0.9138
# import matplotlib.pyplot as plt
# for clm in feature_engineering_5M.columns:

# 	if 'return' in clm:
# 		plt.plot(feature_engineering_5M[clm])
# 		print(clm)
# 		plt.show()

# 	if 'target' in clm:
# 		plt.plot(feature_engineering_5M[clm])
# 		print(clm)
# 		plt.show()

num_test = 50
Batch_Size = 1

train_feature_engineering_5M = feature_engineering_5M.loc[100 : total - num_test]
valid_feature_engineering_5M = feature_engineering_5M.loc[total - window_size - (2 * num_test) : total - num_test]
test_feature_engineering_5M = feature_engineering_5M.loc[total - window_size - num_test : ]
test_feature_engineering_5M_high = feature_engineering_5M_high.loc[total - window_size - num_test : ]
test_feature_engineering_5M_low = feature_engineering_5M_low.loc[total - window_size - num_test : ]

# train_feature_engineering_5M = feature_engineering_5M.loc[int(total * 0.975) : int(total * 0.99)]
# valid_feature_engineering_5M = feature_engineering_5M.loc[int(total * 0.99) : ]

# dataset_train = to_seq2seq_dataset(
# 								series = train_feature_engineering_5M, 
# 								window_size = window_size, 
# 								batch_size = Batch_Size, 
# 								shuffle = False, 
# 								seed = 42,
# 								size_target = size_target,
# 								shift = shift, 
# 								target_name = target_name,
# 								target_type = target_type,
# 								feature_names = feature_names,
# 								feature_names_shouldnt_scale = feature_names_shouldnt_scale
# 								)

# dataset_valid = to_seq2seq_dataset(
# 								series = valid_feature_engineering_5M, 
# 								window_size = window_size, 
# 								batch_size = Batch_Size, 
# 								shuffle = False, 
# 								seed = 42,
# 								size_target = size_target,
# 								shift = shift, 
# 								target_name = target_name,
# 								target_type = target_type,
# 								feature_names = feature_names,
# 								feature_names_shouldnt_scale = feature_names_shouldnt_scale
# 								)

# dataset_test = to_seq2seq_dataset(
# 								series = test_feature_engineering_5M, 
# 								window_size = window_size, 
# 								batch_size = Batch_Size, 
# 								shuffle = False, 
# 								seed = 42,
# 								size_target = size_target,
# 								shift = shift, 
# 								target_name = target_name,
# 								target_type = target_type,
# 								feature_names = feature_names,
# 								feature_names_shouldnt_scale = feature_names_shouldnt_scale
# 								)

# tf.random.set_seed(42)
def Model_Creator():

	n_layers_per_block = 9#7  # 10 in the paper
	n_blocks = 5#8  # 3 in the paper
	n_filters = 128  # 128 in the paper
	n_outputs = size_target  # 256 in the paper

	inputs = tf.keras.layers.Input(shape=[None, len(feature_names) - 1])#, batch_size = Batch_Size)

	z = tf.keras.layers.SeparableConv1D(
										filters = n_filters, 
										kernel_size = 10, 
										padding = "causal",
										depth_multiplier = 50,
										# kernel_regularizer = kernel_regularizer,
										# activity_regularizer = activity_regularizer,
										# bias_regularizer = bias_regularizer,
										)(inputs)	

	z = tf.keras.layers.Dropout(0.02)(z)																

	skip_to_last = []

	for dilation_rate in [2**i for i in range(n_layers_per_block)] * n_blocks:

	    z, skip = wavenet_residual_block(z, n_filters, dilation_rate)
	    skip_to_last.append(skip)

	z = tf.keras.activations.tanh(tf.keras.layers.Add()(skip_to_last))

	# z = tf.keras.layers.SpatialDropout1D(0.46)(z)

	z = tf.keras.layers.SeparableConv1D(
										filters = n_filters, 
										kernel_size = 10, 
										activation = "tanh",
										padding = 'causal',
										depth_multiplier = 50,
										# kernel_regularizer = kernel_regularizer,
										# activity_regularizer = activity_regularizer,
									    bias_initializer="glorot_uniform",
										# bias_regularizer = tf.keras.regularizers.L1L2(l1 = 60, l2 = 10),
										# use_bias = False,
										)(z)

	# z = tf.keras.layers.RNN(
	# 						    tf.keras.layers.LSTMCell(
	# 						    						n_filters,
	# 						    						activation = 'tanh',
	# 												    recurrent_activation = 'sigmoid',
	# 												    # use_bias = False,
	# 												    # bias_regularizer = tf.keras.regularizers.L1L2(l1 = 1.5e-2, l2 = 1.5e-2)
	# 						    						),
	# 						    return_sequences = True,
	# 						    return_state = False,
	# 						    stateful = True,
	# 						)(z)

	# z = tf.keras.layers.Dropout(0.8)(z)

	z = tf.keras.layers.Dropout(0.1)(z)									

	Y_preds = tf.keras.layers.SeparableConv1D(
												filters = 1, 
												kernel_size = 5,
												padding = 'causal',
												depth_multiplier = 50,
												# kernel_regularizer = kernel_regularizer,
												# activity_regularizer = activity_regularizer,
												bias_initializer="glorot_uniform",
												# bias_regularizer = tf.keras.regularizers.L1(60),
												# use_bias = False,
												)(z)

	model = tf.keras.Model(inputs = [inputs], outputs = [Y_preds])

	return model

#****************************************************************************************************
from tensorflow.python.util.tf_export import keras_export
#from keras.utils import losses_utils
#from keras.dtensor import utils as dtensor_utils
from keras.losses import mean_absolute_error
from keras.metrics import Metric

# Custom Loss MAE: *********************************************
@keras_export("keras.losses.MeanAbsoluteError")
class CustomLossMAE(tf.keras.losses.Loss):

	def __init__(
				self, 
				name = "custom_lose_mae",  
				#reduction = losses_utils.ReductionV2.AUTO, 
				window_size = 500, 
				size_target = 10
				):

		super(CustomLossMAE, self).__init__(name = name)#, reduction = reduction)
		self.window_size = window_size
		self.size_target = size_target
		#self.reduction = reduction

	def call(self, y_true, y_pred):

		weight_face = (self.window_size - (2 * self.size_target))
		weight_face = weight_face/(self.window_size)

		weight_ass = ((self.window_size - self.size_target) * 2)/self.window_size

		mae = tf.keras.losses.MeanAbsoluteError()
		mae_target = mae(y_true[: , self.window_size - self.size_target :], y_pred[: , self.window_size - self.size_target :])
		mae_total = mae(y_true, y_pred)
		mae_qual = ((mae_target * weight_face) + mae_total)/(weight_ass)
		loss = mae_qual
		#/////////////
		return loss
#///////////////////////////////////////////////////////////

# Custom Loss MSE: *********************************************
@keras_export("keras.losses.MeanSquaredError")
class CustomLossMSE(tf.keras.losses.Loss):

	def __init__(
				self, 
				name = "custom_lose_mse",  
				#reduction = losses_utils.ReductionV2.AUTO, 
				window_size = 500, 
				size_target = 10
				):

		super(CustomLossMSE, self).__init__(name = name)#, reduction = reduction)
		self.window_size = window_size
		self.size_target = size_target
		#self.reduction = reduction

	def call(self, y_true, y_pred):

		weight_face = (self.window_size - (2 * self.size_target))
		weight_face = weight_face/(self.window_size)

		weight_ass = ((self.window_size - self.size_target) * 2)/self.window_size

		mse = tf.keras.losses.MeanSquaredError()
		mse_target = mse(y_true[: , self.window_size - self.size_target :], y_pred[: , self.window_size - self.size_target :])
		mse_total = mse(y_true, y_pred)
		mse_qual = ((mse_target * weight_face) + mse_total)/(weight_ass)
		loss = mse_qual
		#////////////
		return loss
#///////////////////////////////////////////////////////////

# Custom Loss Huber: *********************************************
@keras_export("keras.losses.Huber")
class CustomLossHuber(tf.keras.losses.Loss):

	def __init__(
				self, 
				name = "custom_lose_huber",  
				#reduction = losses_utils.ReductionV2.AUTO, 
				window_size = 500, 
				size_target = 10
				):

		super(CustomLossHuber, self).__init__(name = name)#, reduction = reduction)
		self.window_size = window_size
		self.size_target = size_target
		#self.reduction = reduction

	def call(self, y_true, y_pred):

		weight_face = (self.window_size - (2 * self.size_target))
		weight_face = weight_face/(self.window_size)

		weight_ass = ((self.window_size - self.size_target) * 2)/self.window_size

		huber = tf.keras.losses.Huber()
		huber_target = huber(y_true[: , self.window_size - self.size_target :], y_pred[: , self.window_size - self.size_target :])
		huber_total = huber(y_true, y_pred)
		huber_qual = ((huber_target * weight_face) + huber_total)/(weight_ass)
		loss = huber_qual
		#///////////
		return loss
#///////////////////////////////////////////////////////////

# Custom Metric MAE: ***************************************
# Custom Loss MAE: *********************************************
@keras_export("keras.metrics.MeanAbsoluteError")
class CustomMAE(Metric):

	#@dtensor_utils.inject_mesh
	def __init__(
				self, 
				name = "custom_metric_mae",  
				window_size = 500, 
				size_target = 10,
				**kwargs
				):

		#super(CustomMAE, self).__init__(mean_absolute_error, name = name, **kwargs)
		super(CustomMAE, self).__init__(name = name, **kwargs)
		self.window_size = window_size
		self.size_target = size_target
		self.mae_tar = tf.keras.metrics.MeanAbsoluteError(name = name + 'target')
		self.mae_tot = tf.keras.metrics.MeanAbsoluteError(name = name + 'total')
		self.mae_target = self.add_weight(name = name, initializer = "ones")

	def update_state(self, y_true, y_pred, sample_weight=None):

		weight_face = (self.window_size - (2 * self.size_target))
		weight_face = weight_face/(self.window_size)

		weight_ass = ((self.window_size - self.size_target) * 2)/self.window_size

		self.mae_tar.update_state(y_true[: , self.window_size - self.size_target :], y_pred[: , self.window_size - self.size_target :])
		self.mae_tot.update_state(y_true, y_pred)
		mae_qual = ((self.mae_tar.result() * weight_face) + self.mae_tot.result())/(weight_ass)

		values = tf.cast(mae_qual, "float32")
		self.mae_target.assign(values)

		return self.mae_target


	def result(self):
		return self.mae_target

	#@dtensor_utils.inject_mesh
	def reset_state(self):
		# The state of the metric will be reset at the start of each epoch.
		self.mae_target.assign(1.0)
		self.mae_tar.reset_states()
		self.mae_tot.reset_states()

#///////////////////////////////////////////////////////////

# Custom Metric MAE Target: ********************************
@keras_export("keras.metrics.MeanAbsoluteError")
class MAETarget(Metric):

	#@dtensor_utils.inject_mesh
	def __init__(self, name = "mae_target", window_size = 500, size_target = 10, **kwargs):

		#super(MAETarget, self).__init__(mean_absolute_error, name = name, dtype = dtype)
		super(MAETarget, self).__init__(name = name, **kwargs)

		self.window_size = window_size
		self.size_target = size_target
		self.mae = tf.keras.metrics.MeanAbsoluteError(name = name)
		self.mae_target = self.add_weight(name = name, initializer = "ones")


	def update_state(self, y_true, y_pred, sample_weight=None):

		self.mae.update_state(
								y_true[: , self.window_size - self.size_target :], 
								y_pred[: , self.window_size - self.size_target :],
								sample_weight = sample_weight
								)

		values = tf.cast(self.mae.result(), "float32")
		self.mae_target.assign(values)

		return self.mae_target


	def result(self):
		return self.mae_target

	#@dtensor_utils.inject_mesh
	def reset_state(self):
		# The state of the metric will be reset at the start of each epoch.
		self.mae_target.assign(1.0)
		self.mae.reset_states()
#///////////////////////////////////////////////////////////

# Custom Metric MAPE: ***************************************
@keras_export("keras.metrics.MeanAbsoluteError")
class MAPETarget(Metric):

	#@dtensor_utils.inject_mesh
	def __init__(self, name = "mape_target", window_size = 500, size_target = 10, **kwargs):

		#super(MAPETarget, self).__init__(mean_absolute_error, name = name, dtype = dtype)
		super(MAPETarget, self).__init__(name = name, **kwargs)
		
		self.window_size = window_size
		self.size_target = size_target
		self.mae = tf.keras.metrics.MeanAbsoluteError(name = name)
		self.mape_target = self.add_weight(name = name, initializer = "ones")

	def update_state(self, y_true, y_pred, sample_weight = None):

		self.mae.update_state(
								y_true[: , self.window_size - self.size_target :], 
								y_pred[: , self.window_size - self.size_target :], 
								sample_weight = sample_weight
								)

		values = tf.cast(self.mae.result() * 11.11111111111111111111111111111111111111111, "float32")
		self.mape_target.assign(values)

		return self.mape_target

	def result(self):
		return self.mape_target

	#@dtensor_utils.inject_mesh
	def reset_state(self):
		# The state of the metric will be reset at the start of each epoch.
		self.mape_target.assign(1.0)
		self.mae.reset_states()
#///////////////////////////////////////////////////////////

#Reset States: ********************************************

class ResetStatesCallback(tf.keras.callbacks.Callback):
    def on_train_begin(self, logs=None):
    	self.model.reset_states()
    	print()
    	print('Train Model Reset States ...')
    	print()

    def on_test_begin(self, logs=None):
    	self.model.reset_states()
    	print()
    	print('Test Model Reset States ...')
    	print()

    def on_epoch_begin(self, epoch, logs=None):
    	self.model.reset_states()
    	print()
    	print('Epoch Start Model Reset States ...')
    	print()

    def on_epoch_end(self, epoch, logs=None):
    	self.model.reset_states()
    	print()
    	print('Epoch End Model Reset States ...')
    	print()

#//////////////////////////////////////////////////////////

# learning_rate = 1.5e-5 #2.5e-4 # 1.5e-5 #2.5e-4
# optimizer = tf.keras.optimizers.Adam(learning_rate = learning_rate)

# model.compile(
# 				optimizer = optimizer,
#               	loss = [
#               			CustomLossHuber(name = "custom_loss_huber", window_size = window_size, size_target = size_target),
#               			CustomLossMAE(name = "custom_loss_mae", window_size = window_size, size_target = size_target),
#               			CustomLossMSE(name = "custom_loss_mse", window_size = window_size, size_target = size_target),
#               			],
#               	loss_weights = [90, 1.1111111, 9],
#              	metrics = [
#              				'mse', 
#              				'mae', 
#              				MAETarget(name = "mae_target", window_size = window_size, size_target = size_target),
#              				MAPETarget(name = "mape_target", window_size = window_size, size_target = size_target)
#              				],
#              )
# # model.summary()

# tf.keras.utils.plot_model(
# 						model, 
# 						show_shapes = True, 
# 						to_file = 'model_' + feature_names_str + '.png'
# 						)

# EPOCHS = 5

# model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
# 														'model_' + feature_names_str + '_' + timeframe + '.h5', 
# 														save_best_only = True,
# 														save_weights_only = False,
# 														monitor = 'val_mae',
#     													mode = 'min',
#     													verbose = 1
# 														)

# early_stopping = tf.keras.callbacks.EarlyStopping(patience = 50)

if os.path.exists('TensorBoard'):
	print('****************************** Exist ******************************')
	shutil.rmtree('TensorBoard')

tensor_board = tf.keras.callbacks.TensorBoard(
											log_dir = 'TensorBoard', 
											histogram_freq = 1
											)
# python.exe C:\\Users\\Mehrshad\\AppData\\Roaming\\Python\\Python38\\site-packages\\tensorboard\\main.py --logdir=C:\\Users\\Mehrshad\\Desktop\\ShadBotTrader\\TensorBoard

# model.evaluate(x = dataset_valid, batch_size = 1)

# history = model.fit(
# 				    x = dataset_train,
# 				    epochs = EPOCHS,
# 				    validation_data = dataset_valid, 
# 				    callbacks = [model_checkpoint, early_stopping, tensor_board]#, ResetStatesCallback()]
# 					)



#/////////////////////////////////////////////////////////////////////////////////////////////

#****************************************************************************************************

if os.path.exists('model_' + feature_names_str + '_' + timeframe + '.h5'):
	print('model_' + feature_names_str + '_' + timeframe + '.h5')
	model = tf.keras.models.load_model(
										'model_' + feature_names_str + '_' + timeframe + '.h5',
										custom_objects = {
															'GatedActivationUnit': GatedActivationUnit(),
															'CustomLossHuber': CustomLossHuber(name = "custom_loss_huber", window_size = window_size, size_target = size_target),
															'CustomLossMAE': CustomLossMAE(name = "custom_loss_mae", window_size = window_size, size_target = size_target),
															'CustomLossMSE': CustomLossMSE(name = "custom_loss_mse", window_size = window_size, size_target = size_target),
															'CustomMAE': CustomMAE(name = "custom_mae", window_size = window_size, size_target = size_target),
															'MAETarget': MAETarget(name = "mae_target", window_size = window_size, size_target = size_target),
															'MAPETarget': MAPETarget(name = "mape_target", window_size = window_size, size_target = size_target),
														}
										)
	model.trainable = True

else:
	model = Model_Creator()

	tf.keras.utils.plot_model(
							model, 
							show_shapes = True, 
							to_file = 'model_' + feature_names_str + '.png'
							)

model.summary()

#*****************************************
# Window Size = 500 learning rates:

learning_rate = 2.5e-5
# learning_rate = 1.5e-5
# learning_rate = 2.5e-07
#////////////////////////////////////////////////

#*****************************************
# Window Size = 1000 learning rates:

# learning_rate = 3.9e-4
# learning_rate = 0.00015109399391803892
#////////////////////////////////////////////////

reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
												    monitor = "val_loss",
												    factor = 0.9,
												    patience = 30,
												    verbose = 1,
												    mode = "min",
												    min_delta = 0.0001,
												    cooldown = 1,
												    min_lr = 2.5e-7,
												)
optimizer = tf.keras.optimizers.experimental.AdamW(learning_rate = learning_rate) # val_mae: 0.0125 - val_mae_target: 0.0158

# lr_schedule = tf.keras.callbacks.LearningRateScheduler(lambda epoch: 1e-8 * 10**(epoch / 10))
# optimizer = tf.keras.optimizers.experimental.AdamW(learning_rate = 1e-8)

model.compile(
				optimizer = optimizer,
              	loss = [
              			CustomLossHuber(name = "custom_loss_huber", window_size = window_size, size_target = size_target),
              			CustomLossMAE(name = "custom_loss_mae", window_size = window_size, size_target = size_target),
              			CustomLossMSE(name = "custom_loss_mse", window_size = window_size, size_target = size_target),
              			],
              	loss_weights = [30.0, 60.0, 10.0],
              	# loss_weights = [diff_max_min],#, 9],
             	metrics = [
             				'mse', 
             				'mae', 
             				CustomMAE(name = "custom_mae", window_size = window_size, size_target = size_target),
             				MAETarget(name = "mae_target", window_size = window_size, size_target = size_target),
             				MAPETarget(name = "mape_target", window_size = window_size, size_target = size_target),
             				],
             )

# evaluate_history = model.evaluate(x = dataset_test, batch_size = 1)
#evaluate_history = model.evaluate(x = dataset_test, batch_size = Batch_Size)

EPOCHS = 1000

# model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
# 														'model_' + feature_names_str + '_' + timeframe + '.h5', 
# 														save_best_only = True,
# 														save_weights_only = False,
# 														monitor = 'val_custom_mae',
#     													mode = 'min',
#     													verbose = 1,
#     													initial_value_threshold = evaluate_history[3],
# 														)

early_stopping = tf.keras.callbacks.EarlyStopping(patience = 200)

# history = model.fit(
# 				    dataset_train,
# 				    epochs = EPOCHS,
# 				    validation_data = dataset_test,
# 				    callbacks = [lr_schedule, tensor_board]
# 					)

# history = model.fit(
# 				    x = dataset_train,
# 				    epochs = EPOCHS,
# 				    shuffle = False,
# 				    # steps_per_epoch = total_train,
# 				    validation_data = dataset_test, 
# 				    # validation_steps = total_valid,
# 				    callbacks = [model_checkpoint, early_stopping, tensor_board, reduce_lr],#, ResetStatesCallback()]
#             # use_multiprocessing = True,
#             # workers = 100,
# 					)

# sys.exit()
#/////////////////////////////////////////////////////////////////////////////////////////////

#****************************************************************************************************
model_high = tf.keras.models.load_model(
										'model_All_feature_price_sin_high_1D.h5',
										custom_objects = {
															'GatedActivationUnit': GatedActivationUnit(),
															'CustomLossHuber': CustomLossHuber(name = "custom_loss_huber", window_size = window_size, size_target = size_target),
															'CustomLossMAE': CustomLossMAE(name = "custom_loss_mae", window_size = window_size, size_target = size_target),
															'CustomLossMSE': CustomLossMSE(name = "custom_loss_mse", window_size = window_size, size_target = size_target),
															'CustomMAE': CustomMAE(name = "custom_mae", window_size = window_size, size_target = size_target),
															'MAETarget': MAETarget(name = "mae_target", window_size = window_size, size_target = size_target),
															'MAPETarget': MAPETarget(name = "mape_target", window_size = window_size, size_target = size_target),
															}
										)

model_low = tf.keras.models.load_model(
										'model_' + feature_names_str + '_' + timeframe + '.h5',
										custom_objects = {
															'GatedActivationUnit': GatedActivationUnit(),
															'CustomLossHuber': CustomLossHuber(name = "custom_loss_huber", window_size = window_size, size_target = size_target),
															'CustomLossMAE': CustomLossMAE(name = "custom_loss_mae", window_size = window_size, size_target = size_target),
															'CustomLossMSE': CustomLossMSE(name = "custom_loss_mse", window_size = window_size, size_target = size_target),
															'CustomMAE': CustomMAE(name = "custom_mae", window_size = window_size, size_target = size_target),
															'MAETarget': MAETarget(name = "mae_target", window_size = window_size, size_target = size_target),
															'MAPETarget': MAPETarget(name = "mape_target", window_size = window_size, size_target = size_target),
														}
										)

model_high.compile(
					optimizer = optimizer,
	              	loss = [
	              			CustomLossHuber(name = "custom_loss_huber", window_size = window_size, size_target = size_target),
	              			CustomLossMAE(name = "custom_loss_mae", window_size = window_size, size_target = size_target),
	              			CustomLossMSE(name = "custom_loss_mse", window_size = window_size, size_target = size_target),
	              			],
	              	loss_weights = [30.0, 60.0, 10.0],
	              	# loss_weights = [diff_max_min],#, 9],
	             	metrics = [
	             				'mse', 
	             				'mae', 
	             				CustomMAE(name = "custom_mae", window_size = window_size, size_target = size_target),
	             				MAETarget(name = "mae_target", window_size = window_size, size_target = size_target),
	             				MAPETarget(name = "mape_target", window_size = window_size, size_target = size_target),
	             				],
	             )

model_low.compile(
					optimizer = optimizer,
	              	loss = [
	              			CustomLossHuber(name = "custom_loss_huber", window_size = window_size, size_target = size_target),
	              			CustomLossMAE(name = "custom_loss_mae", window_size = window_size, size_target = size_target),
	              			CustomLossMSE(name = "custom_loss_mse", window_size = window_size, size_target = size_target),
	              			],
	              	loss_weights = [30.0, 60.0, 10.0],
	              	# loss_weights = [diff_max_min],#, 9],
	             	metrics = [
	             				'mse', 
	             				'mae', 
	             				CustomMAE(name = "custom_mae", window_size = window_size, size_target = size_target),
	             				MAETarget(name = "mae_target", window_size = window_size, size_target = size_target),
	             				MAPETarget(name = "mape_target", window_size = window_size, size_target = size_target),
	             				],
	             )

def window_dataset_predict(
							series, 
							window_size = 200, 
							batch_size = 1,
							shift = 1,
							target_name = 'close',
							size_target = 12,
							feature_names = [],
							feature_names_shouldnt_scale = []
							):

	dataset = to_windows(tf.data.Dataset.from_tensor_slices(series), 1, shift)
	dataset = to_windows(dataset, window_size, shift)


	target = np.where(series.columns == target_name)[0][0]
	feature_names_copy = feature_names.copy()
	#feature_names_copy.remove(target_name)
	feature_names_list = []

	for elm in feature_names_copy:
		feature_names_list.append(np.where(series.columns == elm)[0][0])

	feature_names_shouldnt_scale_list = []

	for elm in feature_names_shouldnt_scale:
		
		if elm in series.columns:
			feature_names_shouldnt_scale_list.append(np.where(series.columns == elm)[0][0])

	# @tf.function
	def MinMax_Feature(dataset, feature_names_list, size_target, feature_names_shouldnt_scale_list):

		input_list = []

		for feat in feature_names_list:

			if (feat in feature_names_shouldnt_scale_list):

				input_list.append(
									tf.cast(
											(
												(
													dataset[: , 0 , feat]
												) * 4.0
											) - 2.0,
											tf.float64
											)
								)
			else:

				input_list.append(
									tf.cast(
												(
													(
														(dataset[: , 0 , feat] - tf.math.reduce_min(dataset[: , 0 , feat]))/
														(tf.math.reduce_max(dataset[: , 0 , feat]) - tf.math.reduce_min(dataset[: , 0 , feat]))
													) * 4.0
												) - 2.0,
											tf.float64
											)
								)

		# (tf.math.reduce_max(dataset[: , 0 , feat]) - tf.math.reduce_min(dataset[: , 0 , feat]))

		input_list = tf.transpose(input_list)
		input_model = tf.stack(input_list)
		return input_model

	dataset = dataset.map(
							lambda window: (
											MinMax_Feature(
															dataset = window, 
															feature_names_list = feature_names_list, 
															size_target = size_target,
															feature_names_shouldnt_scale_list = feature_names_shouldnt_scale_list
															)
											)
							)

	dataset = dataset.batch(batch_size).prefetch(1)


	# target = np.where(series.columns == 'close')[0][0]
	# import matplotlib.pyplot as plt
	# counter = 0
	# for x in dataset:
	# 	print("x = ", x.numpy())
	# 	print('shape x = ', tf.shape(x))
	# 	figure, (ax0, ax1) = plt.subplots(2, 1)
	# 	ax0.plot(x[0, : , target].numpy(), c = 'b')

	# 	print(series['close'][counter: window_size + counter])

	# 	ax1.plot(range(0, int(window_size/2)),series['close'][counter: int(window_size/2) + counter] , c = 'orange', linestyle = '--')
		
		
	# 	print()
	# 	print('////////////////////////////////')
	# 	counter += shift
		
	# 	plt.show()

	return dataset

import matplotlib.pyplot as plt

# test_feature_engineering_5M = feature_engineering_5M.loc[int(total * 0.91) :]
# test_feature_engineering_5M = test_feature_engineering_5M

print('len = ', len(test_feature_engineering_5M_high.columns))

data_evaluate_high = to_seq2seq_dataset(
									series = test_feature_engineering_5M_high, 
									window_size = window_size, 
									batch_size = Batch_Size, 
									shuffle = False, 
									seed = 42,
									size_target = size_target,
									shift = shift, 
									target_name = 'high',
									target_type = 'price_sin_high',
									feature_names = feature_names_high,
									feature_names_shouldnt_scale = feature_names_shouldnt_scale
									)

data_evaluate_low = to_seq2seq_dataset(
									series = test_feature_engineering_5M_low, 
									window_size = window_size, 
									batch_size = Batch_Size, 
									shuffle = False, 
									seed = 42,
									size_target = size_target,
									shift = shift, 
									target_name = 'low',
									target_type = 'price_sin_low',
									feature_names = feature_names_low,
									feature_names_shouldnt_scale = feature_names_shouldnt_scale
									)

model_high.evaluate(x = data_evaluate_high, batch_size = Batch_Size)
model_low.evaluate(x = data_evaluate_low, batch_size = Batch_Size)

i = test_feature_engineering_5M.index[0]

output = pd.DataFrame(columns = [
									'mape_real_price_high', 
									'mape_real_price_low', 
									'mape_percent_price_high', 
									'mape_percent_price_low', 
									])

while i <= test_feature_engineering_5M.index[-1] - size_target:

	data_predict_high = window_dataset_predict(
											series = test_feature_engineering_5M_high.loc[i : i + window_size], 
											window_size = window_size, 
											batch_size = 1,
											size_target = size_target,
											shift = 1,
											target_name = 'high',
											feature_names = feature_names_high,
											feature_names_shouldnt_scale = feature_names_shouldnt_scale
											)

	data_predict_low = window_dataset_predict(
											series = test_feature_engineering_5M_low.loc[i : i + window_size], 
											window_size = window_size, 
											batch_size = 1,
											size_target = size_target,
											shift = 1,
											target_name = 'low',
											feature_names = feature_names_low,
											feature_names_shouldnt_scale = feature_names_shouldnt_scale
											)

	print(i + window_size)

	predict_serie_high = model_high.predict(data_predict_high)
	predict_serie_low = model_low.predict(data_predict_low)

	# print(predict_serie_high)
	# print(tf.shape(predict_serie_high))

	dataset_scaled_total_5M = pd.DataFrame(
											(
						                     ((dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + (window_size + size_target)]) - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + (window_size + size_target)].min())/
						                     (dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + (window_size + size_target)].max() - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + (window_size + size_target)].min())
						                    ),
											columns = ['close']
											)

	dataset_scaled_5M = pd.DataFrame(
										(
					                     ((dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + window_size]) - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + window_size].min())/
					                     (dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + window_size].max() - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + window_size].min())
					                    ),
										columns = ['close']
										)

	percent_change = pd.DataFrame()
	percent_change['none'] = range(0, size_target)

	# percent_change_first = pd.DataFrame()
	# percent_change_first['none'] = range(0, 500)
	# percent_change_first['predict_high_1'] = np.nan
	# percent_change_first['predict_high_2'] = np.nan
	# percent_change_first['predict_high_3'] = np.nan
	# percent_change_first['predict_high_4'] = np.nan
	# percent_change_first['predict_high_5'] = np.nan
	# percent_change_first['predict_high_6'] = np.nan
	# percent_change_first['predict_high_7'] = np.nan
	# percent_change_first['predict_high_8'] = np.nan

	# percent_change_first['error_high_1'] = np.nan
	# percent_change_first['error_high_2'] = np.nan
	# percent_change_first['error_high_3'] = np.nan
	# percent_change_first['error_high_4'] = np.nan
	# percent_change_first['error_high_5'] = np.nan
	# percent_change_first['error_high_6'] = np.nan
	# percent_change_first['error_high_7'] = np.nan
	# percent_change_first['error_high_8'] = np.nan

	# percent_change_first['abs_error_high_1'] = np.nan
	# percent_change_first['abs_error_high_2'] = np.nan
	# percent_change_first['abs_error_high_3'] = np.nan
	# percent_change_first['abs_error_high_4'] = np.nan
	# percent_change_first['abs_error_high_5'] = np.nan
	# percent_change_first['abs_error_high_6'] = np.nan
	# percent_change_first['abs_error_high_7'] = np.nan
	# percent_change_first['abs_error_high_8'] = np.nan

	# percent_change_first['predict_low_1'] = np.nan
	# percent_change_first['predict_low_2'] = np.nan
	# percent_change_first['predict_low_3'] = np.nan
	# percent_change_first['predict_low_4'] = np.nan
	# percent_change_first['predict_low_5'] = np.nan
	# percent_change_first['predict_low_6'] = np.nan
	# percent_change_first['predict_low_7'] = np.nan
	# percent_change_first['predict_low_8'] = np.nan

	# percent_change_first['error_low_1'] = np.nan
	# percent_change_first['error_low_2'] = np.nan
	# percent_change_first['error_low_3'] = np.nan
	# percent_change_first['error_low_4'] = np.nan
	# percent_change_first['error_low_5'] = np.nan
	# percent_change_first['error_low_6'] = np.nan
	# percent_change_first['error_low_7'] = np.nan
	# percent_change_first['error_low_8'] = np.nan

	# percent_change_first['abs_error_low_1'] = np.nan
	# percent_change_first['abs_error_low_2'] = np.nan
	# percent_change_first['abs_error_low_3'] = np.nan
	# percent_change_first['abs_error_low_4'] = np.nan
	# percent_change_first['abs_error_low_5'] = np.nan
	# percent_change_first['abs_error_low_6'] = np.nan
	# percent_change_first['abs_error_low_7'] = np.nan
	# percent_change_first['abs_error_low_8'] = np.nan

	# percent_change_first = percent_change_first.assign(
	# 													valid_high = dataset_5M['high'][i: i + window_size].values,
	# 													valid_low = dataset_5M['low'][i: i + window_size].values,
	# 													)

	# percent_change_first['predict_high_1'][1 : window_size] = ((predict_serie_high[-1, 0 : window_size - 1, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()
	# percent_change_first['predict_high_2'][2 : window_size] = ((predict_serie_high[-1, 0 : window_size - 2, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()
	# percent_change_first['predict_high_3'][3 : window_size] = ((predict_serie_high[-1, 0 : window_size - 3, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()
	# percent_change_first['predict_high_4'][4 : window_size] = ((predict_serie_high[-1, 0 : window_size - 4, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()
	# percent_change_first['predict_high_5'][5 : window_size] = ((predict_serie_high[-1, 0 : window_size - 5, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()
	# percent_change_first['predict_high_6'][6 : window_size] = ((predict_serie_high[-1, 0 : window_size - 6, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()
	# percent_change_first['predict_high_7'][7 : window_size] = ((predict_serie_high[-1, 0 : window_size - 7, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()
	# percent_change_first['predict_high_8'][8 : window_size] = ((predict_serie_high[-1, 0 : window_size - 8, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min()

	# percent_change_first['error_high_1'][1 : window_size] = dataset_5M['high'][i + 1 : i + window_size].values - percent_change_first['predict_high_1'].dropna().values
	# percent_change_first['error_high_2'][2 : window_size] = dataset_5M['high'][i + 2 : i + window_size].values - percent_change_first['predict_high_2'].dropna().values
	# percent_change_first['error_high_3'][3 : window_size] = dataset_5M['high'][i + 3 : i + window_size].values - percent_change_first['predict_high_3'].dropna().values
	# percent_change_first['error_high_4'][4 : window_size] = dataset_5M['high'][i + 4 : i + window_size].values - percent_change_first['predict_high_4'].dropna().values
	# percent_change_first['error_high_5'][5 : window_size] = dataset_5M['high'][i + 5 : i + window_size].values - percent_change_first['predict_high_5'].dropna().values
	# percent_change_first['error_high_6'][6 : window_size] = dataset_5M['high'][i + 6 : i + window_size].values - percent_change_first['predict_high_6'].dropna().values
	# percent_change_first['error_high_7'][7 : window_size] = dataset_5M['high'][i + 7 : i + window_size].values - percent_change_first['predict_high_7'].dropna().values
	# percent_change_first['error_high_8'][8 : window_size] = dataset_5M['high'][i + 8 : i + window_size].values - percent_change_first['predict_high_8'].dropna().values

	# percent_change_first['abs_error_high_1'][1 : window_size] = abs(percent_change_first['error_high_1'][1 : window_size])
	# percent_change_first['abs_error_high_2'][2 : window_size] = abs(percent_change_first['error_high_2'][2 : window_size])
	# percent_change_first['abs_error_high_3'][3 : window_size] = abs(percent_change_first['error_high_3'][3 : window_size])
	# percent_change_first['abs_error_high_4'][4 : window_size] = abs(percent_change_first['error_high_4'][4 : window_size])
	# percent_change_first['abs_error_high_5'][5 : window_size] = abs(percent_change_first['error_high_5'][5 : window_size])
	# percent_change_first['abs_error_high_6'][6 : window_size] = abs(percent_change_first['error_high_6'][6 : window_size])
	# percent_change_first['abs_error_high_7'][7 : window_size] = abs(percent_change_first['error_high_7'][7 : window_size])
	# percent_change_first['abs_error_high_8'][8 : window_size] = abs(percent_change_first['error_high_8'][8 : window_size])

	#/////////////////////////

	# percent_change_first['predict_low_1'][1 : window_size] = ((predict_serie_low[-1, 0 : window_size - 1, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()
	# percent_change_first['predict_low_2'][2 : window_size] = ((predict_serie_low[-1, 0 : window_size - 2, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()
	# percent_change_first['predict_low_3'][3 : window_size] = ((predict_serie_low[-1, 0 : window_size - 3, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()
	# percent_change_first['predict_low_4'][4 : window_size] = ((predict_serie_low[-1, 0 : window_size - 4, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()
	# percent_change_first['predict_low_5'][5 : window_size] = ((predict_serie_low[-1, 0 : window_size - 5, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()
	# percent_change_first['predict_low_6'][6 : window_size] = ((predict_serie_low[-1, 0 : window_size - 6, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()
	# percent_change_first['predict_low_7'][7 : window_size] = ((predict_serie_low[-1, 0 : window_size - 7, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()
	# percent_change_first['predict_low_8'][8 : window_size] = ((predict_serie_low[-1, 0 : window_size - 8, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min()

	# percent_change_first['error_low_1'][1 : window_size] = dataset_5M['low'][i + 1 : i + window_size].values - percent_change_first['predict_low_1'].dropna().values
	# percent_change_first['error_low_2'][2 : window_size] = dataset_5M['low'][i + 2 : i + window_size].values - percent_change_first['predict_low_2'].dropna().values
	# percent_change_first['error_low_3'][3 : window_size] = dataset_5M['low'][i + 3 : i + window_size].values - percent_change_first['predict_low_3'].dropna().values
	# percent_change_first['error_low_4'][4 : window_size] = dataset_5M['low'][i + 4 : i + window_size].values - percent_change_first['predict_low_4'].dropna().values
	# percent_change_first['error_low_5'][5 : window_size] = dataset_5M['low'][i + 5 : i + window_size].values - percent_change_first['predict_low_5'].dropna().values
	# percent_change_first['error_low_6'][6 : window_size] = dataset_5M['low'][i + 6 : i + window_size].values - percent_change_first['predict_low_6'].dropna().values
	# percent_change_first['error_low_7'][7 : window_size] = dataset_5M['low'][i + 7 : i + window_size].values - percent_change_first['predict_low_7'].dropna().values
	# percent_change_first['error_low_8'][8 : window_size] = dataset_5M['low'][i + 8 : i + window_size].values - percent_change_first['predict_low_8'].dropna().values

	# percent_change_first['abs_error_low_1'][1 : window_size] = abs(percent_change_first['error_low_1'][1 : window_size])
	# percent_change_first['abs_error_low_2'][2 : window_size] = abs(percent_change_first['error_low_2'][2 : window_size])
	# percent_change_first['abs_error_low_3'][3 : window_size] = abs(percent_change_first['error_low_3'][3 : window_size])
	# percent_change_first['abs_error_low_4'][4 : window_size] = abs(percent_change_first['error_low_4'][4 : window_size])
	# percent_change_first['abs_error_low_5'][5 : window_size] = abs(percent_change_first['error_low_5'][5 : window_size])
	# percent_change_first['abs_error_low_6'][6 : window_size] = abs(percent_change_first['error_low_6'][6 : window_size])
	# percent_change_first['abs_error_low_7'][7 : window_size] = abs(percent_change_first['error_low_7'][7 : window_size])
	# percent_change_first['abs_error_low_8'][8 : window_size] = abs(percent_change_first['error_low_8'][8 : window_size])

	#/////////////////



	# ve_high_1 = percent_change_first['error_high_1'].std()/(size_target//2) 
	# ve_high_2 = percent_change_first['error_high_2'].std()/(size_target//2)
	# ve_high_3 = percent_change_first['error_high_3'].std()/(size_target//2)
	# ve_high_4 = percent_change_first['error_high_4'].std()/(size_target//2)
	# ve_high_5 = percent_change_first['error_high_5'].std()/(size_target//2)
	# ve_high_6 = percent_change_first['error_high_6'].std()/(size_target//2)
	# ve_high_7 = percent_change_first['error_high_7'].std()/(size_target//2)
	# ve_high_8 = percent_change_first['error_high_8'].std()/(size_target//2)

	# vae_high_1 = percent_change_first['abs_error_high_1'].std()/(size_target//2) 
	# vae_high_2 = percent_change_first['abs_error_high_2'].std()/(size_target//2)
	# vae_high_3 = percent_change_first['abs_error_high_3'].std()/(size_target//2)
	# vae_high_4 = percent_change_first['abs_error_high_4'].std()/(size_target//2)
	# vae_high_5 = percent_change_first['abs_error_high_5'].std()/(size_target//2)
	# vae_high_6 = percent_change_first['abs_error_high_6'].std()/(size_target//2)
	# vae_high_7 = percent_change_first['abs_error_high_7'].std()/(size_target//2)
	# vae_high_8 = percent_change_first['abs_error_high_8'].std()/(size_target//2)

	# me_high_1 = percent_change_first['error_high_1'].mean() 
	# me_high_2 = percent_change_first['error_high_2'].mean()
	# me_high_3 = percent_change_first['error_high_3'].mean()
	# me_high_4 = percent_change_first['error_high_4'].mean()
	# me_high_5 = percent_change_first['error_high_5'].mean()
	# me_high_6 = percent_change_first['error_high_6'].mean()
	# me_high_7 = percent_change_first['error_high_7'].mean()
	# me_high_8 = percent_change_first['error_high_8'].mean()

	# mae_high_1 = percent_change_first['abs_error_high_1'].mean() 
	# mae_high_2 = percent_change_first['abs_error_high_2'].mean()
	# mae_high_3 = percent_change_first['abs_error_high_3'].mean()
	# mae_high_4 = percent_change_first['abs_error_high_4'].mean()
	# mae_high_5 = percent_change_first['abs_error_high_5'].mean()
	# mae_high_6 = percent_change_first['abs_error_high_6'].mean()
	# mae_high_7 = percent_change_first['abs_error_high_7'].mean()
	# mae_high_8 = percent_change_first['abs_error_high_8'].mean()


	# ve_low_1 = percent_change_first['error_low_1'].std()/(size_target//2) 
	# ve_low_2 = percent_change_first['error_low_2'].std()/(size_target//2)
	# ve_low_3 = percent_change_first['error_low_3'].std()/(size_target//2)
	# ve_low_4 = percent_change_first['error_low_4'].std()/(size_target//2)
	# ve_low_5 = percent_change_first['error_low_5'].std()/(size_target//2)
	# ve_low_6 = percent_change_first['error_low_6'].std()/(size_target//2)
	# ve_low_7 = percent_change_first['error_low_7'].std()/(size_target//2)
	# ve_low_8 = percent_change_first['error_low_8'].std()/(size_target//2)

	# vae_low_1 = percent_change_first['abs_error_low_1'].std()/(size_target//2) 
	# vae_low_2 = percent_change_first['abs_error_low_2'].std()/(size_target//2)
	# vae_low_3 = percent_change_first['abs_error_low_3'].std()/(size_target//2)
	# vae_low_4 = percent_change_first['abs_error_low_4'].std()/(size_target//2)
	# vae_low_5 = percent_change_first['abs_error_low_5'].std()/(size_target//2)
	# vae_low_6 = percent_change_first['abs_error_low_6'].std()/(size_target//2)
	# vae_low_7 = percent_change_first['abs_error_low_7'].std()/(size_target//2)
	# vae_low_8 = percent_change_first['abs_error_low_8'].std()/(size_target//2)

	# me_low_1 = percent_change_first['error_low_1'].mean() 
	# me_low_2 = percent_change_first['error_low_2'].mean()
	# me_low_3 = percent_change_first['error_low_3'].mean()
	# me_low_4 = percent_change_first['error_low_4'].mean()
	# me_low_5 = percent_change_first['error_low_5'].mean()
	# me_low_6 = percent_change_first['error_low_6'].mean()
	# me_low_7 = percent_change_first['error_low_7'].mean()
	# me_low_8 = percent_change_first['error_low_8'].mean()

	# mae_low_1 = percent_change_first['abs_error_low_1'].mean() 
	# mae_low_2 = percent_change_first['abs_error_low_2'].mean()
	# mae_low_3 = percent_change_first['abs_error_low_3'].mean()
	# mae_low_4 = percent_change_first['abs_error_low_4'].mean()
	# mae_low_5 = percent_change_first['abs_error_low_5'].mean()
	# mae_low_6 = percent_change_first['abs_error_low_6'].mean()
	# mae_low_7 = percent_change_first['abs_error_low_7'].mean()
	# mae_low_8 = percent_change_first['abs_error_low_8'].mean()

	percent_change = percent_change.assign(
					
											valid_high = dataset_5M['high'][i + window_size + 1: i + (window_size + size_target + 1)].values,
											predict_high = ((predict_serie_high[1, window_size - size_target :, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(),

											valid_low = dataset_5M['low'][i + window_size + 1: i + (window_size + size_target + 1)].values,
											predict_low = ((predict_serie_low[1, window_size - size_target :, 0]) * (dataset_5M['low'][i : i + window_size].max() - dataset_5M['low'][i : i + window_size].min())) + dataset_5M['low'][i : i + window_size].min(),
											)

	# percent_change['predict_high'][0] += (mae_high_1 + (vae_high_1 * (me_high_1/abs(me_high_1))) - ve_high_1)
	# percent_change['predict_high'][1] += (mae_high_2 + (vae_high_2 * (me_high_2/abs(me_high_2))) - ve_high_2)
	# percent_change['predict_high'][2] += (mae_high_3 + (vae_high_3 * (me_high_3/abs(me_high_3))) - ve_high_3)
	# percent_change['predict_high'][3] += (mae_high_4 + (vae_high_4 * (me_high_4/abs(me_high_4))) - ve_high_4)
	# percent_change['predict_high'][4] += (mae_high_5 + (vae_high_5 * (me_high_5/abs(me_high_5))) - ve_high_5)
	# percent_change['predict_high'][5] += (mae_high_6 + (vae_high_6 * (me_high_6/abs(me_high_6))) - ve_high_6)
	# percent_change['predict_high'][6] += (mae_high_7 + (vae_high_7 * (me_high_7/abs(me_high_7))) - ve_high_7)
	# percent_change['predict_high'][7] += (mae_high_8 + (vae_high_8 * (me_high_8/abs(me_high_8))) - ve_high_8)

	# percent_change['predict_low'][0] += (mae_low_1 + (vae_low_1 * (me_low_1/abs(me_low_1))) - ve_low_1)
	# percent_change['predict_low'][1] += (mae_low_2 + (vae_low_2 * (me_low_2/abs(me_low_2))) - ve_low_2)
	# percent_change['predict_low'][2] += (mae_low_3 + (vae_low_3 * (me_low_3/abs(me_low_3))) - ve_low_3)
	# percent_change['predict_low'][3] += (mae_low_4 + (vae_low_4 * (me_low_4/abs(me_low_4))) - ve_low_4)
	# percent_change['predict_low'][4] += (mae_low_5 + (vae_low_5 * (me_low_5/abs(me_low_5))) - ve_low_5)
	# percent_change['predict_low'][5] += (mae_low_6 + (vae_low_6 * (me_low_6/abs(me_low_6))) - ve_low_6)
	# percent_change['predict_low'][6] += (mae_low_7 + (vae_low_7 * (me_low_7/abs(me_low_7))) - ve_low_7)
	# percent_change['predict_low'][7] += (mae_low_8 + (vae_low_8 * (me_low_8/abs(me_low_8))) - ve_low_8)

	with pd.option_context('display.max_rows', None, 'display.max_columns', None):
		print('close_now: ', dataset_5M['close'][i])
		print(percent_change.drop(columns = ['none']))

	#Min: ********************************
	mape_real_price_high = np.max(abs((percent_change['predict_high'] - percent_change['valid_high'])/percent_change['valid_high'])) * 100
	mape_real_price_low = np.max(abs((percent_change['predict_low'] - percent_change['valid_low'])/percent_change['valid_low'])) * 100
	#/////////////////////////////

	#Max: *********************************
	# mape_percent_price_high = np.mean(abs((1 + percent_change['predict_high'].pct_change(1).dropna()[0:].values - 1 - percent_change['valid_high'].pct_change(1).dropna()[0:].values)/(1 + percent_change['valid_high'].pct_change(1).dropna()[0:].values))) * 100
	# mape_percent_price_low = np.max(abs((1 + percent_change['predict_low'].pct_change(1).dropna()[0:].values - 1 - percent_change['valid_low'].pct_change(1).dropna()[0:].values)/(1 + percent_change['valid_low'].pct_change(1).dropna()[0:].values))) * 100

	print('MAPE Real Price High = ', mape_real_price_high, ' %')
	print('MAPE Real Price Low = ', mape_real_price_low, ' %')
	# print('MAPE Percent Price High = ', mape_percent_price_high, ' %')
	# print('MAPE Percent Price Low = ', mape_percent_price_low, ' %')

	output = output.append(
							{
							'mape_real_price_high': mape_real_price_high,
							'mape_real_price_low': mape_real_price_low,
							# 'mape_percent_price_high': mape_percent_price_high,
							# 'mape_percent_price_low': mape_percent_price_low,
							},
							ignore_index = True
							)

	if os.path.exists('pics/Timeseries_Test.csv'):
		os.remove('pics/Timeseries_Test.csv')
	output.to_csv('pics/Timeseries_Test.csv')

	print()

	plt.scatter(dataset_5M['high'][i + window_size + 1 : i + (window_size + size_target + 1)].index, dataset_5M['high'][i + window_size + 1 : i + (window_size + size_target + 1)], c = 'b')
	plt.plot(dataset_5M['high'][i + window_size - 10 : ].index, dataset_5M['high'][i + window_size - 10 : ], c = '#1fdbff', linestyle = ':')

	plt.scatter(dataset_5M['low'][i + window_size + 1 : i + (window_size + size_target + 1)].index, dataset_5M['low'][i + window_size + 1 : i + (window_size + size_target + 1)], c = '#7a28a3')
	plt.plot(dataset_5M['low'][i + window_size - 10 : ].index, dataset_5M['low'][i + window_size - 10 : ], c = '#9932cc', linestyle = ':')
	
	plt.axvline(i + window_size, c = 'g', linestyle = '--')
	plt.axvline(i + (window_size + size_target + 1), c = 'black', linestyle = '--')

	plt.scatter(dataset_5M['close'][i + window_size + 1 : i + (window_size + size_target + 1)].index, percent_change['predict_high'].values, c = 'r')
	plt.plot(dataset_5M['close'][i + window_size + 1 : i + (window_size + size_target + 1)].index, percent_change['predict_high'].values, c = '#ffa42b', linestyle = ':')

	plt.scatter(dataset_5M['close'][i + window_size + 1 : i + (window_size + size_target + 1)].index, percent_change['predict_low'].values, c = '#008000')
	plt.plot(dataset_5M['close'][i + window_size + 1 : i + (window_size + size_target + 1)].index, percent_change['predict_low'].values, c = '#008000', linestyle = ':')

	plt.savefig(f'pics/{i}.jpg', dpi = 150, bbox_inches = 'tight')

	# plt.show()

	plt.figure().clear()
	plt.close('all')
	plt.cla()
	plt.clf()

	# plt.scatter(dataset_5M['high'][i : i + (window_size + size_target)].index, dataset_5M['high'][i : i + (window_size + size_target)], c = 'b')
	# plt.plot(dataset_5M['high'][i : i + (window_size + size_target)].index, dataset_5M['high'][i : i + (window_size + size_target)], c = '#1fdbff', linestyle = ':')

	# plt.axvline(i + window_size, c = 'g', linestyle = '--')
	# plt.axvline(i + (window_size + size_target), c = 'black', linestyle = '--')

	# plt.scatter(dataset_5M['close'][i + 1 : i + (window_size + 1)].index, ((predict_serie_high[-1, :, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), c = 'r')
	# plt.plot(dataset_5M['close'][i + 1 : i + (window_size + 1)].index, ((predict_serie_high[-1, :, 0]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), c = '#ffa42b', linestyle = ':')

	# plt.scatter(dataset_5M['close'][i + 2 : i + (window_size+ 2)].index, ((predict_serie_high[-1, :, 1]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min())
	# plt.plot(dataset_5M['close'][i + 2 : i + (window_size+ 2)].index, ((predict_serie_high[-1, :, 1]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), linestyle = ':')

	# plt.scatter(dataset_5M['close'][i + 3 : i + (window_size + 3)].index, ((predict_serie_high[-1, :, 2]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min())
	# plt.plot(dataset_5M['close'][i + 3 : i + (window_size + 3)].index, ((predict_serie_high[-1, :, 2]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), linestyle = ':')

	# plt.scatter(dataset_5M['close'][i + 4 : i + (window_size + 4)].index, ((predict_serie_high[-1, :, 3]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min())
	# plt.plot(dataset_5M['close'][i + 4: i + (window_size + 4)].index, ((predict_serie_high[-1, :, 3]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), linestyle = ':')

	# plt.scatter(dataset_5M['close'][i + 5 : i + (window_size + 5)].index, ((predict_serie_high[-1, :, 4]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min())
	# plt.plot(dataset_5M['close'][i + 5 : i + (window_size + 5)].index, ((predict_serie_high[-1, :, 4]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), linestyle = ':')

	# plt.scatter(dataset_5M['close'][i + 6 : i + (window_size + 6)].index, ((predict_serie_high[-1, :, 5]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min())
	# plt.plot(dataset_5M['close'][i + 6 : i + (window_size + 6)].index, ((predict_serie_high[-1, :, 5]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), linestyle = ':')

	# plt.scatter(dataset_5M['close'][i + 7 : i + (window_size + 7)].index, ((predict_serie_high[-1, :, 6]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min())
	# plt.plot(dataset_5M['close'][i + 7 : i + (window_size + 7)].index, ((predict_serie_high[-1, :, 6]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), linestyle = ':')
	
	# plt.scatter(dataset_5M['close'][i + 8 : i + (window_size + 8)].index, ((predict_serie_high[-1, :, 7]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min())
	# plt.plot(dataset_5M['close'][i + 8 : i + (window_size + 8)].index, ((predict_serie_high[-1, :, 7]) * (dataset_5M['high'][i : i + window_size].max() - dataset_5M['high'][i : i + window_size].min())) + dataset_5M['high'][i : i + window_size].min(), linestyle = ':')
	
	# plt.show()
	print('i = ', i)

	i += 1

dataset_scaled_5M = pd.DataFrame(dataset_5M['close'][len(dataset_5M['close'].index)-1000: ], columns = ['close'])

# print(dataset_scaled_5M)
# print(dataset_scaled_5M['close'].index[-1])
# print(dataset_scaled_5M['close'].loc[(dataset_scaled_5M.index[-1]-100):].values)
percent_change = pd.DataFrame()
percent_change['valid'] = [0]
percent_change['predict']  = [0]
percent_change['valid'] = np.max(((dataset_scaled_5M['close'].loc[(dataset_scaled_5M.index[-1]-100):].values - dataset_scaled_5M['close'].iloc[-100])/dataset_scaled_5M['close'].iloc[-100]) * 100) + 1
percent_change['predict'] = predict_serie[-1, -1, 0]

print(percent_change)

mape = np.mean(abs(abs(percent_change['valid']) - abs(percent_change['predict']))/abs(percent_change['valid'])) * 100

print('mape = ', mape)



sys.exit()