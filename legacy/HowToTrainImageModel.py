from src.utils.DatasetPreparer.Image.ImageWindowGenerator import ImageWindowGenerator
from src.utils.MLModelGenerator.Image.ModelTrainer import ModelTrainer
from src.utils.MLModelGenerator.Image.ImageModels import ImageModels
from src.utils.MLModelGenerator.Image.Names import ModelNames
import numpy as np


#Reading Image Dataset: *******************************
image_window_generator = ImageWindowGenerator()
image_window_generator.ImageNames()
image_window_generator.ImageClassNames()

image_window_generator.BATCH_SIZE = 200
train_data_gen, total_train, val_data_gen, total_valid, BATCH_SIZE = image_window_generator(
																							image_name = 'GeneralImages', 
																							class_names = ['buy', 'sell', 'no_trade']
																							)
 
# 42/42 [==============================] - 242s 6s/step - loss: 0.1346 - accuracy: 0.9655  Double General
# 2/2 [==============================] - 10s 3s/step - loss: 1.4497 - accuracy: 0.5955     Double

# 42/42 [==============================] - 167s 4s/step - loss: 0.1658 - accuracy: 0.9538  Complex General
# 2/2 [==============================] - 7s 2s/step - loss: 1.2678 - accuracy: 0.6242      Complex

# 42/42 [==============================] - 65s 2s/step - loss: 0.1625 - accuracy: 0.9530   Straight General
# 2/2 [==============================] - 3s 792ms/step - loss: 1.5969 - accuracy: 0.5637   Straight

import matplotlib.pyplot as plt

sample_training_images, _ = next(train_data_gen)

def plotImages(images_arr):
	fig, axes = plt.subplots(1, 5, figsize=(20,20))
	axes = axes.flatten()
	for img, ax in zip(images_arr, axes):
		ax.imshow(img)
	plt.tight_layout()
	plt.show()

# plotImages(sample_training_images[:5])  # Plot images 0-4
#///////////////////////////////////////////////////////////////////////////////////

#Creating Models: ******************************
image_models = ImageModels()
ModelNames()

image_models.dropout_layer_flag = False
image_models.dropout_layer_percent = 0.2

#Pre Models:
# model = image_models.ConcreteModel(model_name = 'buy_sell', num_clusters = 2)
# model = image_models.ConcreteModel(model_name = 'buy_no_trade', num_clusters = 2)
# model = image_models.ConcreteModel(model_name = 'sell_no_trade', num_clusters = 2)
# model = image_models.StraightModelPre()
# model = image_models.ComplexModelPre()
# model = image_models.DoubleModelPre()
#/////////////////////////////////////////////

#Final Models:
# model = image_models.FinalModels(model_name = 'final_image_model_buy_sell', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_buy_no_trade', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_sell_no_trade', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_full_image_model_straight', update = True)
model = image_models.FinalModels(model_name = 'final_image_model_full_image_model_complex', update = True)
# model = image_models.FinalModels(model_name = 'final_image_model_double_full_image_model', update = True)
#/////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////////////////

#Models Training: Finding Learning Rate *********
model_trainer = ModelTrainer(model = model)
# model_trainer.LRFinder(
# 						model = model, 
# 						train_data_gen = train_data_gen, 
# 						total_train = total_train, 
# 						val_data_gen = val_data_gen, 
# 						total_val = total_valid, 
# 						BATCH_SIZE = BATCH_SIZE,
# 						min_learning_rate = 1e-5,
# 						EPOCHS = 100
# 						)

hist = model.evaluate(
						x = val_data_gen,
						y = None,
						batch_size = BATCH_SIZE,
						steps = int(np.ceil(total_valid / float(BATCH_SIZE)))
						)

# model_trainer.Fitter(
# 					model = model, 
# 					model_priority = 'final', #'final', #None,
# 					train_data_gen = train_data_gen, 
# 					total_train = total_train, 
# 					val_data_gen = val_data_gen, 
# 					total_val = total_valid, 
# 					BATCH_SIZE = BATCH_SIZE,
# 					EPOCHS = 1000, 
# 					patience = 50
# 					)

#///////////////////////////////////////////////////////////////////////////////////
