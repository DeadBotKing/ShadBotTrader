from src.utils.MLModelGenerator.Image.Config import Config
import tensorflow as tf
import numpy as np
import sys
import os

if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'

class Predictor:

	def __init__(self):

		image_config = Config()

		if os.path.exists(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_buy_sell' + '.h5'):

			self.final_image_model_buy_sell = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_buy_sell' + '.h5')
			self.final_image_model_buy_sell.trainable = False

		if os.path.exists(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_buy_no_trade' + '.h5'):

			self.final_image_model_buy_no_trade = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_buy_no_trade' + '.h5')
			self.final_image_model_buy_no_trade.trainable = False

		if os.path.exists(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_sell_no_trade' + '.h5'):

			self.final_image_model_sell_no_trade = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_sell_no_trade' + '.h5')
			self.final_image_model_sell_no_trade.trainable = False

		if os.path.exists(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_full_image_model_complex' + '.h5'):

			self.final_image_model_full_image_model_complex = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_full_image_model_complex' + '.h5')
			self.final_image_model_full_image_model_complex.trainable = False

		if os.path.exists(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_full_image_model_straight' + '.h5'):

			self.final_image_model_full_image_model_straight = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_full_image_model_straight' + '.h5')
			self.final_image_model_full_image_model_straight.trainable = False

		if os.path.exists(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_double_full_image_model' + '.h5'):

			self.final_image_model_double_full_image_model = tf.keras.models.load_model(image_config.cfg['path_FinalTrainedModels'] + path_slash + 'final_image_model_double_full_image_model' + '.h5')
			self.final_image_model_double_full_image_model.trainable = False

	
	def SignalClusterer(self, signal, model_name):

		if model_name == 'final_image_model_buy_sell':

			if signal == 0:
				signal_out = 'buy'
			elif signal == 1:
				signal_out = 'sell'
		#/////////////////////

		elif model_name == 'final_image_model_buy_no_trade':

			if signal == 0:
				signal_out = 'buy'
			elif signal == 1:
				signal_out = 'no_trade'
		#//////////////////////

		elif model_name == 'final_image_model_sell_no_trade':

			if signal == 0:
				signal_out = 'sell'
			elif signal == 1:
				signal_out = 'no_trade'

		elif (
				model_name == 'final_image_model_double_full_image_model' or
				model_name == 'final_image_model_full_image_model_straight' or
				model_name == 'final_image_model_full_image_model_complex'
			):
			
			if signal == 0: 
				signal_out = 'buy'
			elif signal == 1:
				signal_out = 'sell'
			elif signal == 2:
				signal_out = 'no_trade'

		else:
			signal_out = 'no_trade'

		return signal_out

	def __call__(self, model_name, signal_image):

		if model_name == 'final_image_model_buy_sell':
			model = self.final_image_model_buy_sell

		elif model_name == 'final_image_model_buy_no_trade':
			model = self.final_image_model_buy_no_trade

		elif model_name == 'final_image_model_sell_no_trade':
			model = self.final_image_model_sell_no_trade

		elif model_name == 'final_image_model_full_image_model_straight':
			model = self.final_image_model_full_image_model_straight

		elif model_name == 'final_image_model_full_image_model_complex':
			model = self.final_image_model_full_image_model_complex

		elif model_name == 'final_image_model_double_full_image_model':
			model = self.final_image_model_double_full_image_model

		signal_predict = model.predict(signal_image[np.newaxis, :, :, :], verbose = 0)

		signal = np.argmax(signal_predict)
		signal_out = self.SignalClusterer(signal = signal, model_name = model_name)

		percent = signal_predict[0][np.argmax(signal_predict)]

		return signal_out, percent