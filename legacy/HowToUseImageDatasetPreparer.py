from src.utils.DatasetPreparer.Image.ImageDatasetPreparer import ImageDatasetPreparer
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
import warnings as warnings
import pandas as pd
warnings.filterwarnings("ignore")

loging = getdata()

dataset_5M = pd.DataFrame()
dataset_15M = pd.DataFrame()
dataset_1H = pd.DataFrame()

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = 'XAUUSD_i', number_5M = 'all', number_15M = 'all', number_1H = 'all')

dataset_5M = dataset_5M['XAUUSD_i']
dataset_15M = dataset_15M['XAUUSD_i']
dataset_1H = dataset_1H['XAUUSD_i']


image_dataset_preparer = ImageDatasetPreparer()

image_dataset_preparer.percent_zigzag_finder = 5
image_dataset_preparer.profit = 10

image_dataset_preparer.RunOffline(
                                  dataset_5M = dataset_5M,
                                  dataset_15M = dataset_15M,
                                  dataset_1H = dataset_1H,
                                  image_size = 1000,
                                  symbol = 'XAUUSD_i'
                                  )