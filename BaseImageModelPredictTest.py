from src.utils.DatasetPreparer.Image.ImageWindowGenerator import ImageWindowGenerator
from src.utils.MLModelGenerator.Image.ModelTrainer import ModelTrainer
from src.utils.MLModelGenerator.Image.ImageModels import ImageModels
from src.utils.MLModelGenerator.Image.Names import ModelNames

import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
import cv2
import os
import sys

if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'

import winsound
frequency = 500  # Set Frequency To 2500 Hertz
duration = 1000  # Set Duration To 1000 ms == 1 second



#Reading Image Dataset: *******************************
image_window_generator = ImageWindowGenerator()
image_window_generator.ImageNames()
image_window_generator.ImageClassNames()

image_window_generator.BATCH_SIZE = 300
_, _, val_data_gen, _, _ = image_window_generator(
													image_name = 'GeneralImages', 
													class_names = ['buy', 'no_trade_buy']
													)

image_models = ImageModels()

# model = image_models.FinalModels(model_name = 'final_image_model_buy_sell', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_buy_no_trade', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_sell_no_trade', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_full_image_model_straight', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_full_image_model_complex', update = True)
model = image_models.FinalModels(model_name = 'final_image_model_double_full_image_model', update = True)

sample_valid_images, labels = next(val_data_gen)

print(val_data_gen)

def plotImages(images_arr):
	fig, axes = plt.subplots(1, 5, figsize=(20,20))
	axes = axes.flatten()
	for img, ax in zip(images_arr, axes):
		ax.imshow(img)
	plt.tight_layout()
	plt.show()


buy_counter = 0
sell_counter = 0
no_trade_counter = 0

for elm in labels:
	if elm == 0:
		buy_counter += 1
	elif elm == 1:
		sell_counter += 1
	elif elm == 2:
		no_trade_counter += 1

print('Number Buy: ', buy_counter)
print('Number Sell: ', sell_counter)
print('Number no_trade: ', no_trade_counter)
print()
# plotImages(np.shape(sample_valid_images[1]))
# print(np.shape(sample_valid_images[1]))

counter = 0
success = 0 
failed = 0
buy_signal_percent = []
sell_signal_percent = []
no_trade_signal_percent = []

buy_counter = 0
sell_counter = 0
no_trade_counter = 0

print('start ...')
for test_images in sample_valid_images:

	predictions = model.predict(test_images[np.newaxis, :, :, :], verbose = 0)


	# print('predict = ', predictions)
	# print('max = ', np.argmax(predictions))
	# print('general lable = ', labels[counter])

	if labels[counter] == np.argmax(predictions):
		success += 1

		if np.argmax(predictions) == 0 and predictions[0][np.argmax(predictions)] >= 0.9:
			buy_signal_percent.append(predictions[0][np.argmax(predictions)])
			buy_counter += 1

		if np.argmax(predictions) == 1 and predictions[0][np.argmax(predictions)] >= 0.9:
			sell_signal_percent.append(predictions[0][np.argmax(predictions)])
			sell_counter += 1

		# if np.argmax(predictions) == 2:
		# 	no_trade_signal_percent.append(predictions[0][np.argmax(predictions)])
		# 	no_trade_counter += 1

	else:
		failed += 1

	print(counter, sep=' ', end=" ", flush=True)

	counter += 1

print('success = ', success)
print('failed = ', failed)

print('min percent buy: ', np.min(buy_signal_percent))
print('max percent buy: ', np.max(buy_signal_percent))
print('mean percent buy: ', np.mean(buy_signal_percent))
print('Number Buy: ', buy_counter)
print()

print('min percent sell: ', np.min(sell_signal_percent))
print('max percent sell: ', np.max(sell_signal_percent))
print('mean percent sell: ', np.mean(sell_signal_percent))
print('Number Sell: ', sell_counter)
print()

print('min percent no_trade: ', np.min(no_trade_signal_percent))
print('max percent no_trade: ', np.max(no_trade_signal_percent))
print('mean percent no_trade: ', np.mean(no_trade_signal_percent))
print('Number no_trade: ', no_trade_counter)
print()
winsound.Beep(frequency, duration)