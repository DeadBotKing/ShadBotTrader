from src.utils.MLModelGenerator.Image.Config import Config
import tensorflow as tf
import sys
import os

if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'


class ImageModels:

	def __init__(self):

		self.IMG_SHAPE_X = 147
		self.IMG_SHAPE_Y = 200
		self.IMG_SHAPE_Z = 3
		self.dropout_layer_flag = False
		self.dropout_layer_percent = 0.2

	def ConcreteModel(self, model_name, num_clusters = 2):

		input_image = tf.keras.layers.Input(
											shape = (self.IMG_SHAPE_X, self.IMG_SHAPE_Y, self.IMG_SHAPE_Z), 
											dtype = tf.float32,
											name = model_name + '_input' 
											)

		model = tf.keras.models.Sequential([input_image], name = model_name)

		conv_counter = 1
		for i in range(0, 6):
			model.add(
						tf.keras.layers.Conv2D(
			    								filters = 32, 
			    								strides = (1, 1), 
			    								kernel_size = (2, 2),
			    								padding = 'same', 
			    								activation = 'tanh',
			    								name = model_name + '_Conv_' + str(i + conv_counter)
			    								)
						)

			conv_counter += 1

			model.add(
				    	tf.keras.layers.Conv2D(
			    								filters = 16, 
			    								strides = (1, 1), 
			    								kernel_size = (2, 2),
			    								padding = 'same', 
			    								activation = 'tanh',
			    								name = model_name + '_Conv_' + str(i + conv_counter)
			    								)
				    	)

			conv_counter += 1

			model.add(
				    	tf.keras.layers.Conv2D(
			    								filters = 16, 
			    								strides = (2, 2), 
			    								kernel_size = (2, 2),
			    								padding = 'same', 
			    								activation = 'tanh',
			    								name = model_name + '_Conv_' + str(i + conv_counter)
			    								)
						)

			if self.dropout_layer_flag == True:
				model.add(tf.keras.layers.Dropout(self.dropout_layer_percent))

			conv_counter += 1
			out_i = i

		model.add(
					tf.keras.layers.Conv2D(
		    								filters = 32, 
		    								strides = (1, 1), 
		    								kernel_size = (2, 2),
		    								padding = 'same', 
		    								activation = 'tanh',
		    								name = model_name + '_Conv_' + str(out_i + conv_counter)
		    								),
				)

		if self.dropout_layer_flag == True:
			model.add(tf.keras.layers.Dropout(self.dropout_layer_percent))

		model.add(tf.keras.layers.Flatten())
		model.add(tf.keras.layers.Dense(num_clusters * 6, activation = 'tanh', name = model_name + '_Dense_1'))

		if self.dropout_layer_flag == True:
			model.add(tf.keras.layers.Dropout(self.dropout_layer_percent))

		model.add(tf.keras.layers.Dense(num_clusters * num_clusters, activation = 'swish', name = model_name + '_Dense_2'))
		model.add(tf.keras.layers.Dense(num_clusters, activation = tf.nn.softmax, name = model_name + '_output'))

		return model

	def ComplexModelPre(self):

		model_name = 'full_image_model_complex'
		input_img = tf.keras.layers.Input(
											shape = (self.IMG_SHAPE_X, self.IMG_SHAPE_Y, self.IMG_SHAPE_Z), 
											dtype = tf.float32, 
											name = model_name + '_input'
										)
		image_config = Config()

		model_buy_sell = tf.keras.models.load_model(image_config.cfg['path_PreTrainedModels'] + path_slash + 'buy_sell.h5')
		model_buy_sell.trainable = False
		model_buy_sell._name = 'buy_sell'

		model_buy_no_trade = tf.keras.models.load_model(image_config.cfg['path_PreTrainedModels'] + path_slash + 'buy_no_trade.h5')
		model_buy_no_trade.trainable = False
		model_buy_no_trade._name = 'buy_no_trade'

		model_sell_no_trade = tf.keras.models.load_model(image_config.cfg['path_PreTrainedModels'] + path_slash + 'sell_no_trade.h5')
		model_sell_no_trade.trainable = False
		model_sell_no_trade._name = 'sell_no_trade'

		#Branch Buy Sell: **********
		branch_buy_sell = model_buy_sell(input_img)
		branch_buy_sell = tf.keras.layers.Dense(6, name = model_name + '_Dense_buy_sell')(branch_buy_sell)
		#///////////////////////////////////

		#Branch Buy No Trade: **********
		branch_buy_no_trade = model_buy_no_trade(input_img)
		branch_buy_no_trade = tf.keras.layers.Dense(6, name = model_name + '_Dense_buy_no_trade')(branch_buy_no_trade)
		#///////////////////////////////////

		#Branch Sell No Trade: **********
		branch_sell_no_trade = model_sell_no_trade(input_img)
		branch_sell_no_trade = tf.keras.layers.Dense(6, name = model_name + '_Dense_sell_no_trade')(branch_sell_no_trade)
		#///////////////////////////////////

		#Concat Branches: ***************
		concat_layer = tf.keras.layers.concatenate([branch_buy_sell, branch_buy_no_trade, branch_sell_no_trade], name = model_name + '_concat')
		#///////////////////////////////////

		#Layer Dense: *******************
		increase_layer = tf.keras.layers.Dense(27, activation = 'tanh', name = model_name + '_increase_1')(concat_layer)
		increase_layer = tf.keras.layers.Dense(6, activation = 'tanh', name = model_name + '_increase_2')(increase_layer)
		#////////////////////////////////////

		#Cluster Layer: ****************
		output = tf.keras.layers.Dense(3, activation = tf.nn.softmax, name = model_name + '_output')(increase_layer)
		#//////////////////////////////////

		full_image_model_complex = tf.keras.Model(input_img, output, name = model_name)
		
		return full_image_model_complex

	def StraightModelPre(self):

		model_name = 'full_image_model_straight'

		full_image_model_straight = self.ConcreteModel(model_name = model_name, num_clusters = 3)

		return full_image_model_straight

	def DoubleModelPre(self):

		model_name = 'double_full_image_model'

		input_img = tf.keras.layers.Input(
											shape = (self.IMG_SHAPE_X, self.IMG_SHAPE_Y, self.IMG_SHAPE_Z), 
											dtype = tf.float32, 
											name = model_name + '_input'
										)
		image_config = Config()

		full_image_model_complex = tf.keras.models.load_model(image_config.cfg['path_PreTrainedModels'] + path_slash + 'full_image_model_complex.h5')
		full_image_model_complex.trainable = False
		full_image_model_complex._name = 'full_image_model_complex'

		full_image_model_straight = tf.keras.models.load_model(image_config.cfg['path_PreTrainedModels'] + path_slash + 'full_image_model_straight.h5')
		full_image_model_straight.trainable = False
		full_image_model_straight._name = 'full_image_model_straight'

		#*******************************
		branch_full_image_model_complex = full_image_model_complex(input_img)
		branch_full_image_model_complex = tf.keras.layers.Dense(6, name = model_name + '_Dense_full_image_model_complex')(branch_full_image_model_complex)
		#//////////////////////////////////////

		#*******************************
		branch_full_image_model_straight = full_image_model_straight(input_img)
		branch_full_image_model_straight = tf.keras.layers.Dense(6, name = model_name + '_Dense_full_image_model_straight')(branch_full_image_model_straight)
		#//////////////////////////////////////

		#Concat Branches: ***************
		concat_layer = tf.keras.layers.concatenate([branch_full_image_model_complex, branch_full_image_model_straight], name = model_name + '_concat')
		#///////////////////////////////////

		#Layer Dense: *******************
		increase_layer = tf.keras.layers.Dense(24, activation = 'tanh', name = model_name + '_increase_1')(concat_layer)
		increase_layer = tf.keras.layers.Dense(6, activation = 'tanh', name = model_name + '_increase_2')(increase_layer)
		#////////////////////////////////////

		#Cluster Layer: ****************
		output = tf.keras.layers.Dense(3, activation = tf.nn.softmax, name = model_name + '_output')(increase_layer)
		#//////////////////////////////////

		double_full_image_model = tf.keras.Model(input_img, output, name = model_name)

		return double_full_image_model

	def ComplexModelFinal(self):

		model_name = 'final_image_model_full_image_model_complex'
		input_img = tf.keras.layers.Input(
											shape = (self.IMG_SHAPE_X, self.IMG_SHAPE_Y, self.IMG_SHAPE_Z), 
											dtype = tf.float32, 
											name = model_name + '_input'
										)
		image_config = Config()

		model_buy_sell = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_' + 'buy_sell.h5')
		model_buy_sell.trainable = False

		model_buy_no_trade = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_' + 'buy_no_trade.h5')
		model_buy_no_trade.trainable = False

		model_sell_no_trade = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_' + 'sell_no_trade.h5')
		model_sell_no_trade.trainable = False

		#Branch Buy Sell: **********
		branch_buy_sell = model_buy_sell(input_img)
		branch_buy_sell = tf.keras.layers.Dense(6, name = model_name + '_Dense_buy_sell')(branch_buy_sell)
		#///////////////////////////////////

		#Branch Buy No Trade: **********
		branch_buy_no_trade = model_buy_no_trade(input_img)
		branch_buy_no_trade = tf.keras.layers.Dense(6, name = model_name + '_Dense_buy_no_trade')(branch_buy_no_trade)
		#///////////////////////////////////

		#Branch Sell No Trade: **********
		branch_sell_no_trade = model_sell_no_trade(input_img)
		branch_sell_no_trade = tf.keras.layers.Dense(6, name = model_name + '_Dense_sell_no_trade')(branch_sell_no_trade)
		#///////////////////////////////////

		#Concat Branches: ***************
		concat_layer = tf.keras.layers.concatenate([branch_buy_sell, branch_buy_no_trade, branch_sell_no_trade], name = model_name + '_concat')
		#///////////////////////////////////

		#Layer Dense: *******************
		increase_layer = tf.keras.layers.Dense(27, activation = 'tanh', name = model_name + '_increase_1')(concat_layer)
		increase_layer = tf.keras.layers.Dense(6, activation = 'tanh', name = model_name + '_increase_2')(increase_layer)
		#////////////////////////////////////

		#Cluster Layer: ****************
		output = tf.keras.layers.Dense(3, activation = tf.nn.softmax, name = model_name + '_output')(increase_layer)
		#//////////////////////////////////

		final_full_image_model_complex = tf.keras.Model(input_img, output, name = model_name)
		
		return final_full_image_model_complex

	def DoubleModelFinal(self):

		model_name = 'final_image_model_double_full_image_model'

		input_img = tf.keras.layers.Input(
											shape = (self.IMG_SHAPE_X, self.IMG_SHAPE_Y, self.IMG_SHAPE_Z), 
											dtype = tf.float32, 
											name = model_name + '_input'
										)
		image_config = Config()

		full_image_model_complex = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_full_image_model_complex.h5')
		full_image_model_complex.trainable = False

		full_image_model_straight = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_full_image_model_straight.h5')
		full_image_model_straight.trainable = False

		#*******************************
		branch_full_image_model_complex = full_image_model_complex(input_img)
		branch_full_image_model_complex = tf.keras.layers.Dense(6, name = model_name + '_Dense_full_image_model_complex')(branch_full_image_model_complex)
		#//////////////////////////////////////

		#*******************************
		branch_full_image_model_straight = full_image_model_straight(input_img)
		branch_full_image_model_straight = tf.keras.layers.Dense(6, name = model_name + '_Dense_full_image_model_straight')(branch_full_image_model_straight)
		#//////////////////////////////////////

		#Concat Branches: ***************
		concat_layer = tf.keras.layers.concatenate([branch_full_image_model_complex, branch_full_image_model_straight], name = model_name + '_concat')
		#///////////////////////////////////

		#Layer Dense: *******************
		increase_layer = tf.keras.layers.Dense(24, activation = 'tanh', name = model_name + '_increase_1')(concat_layer)
		increase_layer = tf.keras.layers.Dense(6, activation = 'tanh', name = model_name + '_increase_2')(increase_layer)
		#////////////////////////////////////

		#Cluster Layer: ****************
		output = tf.keras.layers.Dense(3, activation = tf.nn.softmax, name = model_name + '_output')(increase_layer)
		#//////////////////////////////////

		final_double_full_image_model = tf.keras.Model(input_img, output, name = model_name)

		return final_double_full_image_model

	def FinalModels(self, model_name, update = False):

		image_config = Config()

		if os.path.exists(image_config.cfg['path_FinalTrainedModels'] + path_slash + model_name + '.h5') and update == True:

			final_image_model = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + model_name + '.h5')
			final_image_model.trainable = True

		else:

			if model_name == 'final_image_model_full_image_model_complex':
				final_image_model = self.ComplexModelFinal()

			elif model_name == 'final_image_model_double_full_image_model':
				final_image_model = self.DoubleModelFinal()

			else:
				final_image_model = tf.keras.models.load_model(image_config.cfg['path_PreTrainedModels'] + path_slash + model_name.split('final_image_model_')[1] + '.h5')
				final_image_model.trainable = True
				final_image_model._name = model_name

		return final_image_model
