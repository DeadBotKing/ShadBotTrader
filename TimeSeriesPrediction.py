import pandas as pd
import tensorflow as tf
import tensorflow_transform as tft
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
import os

logger = tf.get_logger()
logger.setLevel(logging.ERROR)

tf.random.set_seed(50)
np.random.seed(50)

def window_dataset(
					series, 
					window_size = 200,
					size_target = 12,
					shift = 1, 
					target_name = 'close',
					target_type = 'max',
					feature_names = [],
					feature_names_shouldnt_scale = [],
					batch_size = 32,
					shuffle = False
					):

	dataset = tf.data.Dataset.from_tensor_slices(series)
	dataset = dataset.window(int(window_size ) + 1, shift = shift, drop_remainder=True)
	dataset = dataset.flat_map(lambda window: window.batch(int(window_size ) + 1))

	if shuffle == True:
		dataset = dataset.shuffle(1000)

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

	@tf.function
	def MinMax_Feature(dataset, feature_names_list, feature_names_shouldnt_scale_list):
		
		input_list = []

		for feat in feature_names_list:
			
			if False:#(feat in feature_names_shouldnt_scale_list ):

				input_list.append(
									tf.cast(
											dataset[ : -(size_target + 1), feat],
											tf.float64
											)
								)
			
			else:

				input_list.append(
								(((dataset[ : -(size_target + 1) , feat] - tf.math.reduce_min(dataset[ : -(size_target + 1) , feat]))/
								(tf.math.reduce_max(dataset[ : -(size_target + 1) , feat]) - tf.math.reduce_min(dataset[ : -(size_target + 1) , feat]))) * 4) - 2
								)

		input_list = tf.transpose(input_list)
		input_model = tf.stack(input_list)
		return input_model

	@tf.function
	def MinMax_Target(dataset, target, target_type, feature_names_shouldnt_scale_list):
		
		input_list_1 = []
		input_list_2 = []
		output_list = []

		input_list_1.append(dataset[ : , target])
							# (((dataset[ : , target] ) - tf.math.reduce_min(dataset[ : , target]))/
							# (tf.math.reduce_max(dataset[ : , target]) - tf.math.reduce_min(dataset[ : , target])))
							# )

		input_list_1 = tf.transpose(input_list_1)
		input_list_1 = tf.stack(input_list_1)

		input_list_2.append(
							((((input_list_1[500 : -1, target] - input_list_1[499, target])/input_list_1[499, target])) + 0.5)
							)

		if target_type == 'max':
			output_list.append(tf.math.reduce_max(input_list_2))

		if target_type == 'min':
			output_list.append(tf.math.reduce_min(input_list_2))

		if target_type == 'mean':
			output_list.append(tf.math.reduce_mean(input_list_2))

		output_list = tf.transpose(output_list)
		target_out = tf.stack(output_list)
		return target_out

	dataset = dataset.map(
							lambda window: (
											MinMax_Feature(
															dataset = window, 
															feature_names_list = feature_names_list, 
															feature_names_shouldnt_scale_list = feature_names_shouldnt_scale_list,
															), 
											MinMax_Target(
															dataset = window, 
															target = target,
															target_type = target_type,
															feature_names_shouldnt_scale_list = feature_names_shouldnt_scale_list
															)
											)
							)

	# counter = 0
	# import matplotlib.pyplot as plt
	# for x, y in dataset:
	# 	# for elm in x[0].numpy():
	# 	# 	print('elm = ', elm)
	# 	# print('elm = ', elm)
	# 	if counter >= 99:
	# 		# for elm in x:
	# 		# 	print(tf.math.is_inf(elm))
	# 		print('counter = ', counter)
	# 		plt.plot(x.numpy())
	# 		plt.axhline(y.numpy(), linestyle = '--', c = 'black')
	# 		plt.show()
	# 		print('x = ', x.numpy())
	# 		print('y = ', y.numpy())
	# 		# print()
	# 		# print('***********************************')
	# 		print('shape x = ', tf.shape(x))
	# 		print('shape y = ', tf.shape(y))
			
	# 		# print()
	# 	counter += 1
		# break

	
	dataset = dataset.batch(batch_size).prefetch(1)

	return dataset

loging = getdata()

symbol = 'XAUUSD_i'

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = symbol, number_5M = 'all', number_15M = 0, number_1H = 1)
dataset_5M = dataset_5M[symbol]
dataset_15M = pd.DataFrame()#dataset_15M[symbol]
dataset_1H = pd.DataFrame()#dataset_1H[symbol]


feature_engineering = FeatureEngineering()

_, _, feature_engineering_5M = feature_engineering(
                                                    dataset_5M = dataset_5M, 
                                                    dataset_15M = dataset_15M, 
                                                    dataset_1H = dataset_1H, 
                                                    symbol = symbol, 
                                                    mode = None, 
                                                    scale = False
                                                    )

if 'time' in feature_engineering_5M.columns and symbol in feature_engineering_5M.columns:
	feature_engineering_5M = feature_engineering_5M.drop(columns = ['time', symbol])
	feature_engineering_5M = feature_engineering_5M.drop(columns = [
																	'pattern_week', 
																	'number',
																	'pattern_day',
																	'color_candle'
																	])

# feature_engineering_5M['close_return_100_1'] = feature_engineering_5M['close'].pct_change(100).fillna(method = 'bfill', axis = 0).fillna(0)

target_name = 'low'
target_type = 'min'
timeframe = '1H'
window_size = 512
size_target = 12
shift = 1

percent_feature_names = []
for clm in feature_engineering_5M.columns:
	if 'target' in clm:
		percent_feature_names.append(clm)
	if 'return' in clm:
		percent_feature_names.append(clm)

feature_names = []
# feature_names.extend(price_feature_names)
# feature_names.append(target_name)
# feature_names_str = 'price_feature_' + target_type

# feature_names.extend(oscilator_feature_names)
# feature_names.append(target_name)
# feature_names_str = 'oscilator_feature_' + target_type

# feature_names.extend(pca_feature_names)
# feature_names.append(target_name)
# feature_names_str = 'pca_feature_' + target_type

# feature_names.extend(fourier_feature_names)
# feature_names.append(target_name)
# feature_names_str = 'fourier_feature_' + target_type

# feature_names.extend(percent_feature_names)
# feature_names.append(target_name)
# feature_names_str = 'percent_feature_' + target_type

feature_names.append(target_name)
feature_names.extend(feature_engineering_5M.columns)
feature_names_str = 'All_feature_' + target_type

feature_names_shouldnt_scale = []
feature_names_shouldnt_scale.extend(percent_feature_names)

print()
print()
print('**********************************')
# print('price = ', len(price_feature_names))
# print('oscilator = ', len(oscilator_feature_names))
# print('pca = ', len(pca_feature_names))
# print('fourier = ', len(fourier_feature_names))
# print('percent = ', len(percent_feature_names))
print('percent_price = ', len(feature_engineering_5M.columns))
print(feature_engineering_5M.columns)
print('//////////////////////////////////')
print()
print()



# feature_engineering_5M[percent_feature_names] += 1

feature_engineering_5M = pd.DataFrame(feature_engineering_5M, columns = feature_names)
total = len(feature_engineering_5M.index)
start_point = total

train_feature_engineering_5M = feature_engineering_5M.loc[1000 : (total - start_point) + int(start_point * 0.9)]
valid_feature_engineering_5M = feature_engineering_5M.loc[(total - start_point) + int(start_point * 0.9) : int(start_point * 0.99)]

# train_feature_engineering_5M = feature_engineering_5M.loc[int(total * 0.79) : int(total * 0.99)]
# valid_feature_engineering_5M = feature_engineering_5M.loc[int(total * 0.99) : ]

total_train = len(train_feature_engineering_5M.index)
total_valid = len(valid_feature_engineering_5M.index)

# print('train ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
dataset_train = window_dataset(
								series = train_feature_engineering_5M,
								window_size = window_size, 
								size_target = size_target,
								shift = shift,
								target_name = target_name,
								target_type = target_type,
								feature_names = feature_names,
								feature_names_shouldnt_scale = feature_names_shouldnt_scale,
								batch_size = 1,
								shuffle = True
								)

# # print('valid ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
dataset_valid = window_dataset(
								series = valid_feature_engineering_5M,
								window_size = window_size, 
								size_target = size_target,
								shift = shift,
								target_name = target_name,
								target_type = target_type,
								feature_names = feature_names,
								feature_names_shouldnt_scale = feature_names_shouldnt_scale,
								batch_size = 1,
								shuffle = False
								)

class MinLayer(tf.keras.layers.Layer):

    def __init__(self, shape, batch_size, units, name, **kwargs):
    	super().__init__(name = name)
    	super(MinLayer, self).__init__(**kwargs)

    	self.batch_size = batch_size
    	self.shape = shape
    	self.my_input_shape = [batch_size, self.shape[0], self.shape[1]]
    	self.units = units


    def build(self, input_shape):

    	# self.w = self.add_weight(shape = (self.batch_size, ), name = 'weights_' + self.name, initializer = 'random_normal', trainable=True)
    	# self.w_1 = self.add_weight(shape = (self.batch_size, self.my_input_shape[2], self.units), name = 'weights_1_' + self.name, initializer = 'random_normal', trainable=True)
    	# self.w_3 = self.add_weight(shape = (self.batch_size, self.units, self.my_input_shape[2]), name = 'weights_3_' + self.name, initializer = 'random_normal', trainable=True)

    	# self.b_1 = self.add_weight(shape = (self.batch_size, self.units, self.my_input_shape[2]), name = 'biases_1_' + self.name, initializer = 'random_normal', trainable=True)
    	# self.b_2 = self.add_weight(shape = (self.batch_size, self.units, self.my_input_shape[2]), name = 'biases_2_' + self.name, initializer = 'random_normal', trainable=True)
    	pass

    @tf.function
    def call(self, inputs):
    	return tf.math.reduce_min(inputs, keepdims = True) #+ self.b_1

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


    def build(self, input_shape):

    	# self.w = self.add_weight(shape = (self.batch_size, ), name = 'weights_' + self.name, initializer = 'random_normal', trainable=True)
    	# self.w_1 = self.add_weight(shape = (self.batch_size, self.my_input_shape[2], self.units), name = 'weights_1_' + self.name, initializer = 'random_normal', trainable=True)
    	# self.w_3 = self.add_weight(shape = (self.batch_size, self.units, self.my_input_shape[2]), name = 'weights_3_' + self.name, initializer = 'random_normal', trainable=True)

    	# self.b_1 = self.add_weight(shape = (self.batch_size, self.units, self.my_input_shape[2]), name = 'biases_1_' + self.name, initializer = 'random_normal', trainable=True)
    	# self.b_2 = self.add_weight(shape = (self.batch_size, self.units, self.my_input_shape[2]), name = 'biases_2_' + self.name, initializer = 'random_normal', trainable=True)
    	pass

    @tf.function
    def call(self, inputs):
    	return tf.math.reduce_max(inputs, keepdims = True) #+ self.b_1

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

input_simple_model = tf.keras.layers.Input(shape = [500, len(feature_names) - 1], batch_size = 1, name = 'model_' + feature_names_str + '_input_price')

# input_simple_model_scale = BatchScaler(units = 64,shape = [900, len(feature_names) - 1], batch_size = 1, name = 'model_' + feature_names_str + '_input_scaler')
if target_type == 'max':
	output_max = MaxLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_max_layer')
if target_type == 'min':
	output_min = MinLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_min_layer')

input_percent_feature = input_simple_model

input_sepconv = tf.keras.layers.SeparableConv1D(
											    filters = 100,
											    kernel_size = 5,
											    strides = 1,
											    padding = "causal",
											    depth_multiplier = 60,
											    activation = 'tanh',
											    data_format = 'channels_last',
											    use_bias = False,
											    name = 'model_' + feature_names_str + '_sepconv_1'
												)(input_percent_feature)

#Wave Net Branch: *********************************************
wave_net_output = input_sepconv

wave_net_output = tf.keras.layers.AveragePooling1D(pool_size = 5)(wave_net_output)

wave_net_output = tf.keras.layers.SeparableConv1D(
													filters = 100,
													kernel_size = 5,
													strides = 1,
													activation = 'tanh',
													padding = 'causal',
													depth_multiplier = 20,
													data_format = 'channels_last',
													use_bias = False,
													name = 'model_' + feature_names_str + '_sepconv_2'
													)(wave_net_output)

counter = 1
for dilation_rate in (1, 5, 10, 15, 20, 25):

	wave_net_1 = tf.keras.layers.SeparableConv1D(
											    filters = 25,
											    kernel_size = 5,
											    strides = 1,
											    dilation_rate = dilation_rate,
											    padding = "causal",
											    depth_multiplier = 20,
											    activation = 'tanh',
											    data_format = 'channels_last',
											    use_bias = False,
											    name = 'model_' + feature_names_str + '_sepconv_wave_1_' + str(counter)
												)(wave_net_output)

	wave_net_2 = tf.keras.layers.SeparableConv1D(
											    filters = 25,
											    kernel_size = 5,
											    strides = 1,
											    dilation_rate = dilation_rate,# * 2,
											    padding = "causal",
											    depth_multiplier = 20,
											    activation = 'swish',
											    data_format = 'channels_last',
											    use_bias = False,
											    name = 'model_' + feature_names_str + '_sepconv_wave_2_' + str(counter)
												)(wave_net_output)

	wave_net_3 = tf.keras.layers.SeparableConv1D(
											    filters = 25,
											    kernel_size = 5,
											    strides = 1,
											    dilation_rate = dilation_rate,# * 4,
											    padding = "causal",
											    depth_multiplier = 20,
											    activation = 'elu',
											    data_format = 'channels_last',
											    use_bias = False,
											    name = 'model_' + feature_names_str + '_sepconv_wave_3_' + str(counter)
												)(wave_net_output)

	wave_net_4 = tf.keras.layers.SeparableConv1D(
											    filters = 25,
											    kernel_size = 5,
											    strides = 1,
											    dilation_rate = dilation_rate,# * 8,
											    padding = "causal",
											    depth_multiplier = 20,
											    activation = 'softsign',
											    data_format = 'channels_last',
											    use_bias = False,
											    name = 'model_' + feature_names_str + '_sepconv_wave_4_' + str(counter)
												)(wave_net_output)											

	wave_net_output = tf.keras.layers.concatenate([
													wave_net_1,
													wave_net_2, 
													wave_net_3,
													wave_net_4,
													], 
													name = 'model_' + feature_names_str + '_concat_' + str(counter)
													)
	counter += 1

output_sepconv = tf.keras.layers.SeparableConv1D(
													filters = 100, 
													kernel_size = 5, 
													strides = 1, 
													activation = 'tanh', 
													padding = 'causal', 
													depth_multiplier = 20, 
													data_format = 'channels_last',
													use_bias = False,
													name = 'model_' + feature_names_str + '_sepconv_3'
													)(wave_net_output)

output_sepconv = tf.keras.layers.SeparableConv1D(
													filters = 100, 
													kernel_size = 5, 
													strides = 1, 
													activation = 'tanh', 
													padding = "causal", 
													depth_multiplier = 20, 
													data_format = 'channels_last',
													use_bias = False,
													name = 'model_' + feature_names_str + '_sepconv_4'
													)(output_sepconv)

output_sepconv = tf.keras.layers.AveragePooling1D(pool_size = 5)(output_sepconv)

# output_sepconv = tf.keras.layers.Lambda(lambda x: x + 1)(wave_net_output)

output_sepconv = tf.keras.layers.SeparableConv1D(
													filters = 100, 
													kernel_size = 2, 
													strides = 1, 
													activation = 'swish', 
													padding = 'causal', 
													depth_multiplier = 20, 
													data_format = 'channels_last',
													use_bias = True,
													name = 'model_' + feature_names_str + '_sepconv_1' + '_output'
													)(output_sepconv)

output_sepconv = tf.keras.layers.SeparableConv1D(
													filters = 50, 
													kernel_size = 2, 
													strides = 1, 
													activation = 'swish', 
													padding = 'causal', 
													depth_multiplier = 20, 
													data_format = 'channels_last',
													use_bias = True,
													name = 'model_' + feature_names_str + '_sepconv_2' + '_output'
													)(output_sepconv)

output_sepconv = tf.keras.layers.SeparableConv1D(
													filters = 25, 
													kernel_size = 2, 
													strides = 1, 
													activation = 'swish', 
													padding = 'causal', 
													depth_multiplier = 20, 
													use_bias = True,
													name = 'model_' + feature_names_str + '_sepconv_3' + '_output'
													)(output_sepconv)

output_sepconv = tf.keras.layers.SeparableConv1D(
													filters = 5, 
													kernel_size = 2, 
													strides = 1, 
													activation = 'swish', 
													padding = 'causal', 
													depth_multiplier = 20, 
													data_format = 'channels_last',
													use_bias = True,
													name = 'model_' + feature_names_str + '_sepconv_4' + '_output'
													)(output_sepconv)

output_sepconv = tf.keras.layers.AveragePooling1D(pool_size = 5)(output_sepconv)

output_sepcpconv_branch = tf.keras.layers.SeparableConv1D(
															filters = 1,
															kernel_size = 1,
															# activation = 'swish',
															# padding = 'causal',
															depth_multiplier = 20,
															data_format = 'channels_last',
															use_bias = True,
															name = 'model_' + feature_names_str + '_sepconv' + '_output'
															)(output_sepconv)
#/////////////////////////////////////////////////////////////////////////

#OutPut Branch: ***************************
if target_type == 'max':
	output_percent = output_max(inputs = output_sepcpconv_branch)

if target_type == 'min':
	output_percent = output_min(inputs = output_sepcpconv_branch)

if target_type == 'mean':
	output_percent = tf.keras.layers.AveragePooling1D(pool_size = 4)(output_sepcpconv_branch)
#//////////////////////////////////////////////////


model = tf.keras.Model(input_simple_model, output_percent, name = 'model_' + feature_names_str)

learning_rate = 1.5e-5 #7.0e-6
optimizer = tf.keras.optimizers.Adam(learning_rate = learning_rate)

model.compile(
				optimizer = optimizer,
              	loss = [tf.keras.losses.Huber(), 'mae', 'mse', tf.keras.losses.MeanAbsolutePercentageError()],
             	metrics = ['mae', 'mse', tf.keras.metrics.MeanAbsolutePercentageError()],
             )
model.summary()

tf.keras.utils.plot_model(
						model, 
						show_shapes = True, 
						to_file = 'model_' + feature_names_str + '.png'
						)

EPOCHS = 2

model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
														'model_' + feature_names_str + '_' + timeframe + '.h5', 
														save_best_only=True,
														save_weights_only = False
														)

early_stopping = tf.keras.callbacks.EarlyStopping(patience = 50)

history = model.fit(
				    x = dataset_train,
				    epochs = EPOCHS,
				    validation_data = dataset_valid, 
				    callbacks = [model_checkpoint, early_stopping]
					)

if os.path.exists('model_' + feature_names_str + '_' + timeframe + '.h5'):
	if target_type == 'max':
		model = tf.keras.models.load_model(
											'model_' + feature_names_str + '_' + timeframe + '.h5', 
											custom_objects = {'MaxLayer': MaxLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_max_layer')}
											)
		model.trainable = True
		# learning_rate = 6.0e-5

	if target_type == 'min':
		model = tf.keras.models.load_model(
											'model_' + feature_names_str + '_' + timeframe + '.h5', 
											custom_objects = {'MinLayer': MinLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_min_layer')}
											)
		model.trainable = True

	if target_type == 'mean':
		model = tf.keras.models.load_model('model_' + feature_names_str + '_' + timeframe + '.h5')
		model.trainable = True
	
	learning_rate = 5e-8 #6.3e-9 #1.5e-8

optimizer = tf.keras.optimizers.Adam(learning_rate = learning_rate)

if os.path.exists('TensorBoard'):
	print('****************************** Exist ******************************')
	shutil.rmtree('TensorBoard')

tensor_board = tf.keras.callbacks.TensorBoard(
											log_dir = 'TensorBoard', 
											histogram_freq = 1
											)
#python.exe C:\\Users\\Mehrshad\\AppData\\Roaming\\Python\\Python38\\site-packages\\tensorboard\\main.py --logdir=C:\\Users\\Mehrshad\\Desktop\\ShadBot\\TensorBoard

# lr_schedule = tf.keras.callbacks.LearningRateScheduler(lambda epoch: 1e-9 * 10**(epoch / 10))
# optimizer = tf.keras.optimizers.Adam(learning_rate = 1e-9)

# tf.keras.losses.MeanAbsolutePercentageError()
# tf.keras.metrics.MeanAbsolutePercentageError()

model.compile(
				optimizer = optimizer,
              	loss = [tf.keras.losses.MeanAbsolutePercentageError()],
             	metrics = [tf.keras.metrics.MeanAbsolutePercentageError()],
             )
model.summary()

tf.keras.utils.plot_model(
						model, 
						show_shapes = True, 
						to_file = 'model_' + feature_names_str + '.png'
						)

EPOCHS = 100

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
    	print('Epoch Model Reset States ...')
    	print()

model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
														'model_' + feature_names_str + '_' + timeframe + '.h5', 
														save_best_only=True,
														save_weights_only = False
														)

early_stopping = tf.keras.callbacks.EarlyStopping(patience = 50)

# history = model.fit(
# 				    dataset_train,
# 				    epochs = EPOCHS,
# 				    validation_data = dataset_valid,
# 				    callbacks = [lr_schedule, tensor_board]
# 					)

history = model.fit(
				    x = dataset_train,
				    epochs = EPOCHS,
				    # steps_per_epoch = total_train,
				    validation_data = dataset_valid, 
				    # validation_steps = total_valid,
				    callbacks = [model_checkpoint, early_stopping, tensor_board]#, ResetStatesCallback()]
					)
# sys.exit()

model_max = tf.keras.models.load_model(
									'model_' + feature_names_str.split(target_type)[0] + 'max' + '_' + timeframe + '.h5', 
									custom_objects = {'MaxLayer': MaxLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_max_layer')}
									)

model_min = tf.keras.models.load_model(
									'model_' + feature_names_str.split(target_type)[0] + 'min' + '_' + timeframe + '.h5', 
									custom_objects = {'MinLayer': MinLayer(units = 1, shape = [50, 1], batch_size = 1, name = 'model_' + feature_names_str + '_output_min_layer')}
									)

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

	def MinMax(dataset, feature_names_list, feature_names_shouldnt_scale_list):
		
		input_list = []

		for feat in feature_names_list:

			if False:#(feat in feature_names_shouldnt_scale_list):

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
													feature_names_shouldnt_scale_list = feature_names_shouldnt_scale_list
													)
											)
							)

	dataset = dataset.batch(batch_size).prefetch(1)


	# target = np.where(series.columns == 'close')[0][0]
	# import matplotlib.pyplot as plt
	# counter = 0
	# for x in dataset:
	# 	figure, (ax0, ax1) = plt.subplots(2, 1)
	# 	ax0.plot(x[0, : , target].numpy(), c = 'b')

	# 	print(series['close'][counter: window_size + counter])

	# 	ax1.plot(range(0, int(window_size/2)),series['close'][counter: int(window_size/2) + counter] , c = 'orange', linestyle = '--')
		
	# 	print("x = ", x[0, : , target].numpy())
	# 	print()
	# 	print('////////////////////////////////')
	# 	counter += shift
	# 	print('shape x = ', tf.shape(x))
	# 	plt.show()

	return dataset

import matplotlib.pyplot as plt

test_feature_engineering_5M = feature_engineering_5M.loc[int(total * 0.9) :]

# data_evaluate = window_dataset(
# 								series = test_feature_engineering_5M[ : ], 
# 								window_size = 512, 
# 								batch_size = 1,
# 								shift = 1,
# 								target_name = target_name,
# 								feature_names = feature_names,
# 								feature_names_shouldnt_scale = percent_feature_names,
# 								)

# model_min.evaluate(x = data_evaluate, batch_size = 1)
# model_max.evaluate(x = data_evaluate, batch_size = 1)

i = test_feature_engineering_5M.index[0]

while i <= test_feature_engineering_5M.index[-1] - 4:

	data_predict = window_dataset_predict(
											series = test_feature_engineering_5M.loc[i : i + 500], 
											window_size = 500, 
											batch_size = 1,
											shift = 1,
											target_name = target_name,
											feature_names = feature_names,
											feature_names_shouldnt_scale = percent_feature_names
											)

	predict_serie_min = model_min.predict(data_predict)
	predict_serie_max = model_max.predict(data_predict)

	dataset_scaled_total_5M = pd.DataFrame(
											(
						                     ((dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 550] * 2) - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 550].min())/
						                     (dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 550].max() - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 550].min())
						                    ),
											columns = ['close']
											)

	dataset_scaled_5M = pd.DataFrame(
										(
					                     ((dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 500] * 2) - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 500].min())/
					                     (dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 500].max() - dataset_5M.drop(columns = ['XAUUSD_i', 'time'])['close'][i : i + 500].min())
					                    ),
										columns = ['close']
										)

	percent_change = pd.DataFrame()
	percent_change['none'] = [0]
	percent_change = percent_change.assign(
											predict_scale_min = dataset_scaled_5M['close'][i + 499] * predict_serie_min[-1, -1, 0],
											valid_scale_min = np.min(dataset_scaled_total_5M.loc[i + 500: i + 550].values),
											valid_min = np.min(dataset_5M['low'][i + 500: i + 550].values),
											percent_valid_scale_min = ((np.min(dataset_scaled_total_5M.loc[i + 500: i + 550].values) - dataset_scaled_5M['close'][i + 499])/dataset_scaled_5M['close'][i + 499]) + 1,
											percent_valid_min = ((np.min(dataset_5M['close'][i + 500: i + 550]) - dataset_5M['close'][i + 499])/dataset_5M['close'][i + 499]) + 1,
											percent_predict_min = predict_serie_min[-1, -1, 0] + 0.5,

											predict_scale_max = dataset_scaled_5M['close'][i + 499] * predict_serie_max[-1, -1, 0],
											valid_scale_max = np.max(dataset_scaled_total_5M.loc[i + 500: i + 550].values),
											valid_max = np.max(dataset_5M['high'][i + 500: i + 550].values),
											percent_valid_scale_max = ((np.max(dataset_scaled_total_5M.loc[i + 500: i + 512].values) - dataset_scaled_5M['close'][i + 499])/dataset_scaled_5M['close'][i + 499]) + 1,
											percent_valid_max = ((np.max(dataset_5M['close'][i + 500: i + 512]) - dataset_5M['close'][i + 499])/dataset_5M['close'][i + 499]) + 1,
											percent_predict_max = predict_serie_max[-1, -1, 0] ,
											)

	percent_change = percent_change.assign(
											predict_min = dataset_5M['low'][i + 499] * (predict_serie_min[-1, -1, 0] + 0.5),
											predict_max = dataset_5M['high'][i + 499] * (predict_serie_max[-1, -1, 0] + 0.5),

											# predict_min = 	(
											# 					(
											# 						percent_change['predict_scale_min'] * 
											# 						(
											# 							dataset_5M['close'][i : i + 499].max() - 
											# 							dataset_5M['close'][i : i + 499].min()
											# 						)
											# 					) + (dataset_5M['close'][i : i + 499].min())
											# 				)/2,

											# predict_max = 	(
											# 					(
											# 						percent_change['predict_scale_max'] * 
											# 						(
											# 							dataset_5M['close'][i : i + 499].max() - 
											# 							dataset_5M['close'][i : i + 499].min()
											# 						)
											# 					) + (dataset_5M['close'][i : i + 499].min())
											# 				)/2
											)
	# with pd.option_context('display.max_rows', None, 'display.max_columns', None):
	# 	print(percent_change.drop(columns = ['none']).loc[0])

	#Min: ********************************
	mape_real_price_min = abs((percent_change['predict_min'] - percent_change['valid_min'])/percent_change['valid_min']) * 100
	mape_scale_price_min = abs((percent_change['predict_scale_min'] - percent_change['valid_scale_min'])/percent_change['valid_scale_min']) * 100

	mape_real_percent_min = abs((percent_change['percent_predict_min'] - percent_change['percent_valid_min'])/percent_change['percent_valid_min']) * 100
	mape_scale_percent_min = abs((percent_change['percent_predict_min'] - percent_change['percent_valid_scale_min'])/percent_change['percent_valid_scale_min']) * 100
	#/////////////////////////////

	#Max: *********************************
	mape_real_price_max = abs((percent_change['predict_max'] - percent_change['valid_max'])/percent_change['valid_max']) * 100
	mape_scale_price_max = abs((percent_change['predict_scale_max'] - percent_change['valid_scale_max'])/percent_change['valid_scale_max']) * 100

	mape_real_percent_max = abs((percent_change['percent_predict_max'] - percent_change['percent_valid_max'])/percent_change['percent_valid_max']) * 100
	mape_scale_percent_max = abs((percent_change['percent_predict_max'] - percent_change['percent_valid_scale_max'])/percent_change['percent_valid_scale_max']) * 100

	print('MAPE Real Price Min = ', mape_real_price_min.values[0], ' %')
	print('MAPE Real Percent Min = ', mape_real_percent_min.values[0], ' %')
	print('MAPE Scale Price Min = ', mape_scale_price_min.values[0], ' %')
	print('MAPE Scale Percent Min = ', mape_scale_percent_min.values[0], ' %')

	print()

	print('MAPE Real Price Max = ', mape_real_price_max.values[0], ' %')
	print('MAPE Real Percent Max = ', mape_real_percent_max.values[0], ' %')
	print('MAPE Scale Price Max = ', mape_scale_price_max.values[0], ' %')
	print('MAPE Scale Percent Max = ', mape_scale_percent_max.values[0], ' %')

	# figure, (ax0, ax1, ax2, ax3) = plt.subplots(4, 1)
	# plt.plot(dataset_5M['close'][i : i + 550].index, dataset_scaled_total_5M['close'], c = 'b', linestyle = '--')
	# plt.axvline(i + 499, c = 'g', linestyle = '--')

	# plt.axvline(dataset_5M['close'][i + 500: i + 512].idxmax(), c = 'orange', linestyle = '--')
	# plt.axvline(dataset_5M['close'][i + 500: i + 512].idxmin(), c = 'purple', linestyle = '--')

	# plt.axhline(dataset_5M['close'][i + 500: i + 512].max(), c = 'g', linestyle = ':')
	# plt.axhline(dataset_5M['close'][i + 500: i + 512].min(), c = 'r', linestyle = ':')

	# plt.axhline(dataset_scaled_5M['close'][i + 499] * predict_serie_min[-1, -1, 0], c = 'r')
	# plt.axhline(dataset_scaled_5M['close'][i + 499] * predict_serie_max[-1, -1, 0], c = 'g')

	# plt.show()

	plt.plot(dataset_5M['close'][i : i + 750].index, dataset_5M['close'][i : i + 750], c = 'b', linestyle = '--')
	plt.axvline(i + 499, c = 'g', linestyle = '--')
	plt.axvline(i + 512, c = 'black', linestyle = '--')

	plt.axvline(dataset_5M['close'][i + 500: i + 512].idxmax(), c = 'orange', linestyle = '--')
	plt.axvline(dataset_5M['close'][i + 500: i + 512].idxmin(), c = 'purple', linestyle = '--')

	plt.axhline(dataset_5M['close'][i + 500: i + 512].max(), c = 'g', linestyle = ':')
	plt.axhline(dataset_5M['close'][i + 500: i + 512].min(), c = 'r', linestyle = ':')

	plt.axhline(percent_change['predict_min'].values, c = 'r')
	plt.axhline(percent_change['predict_max'].values, c = 'g')

	plt.savefig(f'pics/{i}.jpg', dpi=600, bbox_inches='tight')

	plt.figure().clear()
	plt.close('all')
	plt.cla()
	plt.clf()

	# plt.show()

	# plt.plot(percent_change['predict'])
	# plt.plot(percent_change['valid'])
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