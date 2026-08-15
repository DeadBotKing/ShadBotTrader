from src.utils.Photographer.Photographer import Photographer
from src.utils.DatasetPreparer.BaseImageDatasetPreparer import BaseImageDatasetPreparer
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
import pandas as pd
import numpy
import cv2
from mlxtend.preprocessing import minmax_scaling

loging = getdata()

dataset_5M = pd.DataFrame()
dataset_15M = pd.DataFrame()
dataset_1H = pd.DataFrame()

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = 'XAUUSD_i', number_5M = 'all', number_15M = 'all', number_1H = 'all')


base_image_dataset_preparer = BaseImageDatasetPreparer()

base_image_dataset_preparer.percent_zigzag_finder = 0.25
base_image_dataset_preparer.profit = 0.4

base_image_dataset_preparer.Run(
								dataset_5M = dataset_5M, 
								dataset_15M = dataset_15M, 
								dataset_1H = dataset_1H, 
								image_size = 200,
								symbol = 'XAUUSD_i'
								)
