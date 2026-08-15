from .Config import Config
import pandas as pd
import os


#Functions:

#Read()
#Write()
#Delete()

#*************

class DatasetIO:

	def Read(self, type_feature, name, symbol):

		dataset_config = Config()

		path = dataset_config.cfg['path_' + type_feature] + symbol + '_' + name + '.csv'

		if os.path.exists(path):
			dataset = pd.read_csv(path)

			if 'Unnamed' in dataset.columns[0]:
				dataset = dataset.drop(columns = ['Unnamed: 0'])

		else:
			dataset = pd.DataFrame()

		return dataset


	def Write(self, dataset, type_feature , name, symbol):

		dataset_config = Config()

		path = dataset_config.cfg['path_' + type_feature] + symbol + '_' + name + '.csv'

		if os.path.exists(dataset_config.cfg['path_' + type_feature]):

			if os.path.exists(path):
				os.remove(path)
			dataset = dataset.to_csv(path)

		else:
			os.makedirs(dataset_config.cfg['path_' + type_feature])
			dataset = dataset.to_csv(path)

	def Delete(self, type_feature , name, symbol):

		dataset_config = Config()

		
		path = dataset_config.cfg['path_' + type_feature] + symbol + '_' + name + '.csv'

		if os.path.exists(path):
			os.remove(path)