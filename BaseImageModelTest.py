from src.utils.DatasetPreparer.Config import Config as BaseImageModelConfig
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import tensorflow_datasets as tfds
import tensorflow_hub as hub
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import logging
import os

# import urllib
# import urllib.request

# urllib.request.urlretrieve("http://wordpress.org/latest.tar.gz", "/thefile.gz")

tfds.disable_progress_bar()
logger = tf.get_logger()
logger.setLevel(logging.ERROR)

tf.random.set_seed(50)
np.random.seed(50)

# dataset, metadata = tfds.load('fashion_mnist', as_supervised=True, with_info=True)

sample_training_images, _ = next(train_data_gen)

def plotImages(images_arr):
	fig, axes = plt.subplots(1, 5, figsize=(20,20))
	axes = axes.flatten()
	for img, ax in zip(images_arr, axes):
		ax.imshow(img)
	plt.tight_layout()
	plt.show()

# plotImages(sample_training_images[:5])  # Plot images 0-4

# image_model = tf.keras.models.load_model("mehrshad_image_net.h5", custom_objects={'KerasLayer':hub.KerasLayer})

# tf.keras.applications.ConvNeXtXLarge(
# 									    model_name="convnext_xlarge",
# 									    include_top=False,
# 									    include_preprocessing=True,
# 									    weights="imagenet",
# 									    input_tensor=None,
# 									    input_shape=(9, 200, 3),
# 									    pooling=None,
# 									    # classes=1000,
# 									    # classifier_activation="softmax",
# 									)

# model_mobile = tf.keras.applications.MobileNetV2(
# 													input_shape = (IMG_SHAPE, IMG_SHAPE, 3),
# 													alpha = 1.4,
# 													include_top = True,
# 													weights = None,
# 													input_tensor = None,
# 													pooling = True,
# 													classes = 2,
# 													classifier_activation = "softmax"
# 												)

# model_mobile.trainable = True



full_image_model_complex = tf.keras.models.load_model('Models/full_image_model.h5')
full_image_model_complex.trainable = False
full_image_model_complex._name = 'full_image_model_complex'

full_image_model_straight = tf.keras.models.load_model('Models/full_image_model_straight.h5')
full_image_model_straight.trainable = False

full_image_model = tf.keras.models.load_model('final_full_image_model.tf')
full_image_model.trainable = False

hist = full_image_model_straight.evaluate(
										    x = test_data_gen,
										    y=None,
										    batch_size = BATCH_SIZE,
										    steps=int(np.ceil(total_test / float(BATCH_SIZE)))
										)

hist = full_image_model_complex.evaluate(
										    x = val_data_gen,
										    y=None,
										    batch_size = BATCH_SIZE,
										    steps=int(np.ceil(total_val / float(BATCH_SIZE)))
										)

hist = full_image_model.evaluate(
								    x = val_data_gen,
								    y=None,
								    batch_size = BATCH_SIZE,
								    steps=int(np.ceil(total_val / float(BATCH_SIZE)))
								)

print(hist)
sys.exit()

#Plot Model: ***************************************
tf.keras.utils.plot_model(model, show_shapes = True, to_file = 'buy_sell.png')
#////////////////////////////////////////////////////////

#TensorBoard Model: ***************************************
tensor_board = tf.keras.callbacks.TensorBoard(log_dir = 'buy_sell', histogram_freq = 1)
#http://localhost:6006/
#python.exe C:\Users\Mehrshad\AppData\Roaming\Python\Python38\site-packages\tensorboard\main.py --logdir=C:\Users\Mehrshad\Desktop\ShadBot\buy_sell
#////////////////////////////////////////////////////////

#LR Schedule: **************************************

# lr_schedule = tf.keras.callbacks.LearningRateScheduler(lambda epoch: 1e-5 * 10**(epoch / 10))
# optimizer = tf.keras.optimizers.Adam(learning_rate = 1e-5)

# # model.build(input_shape)

# model.compile(
# 				optimizer = optimizer,
#               	loss=tf.keras.losses.SparseCategoricalCrossentropy(),
#               	# loss = tf.keras.losses.BinaryCrossentropy(from_logits=True),
#              	metrics = ['accuracy']
#              )

# model.summary()

# EPOCHS = 70
# history = model.fit(
# 				    train_data_gen,
# 				    steps_per_epoch=int(np.ceil(total_train / float(BATCH_SIZE))),
# 				    epochs=EPOCHS,
# 				    validation_data=val_data_gen,
# 					validation_steps=int(np.ceil(total_val / float(BATCH_SIZE))),
# 				    callbacks=[lr_schedule, tensor_board]
# 					)

# import matplotlib.pyplot as plt

# plt.semilogx(history.history["lr"], history.history["loss"])
# plt.axis([1e-6, 1, 0, 1])
# plt.show()
# sys.exit()
#////////////////////////////////////////////////////////////
#1e-3
#5e-3
#1e-3

model.compile(
				optimizer = tf.keras.optimizers.Adam(learning_rate = 1e-4),
              	loss = tf.keras.losses.SparseCategoricalCrossentropy(),
              	# loss = tf.keras.losses.Huber(),
             	metrics = ['accuracy']
             )

model.summary()

early_stopping = tf.keras.callbacks.EarlyStopping(patience=50)
model_checkpoint = tf.keras.callbacks.ModelCheckpoint("final_full_image_model.tf", verbose = 0, save_weights_only = False, save_best_only=True)

EPOCHS = 1000

history = model.fit(
				    train_data_gen,
				    steps_per_epoch=int(np.ceil(total_train / float(BATCH_SIZE))),
				    epochs=EPOCHS,
				    validation_data=val_data_gen,
				    validation_steps=int(np.ceil(total_val / float(BATCH_SIZE))),
				    callbacks=[early_stopping, model_checkpoint, tensor_board]
					)

acc = history.history['accuracy']
val_acc = history.history['val_accuracy']

loss = history.history['loss']
val_loss = history.history['val_loss']

epochs_range = range(EPOCHS)

plt.figure(figsize=(8, 8))
plt.subplot(1, 2, 1)
plt.plot(acc, label='Training Accuracy')
plt.plot(val_acc, label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Training and Validation Accuracy')

plt.subplot(1, 2, 2)
plt.plot(loss, label='Training Loss')
plt.plot(val_loss, label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Training and Validation Loss')
plt.savefig('./foo.png')
plt.show()






