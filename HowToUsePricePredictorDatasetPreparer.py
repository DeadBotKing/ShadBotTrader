from src.utils.DatasetPreparer.TimeSeries.PricePredictorDatasetPreparer import PricePredictorDatasetPreparer
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
import pandas as pd


loging = getdata()
symbol = 'XAUUSD_i'

_, _, _, _, dataset_1D = loging.readall(
										symbol = symbol, 
										number_5M = 0, 
										number_15M = 0, 
										number_1H = 0,
										number_4H = 0,
										number_1D = 'all'
										)

pricepredictordatasetpreparer = PricePredictorDatasetPreparer()

pricepredictordatasetpreparer.Run(
									dataset_5M = pd.DataFrame(),
									dataset_15M = pd.DataFrame(),
									dataset_1H = pd.DataFrame(),
									dataset_4H = pd.DataFrame(),
									dataset_1D = dataset_1D,
									symbol = symbol,
									Mode = 'Learn',
									NumberOfTest = 1
									)