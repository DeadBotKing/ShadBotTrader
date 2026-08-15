from src.utils.MLModelGenerator.Image.Config import Config
import tensorflow as tf
import numpy as np
import logging
import shutil
import sys
import os


logger = tf.get_logger()
logger.setLevel(logging.ERROR)

tf.random.set_seed(50)
np.random.seed(50)

if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'

two_cluster_models = [
					'buy_no_trade', 
					'sell_no_trade', 
					'final_image_model_buy_no_trade',
					'final_image_model_sell_no_trade'
					]

class ModelTrainer:

	def __init__(self, model):

		if model._name in two_cluster_models:
			self.learning_rate = 1e-3 #7e-4

		elif model._name == 'buy_sell' or model._name == 'final_image_model_buy_sell':
			self.learning_rate = 5e-4

		elif model._name == 'full_image_model_complex' or model._name == 'final_image_model_full_image_model_complex':
			self.learning_rate = 1e-3

		elif model._name == 'full_image_model_straight' or model._name == 'final_image_model_full_image_model_straight':
			self.learning_rate = 1e-3 #3e-3

		elif model._name == 'double_full_image_model' or model._name == 'final_image_model_double_full_image_model':
			self.learning_rate = 0.06

	def LRFinder(
				self, 
				model, 
				train_data_gen, 
				total_train, 
				val_data_gen, 
				total_val, 
				BATCH_SIZE,
				min_learning_rate = 1e-8,
				EPOCHS = 100
				):
		print()
		print()
		print(f'Model {model._name} LR Finding Strat ...')

		print()
		print("python.exe C:\\Users\\Mehrshad\\AppData\\Roaming\\Python\\Python38\\site-packages\\tensorboard\\main.py --logdir=C:\\Users\\Mehrshad\\Desktop\\ShadBot\\src\\utils\\MLModelGenerator\\Image\\Models\\TensorBoard\\LRFinder")

		print()
		print()

		image_config = Config()

		if not os.path.exists(image_config.cfg['path_TensorBoard'] + path_slash + 'LRFinder'): 
			os.makedirs(image_config.cfg['path_TensorBoard'] + path_slash + 'LRFinder')
		else:
			shutil.rmtree(image_config.cfg['path_TensorBoard'] + path_slash + 'LRFinder')

		tensor_board = tf.keras.callbacks.TensorBoard(
													log_dir = image_config.cfg['path_TensorBoard'] + path_slash + 'LRFinder', 
													histogram_freq = 1
													)

		lr_schedule = tf.keras.callbacks.LearningRateScheduler(lambda epoch: min_learning_rate * 10**(epoch / 10))
		optimizer = tf.keras.optimizers.Adam(learning_rate = min_learning_rate)

		model.compile(
						optimizer = optimizer,
		              	loss = tf.keras.losses.SparseCategoricalCrossentropy(),
		             	metrics = ['accuracy']
		             )

		model.summary()

		history = model.fit(
						    train_data_gen,
						    steps_per_epoch = int(np.ceil(total_train / float(BATCH_SIZE))),
						    epochs = EPOCHS,
						    validation_data = val_data_gen,
							validation_steps = int(np.ceil(total_val / float(BATCH_SIZE))),
						    callbacks = [lr_schedule, tensor_board]
							)

		import matplotlib.pyplot as plt

		plt.semilogx(history.history["lr"], history.history["loss"])
		plt.axis([min_learning_rate, 1, 0, 1])
		plt.show()

		print(f'Model {model._name} LR Finding Finished ...')

	def Fitter(
				self, 
				model, 
				model_priority, 
				train_data_gen, 
				total_train, 
				val_data_gen, 
				total_val, 
				BATCH_SIZE, 
				EPOCHS = 1000, 
				patience = 50
				):

		print()
		print()

		print(f'Model {model._name} Fitting Strat ...')
		print()

		print("python.exe C:\\Users\\Mehrshad\\AppData\\Roaming\\Python\\Python38\\site-packages\\tensorboard\\main.py --logdir=C:\\Users\\Mehrshad\\Desktop\\ShadBot\\src\\utils\\MLModelGenerator\\Image\\Models\\TensorBoard\\Training")

		print()
		print()

		image_config = Config()

		#TensorBoard:
		if not os.path.exists(image_config.cfg['path_TensorBoard'] + path_slash + 'Training'): 
			os.makedirs(image_config.cfg['path_TensorBoard'] + path_slash + 'Training')
		else:
			shutil.rmtree(image_config.cfg['path_TensorBoard'] + path_slash + 'Training')

		tensor_board = tf.keras.callbacks.TensorBoard(
													log_dir = image_config.cfg['path_TensorBoard'] + path_slash + 'Training', 
													histogram_freq = 1
													)
		#////////////////////////////////////

		#Plot Model Flow Chart:
		if not os.path.exists(image_config.cfg['path_FlowChart']): os.makedirs(image_config.cfg['path_FlowChart'])
		tf.keras.utils.plot_model(
								model, 
								show_shapes = True, 
								to_file = image_config.cfg['path_FlowChart'] + path_slash + model._name + '.png'
								)
		#///////////////////////////////////

		model.summary()

		#Model Compile:
		model.compile(
						optimizer = tf.keras.optimizers.Adam(learning_rate = self.learning_rate),
		              	loss = tf.keras.losses.SparseCategoricalCrossentropy(),
		             	metrics = ['accuracy']
		             )
		#////////////////////////////////////

		#Model Check Points:
		early_stopping = tf.keras.callbacks.EarlyStopping(patience = patience)

		if model_priority == 'final':
			path_name = 'path_FinalTrainedModels'
		else:
			path_name = 'path_PreTrainedModels'

		if not os.path.exists(image_config.cfg[path_name]): os.makedirs(image_config.cfg[path_name])

		model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
															image_config.cfg[path_name] + path_slash + model._name + '.h5', 
															verbose = 0, 
															save_weights_only = False, 
															save_best_only=True
															)
		#/////////////////////////////////////

		#Model Fitting:
		history = model.fit(
						    train_data_gen,
						    steps_per_epoch = int(np.ceil(total_train / float(BATCH_SIZE))),
						    epochs = EPOCHS,
						    validation_data = val_data_gen,
						    validation_steps = int(np.ceil(total_val / float(BATCH_SIZE))),
						    callbacks = [early_stopping, model_checkpoint, tensor_board]
							)
		#/////////////////////////////////////

		print(f'Model {model._name} Fitting Finished ...')

		return history