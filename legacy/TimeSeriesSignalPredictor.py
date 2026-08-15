import pandas as pd
import tensorflow as tf
# import tensorflow_transform as tft
import tensorflow_datasets as tfds
import numpy as np
from mlxtend.preprocessing import minmax_scaling
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.FeatureEngineering.FeatureEngineering import FeatureEngineering
from src.utils.FeatureEngineering.DatasetIO import DatasetIO
import shutil
import logging
import os
from src.utils.FeatureEngineering.Patterns import Patterns

logger = tf.get_logger()
logger.setLevel(logging.ERROR)

tf.random.set_seed(50)
np.random.seed(50)

#Buy: 0.9
#Sell: 0.45
#No Trade: 0

def to_windows(dataset, length, shift):
	dataset = dataset.window(int(length), shift = shift, drop_remainder = True)
	return dataset.flat_map(lambda window_ds: window_ds.batch(int(length)))

def PatternReader(dataset, symbol, timeframe):

    patterns = Patterns()
    patterns.percent_zigzag_finder = 0.6 #0.5
    patterns.profit = 2.0 #1.0
    
    zigzag_patterns = patterns.Get(
                                    mode = None, 
                                    dataset_5M = dataset, 
                                    dataset_15M = dataset, 
                                    dataset_1H = dataset, 
                                    dataset_4H = dataset,
                                    dataset_1D = dataset,
                                    symbol = symbol,
                                    pattern_name = 'zigzag',
                                    timeframe = timeframe
                                    )
    return zigzag_patterns

def window_dataset_signal_model(
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
	def MinMax_Feature(dataset, feature_names_list, size_target, feature_names_shouldnt_scale_list):

		input_list = []

		for feat in feature_names_list:

			if False:#(feat in feature_names_shouldnt_scale_list):

				input_list.append(
									tf.cast(
											(
												(
													dataset[: , 0 , feat]
												) #* 4.0
											) ,#- 2.0,
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
															), 

											window[-1, 0, target]
											)
							)

	if shuffle:
		dataset = dataset.shuffle(1000 * batch_size)#, seed = seed)

	@tf.function
	def NoTradeFilter(window, target):
		if tf.math.equal(target, 3):
			return False
		else:
			return True

	dataset = dataset.filter(NoTradeFilter)

	dataset = dataset.batch(batch_size).prefetch(1)

	# counter = 0
	# for x, y in dataset:
	# 	# if y[0].numpy() == 3:
	# 	# 	print('x = ', x.numpy())
	# 	# 	print('y = ', y.numpy())
	# 	# 	print('shape x = ', tf.shape(x))
	# 	# 	print('shape y = ', tf.shape(y))

	# 	if counter >= 217:
	# 		print('x = ', x.numpy())
	# 		print('y = ', y.numpy())
	# 		print('shape x = ', tf.shape(x))
	# 		print('shape y = ', tf.shape(y))

	# 	counter += 1

	return dataset


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

def wavenet_residual_block(inputs, n_filters, dilation_rate):

	z = tf.keras.layers.Conv1D(
								filters = n_filters * 2 , 
								kernel_size = 5, 
								padding = "causal",
								# activation = 'tanh',
								dilation_rate = dilation_rate,
								kernel_regularizer = tf.keras.regularizers.L2(1.5e-4),
								activity_regularizer = tf.keras.regularizers.L2(1.5e-4),
								# bias_regularizer = tf.keras.regularizers.L2(1.5e-4),
								)(inputs)																												
	
	# z = tf.keras.layers.SpatialDropout1D(0.2)(z)

	z = GatedActivationUnit()(z)
	z = tf.keras.layers.Conv1D(
								filters = n_filters, 
								kernel_size = 1,
								kernel_regularizer = tf.keras.regularizers.L2(1.5e-4),
								activity_regularizer = tf.keras.regularizers.L2(1.5e-4),
								# bias_regularizer = tf.keras.regularizers.L2(1.5e-4),
								)(z)

	z = tf.keras.layers.Dropout(0.05)(z)	
	# z = tf.keras.layers.SpatialDropout1D(0.1)(z)

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

	feature_engineering_5M, feature_engineering_15M, feature_engineering_1H, feature_engineering_4H, feature_engineering_1D = feature_engineering(
																							                                                    dataset_5M = dataset_5M, 
																							                                                    dataset_15M = dataset_15M, 
																							                                                    dataset_1H = dataset_1H, 
																							                                                    dataset_4H = dataset_4H, 
																							                                                    dataset_1D = dataset_1D, 
																							                                                    symbol = symbol, 
																							                                                    mode = 'Run', 
																							                                                    scale = False
																							                                                    )

else:
	dataset_5M, dataset_15M, dataset_1H, dataset_4H, dataset_1D = loging.readall(
																				symbol = symbol, 
																				number_5M = 'all', 
																				number_15M = 0, 
																				number_1H = 0,
																				number_4H = 0,
																				number_1D = 0
																				)


	dataset_5M = dataset_5M[symbol]
	dataset_15M = pd.DataFrame()
	dataset_1H = pd.DataFrame()
	dataset_4H = pd.DataFrame()
	dataset_1D = pd.DataFrame()

	feature_engineering = FeatureEngineering()

	feature_engineering_5M, _, _, _, _ = feature_engineering(
		                                                    dataset_5M = dataset_5M, 
		                                                    dataset_15M = dataset_15M, 
		                                                    dataset_1H = dataset_1H, 
		                                                    dataset_4H = dataset_4H, 
		                                                    dataset_1D = dataset_1D, 
		                                                    symbol = symbol, 
		                                                    mode = None, 
		                                                    scale = False
		                                                    )


if symbol in feature_engineering_5M.columns:
	feature_engineering_5M = feature_engineering_5M.drop(columns = [symbol])

dataset = feature_engineering_5M

for clm in dataset.columns:
	if 'time' in clm:
		dataset = dataset.drop(columns = [clm])

feature_engineering_5M = dataset

timeframe = '5M'
target_name = 'signal'
target_type = 'signal_' + target_name
window_size = 500
size_target = 1
shift = 1

feature_names = []

feature_names.append(target_name)
feature_names.extend(feature_engineering_5M.columns)


feature_names_str = 'All_feature_' + target_type

feature_names_shouldnt_scale_list = []
for clm in feature_engineering_5M.columns:

	if 'sin' in clm:
		feature_names_shouldnt_scale_list.append(clm)

	if 'cos' in clm:
		feature_names_shouldnt_scale_list.append(clm)

	if 'number' in clm:
		feature_names_shouldnt_scale_list.append(clm)

	if 'pattern' in clm:
		feature_names_shouldnt_scale_list.append(clm)

	if 'color' in clm:
		feature_names_shouldnt_scale_list.append(clm)

	if 'div' in clm:
		feature_names_shouldnt_scale_list.append(clm)

	if 'CDL' in clm:
		feature_names_shouldnt_scale_list.append(clm)

feature_names_shouldnt_scale = []
feature_names_shouldnt_scale.extend(feature_names_shouldnt_scale_list)

print()
print()
print('**********************************')
print('percent_price = ', len(feature_engineering_5M.columns))
print(feature_engineering_5M.columns)
print('//////////////////////////////////')
print()
print()

#24781
#0.9138

patterns = PatternReader(dataset = dataset_5M, symbol = symbol, timeframe = timeframe)

print('Full Buy: ', len(patterns['signal'][patterns['signal'] == 'buy'].index))
print('Full Sell: ', len(patterns['signal'][patterns['signal'] == 'sell'].index))
print('Full No Trade: ', len(patterns['signal'][patterns['signal'] == 'no_trade'].index))

buy = 0
sell = 1
no_trade = 3

patterns['signal'][patterns['signal'] == 'buy'] = buy
patterns['signal'][patterns['signal'] == 'sell'] = sell
patterns['signal'][patterns['signal'] == 'no_trade'] = no_trade
patterns['signal'] = patterns['signal'].fillna(value = 3)


target_name = 'signal'
feature_engineering_5M = feature_engineering_5M.join(patterns[target_name].copy(deep = True), how = 'right')

feature_engineering_5M = pd.DataFrame(feature_engineering_5M, columns = feature_names)
total = len(feature_engineering_5M.index)
start_point = total
# feature_engineering_5M = feature_engineering_5M[145000:].reset_index()
num_test = 9000
#start for lr_schedule = 130000

train_feature_engineering_5M = feature_engineering_5M.loc[100 : total - num_test]
valid_feature_engineering_5M = feature_engineering_5M.loc[total - window_size - num_test : ]
# test_feature_engineering_5M = feature_engineering_5M.loc[total - window_size - num_test : ]

print()
print()
print('*********************************')
print('Train Buy: ', len(train_feature_engineering_5M['signal'][train_feature_engineering_5M['signal'] == buy].index))
print('Train Sell: ', len(train_feature_engineering_5M['signal'][train_feature_engineering_5M['signal'] == sell].index))
print('Train No Trade: ', len(train_feature_engineering_5M['signal'][train_feature_engineering_5M['signal'] == no_trade].index))
num_total_train = (
					len(train_feature_engineering_5M['signal'][train_feature_engineering_5M['signal'] == buy].index) + 
					len(train_feature_engineering_5M['signal'][train_feature_engineering_5M['signal'] == sell].index) +
					len(train_feature_engineering_5M['signal'][train_feature_engineering_5M['signal'] == no_trade].index)
					)

print('Train Total: ', num_total_train)
print()

print('Valid Buy: ', len(valid_feature_engineering_5M['signal'][valid_feature_engineering_5M['signal'] == buy].index))
print('Valid Sell: ', len(valid_feature_engineering_5M['signal'][valid_feature_engineering_5M['signal'] == sell].index))
print('Valid No Trade: ', len(valid_feature_engineering_5M['signal'][valid_feature_engineering_5M['signal'] == no_trade].index))

num_total_valid = (
					len(valid_feature_engineering_5M['signal'][valid_feature_engineering_5M['signal'] == buy].index) + 
					len(valid_feature_engineering_5M['signal'][valid_feature_engineering_5M['signal'] == sell].index) +
					len(valid_feature_engineering_5M['signal'][valid_feature_engineering_5M['signal'] == no_trade].index)
					)

print('Valid Total: ', num_total_valid)
print('//////////////////////////////////')
print()
print()

dataset_train = window_dataset_signal_model(
											series = train_feature_engineering_5M, 
											window_size = window_size, 
											batch_size = 1, 
											shuffle = True, 
											seed = 42,
											size_target = size_target,
											shift = shift, 
											target_name = target_name,
											target_type = target_type,
											feature_names = feature_names,
											feature_names_shouldnt_scale = feature_names_shouldnt_scale
											)

dataset_valid = window_dataset_signal_model(
											series = valid_feature_engineering_5M, 
											window_size = window_size, 
											batch_size = 1, 
											shuffle = False, 
											seed = 42,
											size_target = size_target,
											shift = shift, 
											target_name = target_name,
											target_type = target_type,
											feature_names = feature_names,
											feature_names_shouldnt_scale = feature_names_shouldnt_scale
											)

# dataset_test = window_dataset_signal_model(
# 											series = test_feature_engineering_5M, 
# 											window_size = window_size, 
# 											batch_size = 1, 
# 											shuffle = False, 
# 											seed = 42,
# 											size_target = size_target,
# 											shift = shift, 
# 											target_name = target_name,
# 											target_type = target_type,
# 											feature_names = feature_names,
# 											feature_names_shouldnt_scale = feature_names_shouldnt_scale
# 											)

tf.random.set_seed(42)

n_layers_per_block = 10  # 10 in the paper
n_blocks = 3  # 3 in the paper
n_filters = 128  # 128 in the paper
n_outputs = size_target  # 256 in the paper

inputs = tf.keras.layers.Input(shape=[window_size, len(feature_names) - 1])

z = tf.keras.layers.SeparableConv1D(
									filters = n_filters, 
									kernel_size = 10, 
									padding = "causal",
									# activation = "softsign",
									depth_multiplier = 20,
									kernel_regularizer = tf.keras.regularizers.L2(1.5e-4),
									activity_regularizer = tf.keras.regularizers.L2(1.5e-4),
									# bias_regularizer = tf.keras.regularizers.L2(1.5e-4),
									)(inputs)

z = tf.keras.layers.Dropout(0.05)(z)																										

skip_to_last = []

for dilation_rate in [2**i for i in range(n_layers_per_block)] * n_blocks:

    z, skip = wavenet_residual_block(z, n_filters, dilation_rate)
    skip_to_last.append(skip)

z = tf.keras.activations.relu(tf.keras.layers.Add()(skip_to_last))

# z = tf.keras.layers.SpatialDropout1D(0.46)(z)

z = tf.keras.layers.SeparableConv1D(
									filters = n_filters, 
									kernel_size = 5, 
									activation = "relu",
									depth_multiplier = 20,
									kernel_regularizer = tf.keras.regularizers.L2(1.5e-4),
									activity_regularizer = tf.keras.regularizers.L2(1.5e-4),
									# bias_regularizer = tf.keras.regularizers.L2(1.5e-4),
									)(z)

# z = tf.keras.layers.SpatialDropout1D(0.93)(z)										

Y_preds = tf.keras.layers.SeparableConv1D(
											filters = 2, 
											kernel_size = 5,
											depth_multiplier = 20,
											activation = 'linear',
											kernel_regularizer = tf.keras.regularizers.L2(1.5e-4),
											activity_regularizer = tf.keras.regularizers.L2(1.5e-4),
											# bias_regularizer = tf.keras.regularizers.L2(1.5e-4),
											)(z)		


output = tf.keras.layers.Flatten()(Y_preds)#[:, -1, :])

# output = tf.keras.layers.Dense(
# 								units = 90, 
# 								activation= 'sigmoid',
# 								# kernel_regularizer = tf.keras.regularizers.L2(1.5e-7),
# 								# activity_regularizer = tf.keras.regularizers.L2(1.5e-7),
# 								# bias_regularizer = tf.keras.regularizers.L1L2(1.0e-20, 1.5e-7),
# 								)(output)

# output = tf.keras.layers.Dense(
# 								units = 30, 
# 								activation= 'sigmoid',
# 								# kernel_regularizer = tf.keras.regularizers.L2(1.5e-7),
# 								# activity_regularizer = tf.keras.regularizers.L2(1.5e-7),
# 								# bias_regularizer = tf.keras.regularizers.L1L2(1.0e-20, 1.5e-7),
# 								)(output)

# output = tf.keras.layers.Dropout(0.8)(output)

output = tf.keras.layers.Dense(
								units = 2, 
								activation= 'sigmoid',
								kernel_regularizer = tf.keras.regularizers.L2(1.5e-4),
								activity_regularizer = tf.keras.regularizers.L2(1.5e-4),
								# bias_regularizer = tf.keras.regularizers.L2(1.5e-4),
								)(output)


full_wavenet_model = tf.keras.Model(inputs = [inputs], outputs = [output])

model = full_wavenet_model

learning_rate = 1.5e-4
# learning_rate = 1.0800e-04

optimizer = tf.keras.optimizers.experimental.AdamW(learning_rate = learning_rate)

if os.path.exists('TensorBoard'):
	print('****************************** Exist ******************************')
	shutil.rmtree('TensorBoard')

tensor_board = tf.keras.callbacks.TensorBoard(
											log_dir = 'TensorBoard', 
											histogram_freq = 1
											)
#python.exe C:\\Users\\Mehrshad\\AppData\\Roaming\\Python\\Python38\\site-packages\\tensorboard\\main.py --logdir=C:\\Users\\Mehrshad\\Desktop\\ShadBotTrader\\TensorBoard

if os.path.exists('model_signal_' + timeframe + '.h5'):
	print('model_signal_' + timeframe + '.h5')
	model = tf.keras.models.load_model(
										'model_signal_' + timeframe + '.h5',
										custom_objects = {
															'GatedActivationUnit': GatedActivationUnit(),
															}
										)
# lr_schedule = tf.keras.callbacks.LearningRateScheduler(lambda epoch: 1e-8 * 10**(epoch / 10))
# optimizer = tf.keras.optimizers.experimental.AdamW(learning_rate = 1e-8)

model.compile(
				optimizer = optimizer,
              	loss = tf.keras.losses.SparseCategoricalCrossentropy(),
             	metrics = [tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")]
             )
model.summary()

tf.keras.utils.plot_model(
						model, 
						show_shapes = True, 
						to_file = 'model_signal_percent.png'
						)

EPOCHS = 200

class ResetStatesCallback(tf.keras.callbacks.Callback):
    def on_batch_begin(self, batch, logs=None):
    	self.model.reset_states()

evaluate_history = model.evaluate(x = dataset_valid, batch_size = 1)

model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
														'model_signal_' + timeframe + '.h5', 
														save_best_only = True,
														save_weights_only = False,
														monitor = 'val_loss',
    													mode = 'min',
    													verbose = 1, 
    													initial_value_threshold = evaluate_history[0]
														)

early_stopping = tf.keras.callbacks.EarlyStopping(patience = 200)

reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
												    monitor = "val_loss",
												    factor = 0.9,
												    patience = 10,
												    verbose = 1,
												    mode = "min",
												    min_delta = 0.0001,
												    cooldown = 1,
												    min_lr = 1.0e-7,
												)

# history = model.fit(
# 				    dataset_train,
# 				    epochs = EPOCHS,
# 				    validation_data = dataset_valid,
# 				    callbacks = [lr_schedule, tensor_board, ResetStatesCallback()]
# 					)

history = model.fit(
				    dataset_train,
				    epochs = EPOCHS,
				    # steps_per_epoch = total_train,
				    validation_data = dataset_valid,
				    # validation_steps = total_valid,
				    callbacks = [model_checkpoint, early_stopping, reduce_lr, tensor_board]
					)
sys.exit()