from src.utils.MLModelGenerator.TimeSeries.PricePredictor.ModelLoader import ModelLoader
from src.utils.MLModelGenerator.TimeSeries.PricePredictor.Trainer import Trainer
import tensorflow as tf

#Model Load ****************************************************
# model_loader = ModelLoader()
# model_high, model_low, path_high, path_low = model_loader.Load(
# 																	timeframe = '1D',
# 																	size_target = 1,
# 																	window_size = 500,
# 																	feature_names_high = ['salam', 'bye'],
# 																	feature_names_low = ['salam', 'bye'],
# 																	Trainable = True,
# 																)



# model_high.summary()
# model_low.summary()
#///////////////////////////////////////////////////////////////


#Model Fit ****************************************************

from src.utils.DatasetPreparer.TimeSeries.PricePredictorDatasetPreparer import PricePredictorDatasetPreparer
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
import pandas as pd


loging = getdata()
symbol = 'XAUUSD_i'
target = 'low'

_, _, _, _, dataset_1D = loging.readall(
										symbol = symbol, 
										number_5M = 0, 
										number_15M = 0, 
										number_1H = 0,
										number_4H = 0,
										number_1D = 'all'
										)

pricepredictordatasetpreparer = PricePredictorDatasetPreparer()
pricepredictordatasetpreparer.target_name = target

dataset_train, dataset_valid, dataset_test, feature_names_str = pricepredictordatasetpreparer.Run(
																									dataset_5M = pd.DataFrame(),
																									dataset_15M = pd.DataFrame(),
																									dataset_1H = pd.DataFrame(),
																									dataset_4H = pd.DataFrame(),
																									dataset_1D = dataset_1D,
																									symbol = symbol,
																									Mode = 'Learn',
																									NumberOfTest = 1
																									)


# counter = 0
# import matplotlib.pyplot as plt
# for x, y in dataset_train:
# 	if counter >= 0:
# 	# 	print('counter = ', counter)
# 		print('x = ', x.numpy())
# 		print('y = ', y.numpy())
# 		print('shape x = ', tf.shape(x))
# 		print('shape y = ', tf.shape(y))

# 		# plt.plot(x[: , target].numpy())
# 		# plt.plot(x.numpy())
# 		# plt.plot(range(size_target, window_size + size_target), y[:].numpy(), linestyle = '--', c = 'black')
# 		# plt.show()
	
# 	counter += 1

model_trainer = Trainer()
model_trainer.ModelTarget = target
model_trainer.Fitter(
					dataset_train = dataset_train,
					dataset_valid = dataset_valid,
					feature_names_high = feature_names_str, 
					feature_names_low = feature_names_str,
					Epochs = 100
					)
#///////////////////////////////////////////////////////////////
