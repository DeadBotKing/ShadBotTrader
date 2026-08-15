from Updater import MainDatasetUpdater

pc_name = 'DeadBot'
symbol = 'XAUUSD_i'

timeframes = ['5M', '15M', '1H', '4H', '1D']
candle_numbers = [99800, 30000, 8323, 2000, 600]

for timeframe, candle_number in zip(timeframes, candle_numbers):

	MainDatasetUpdater.DatasetUpdate(
									pc_name = pc_name,
									symbol = symbol,
									timeframe = timeframe,
									candle_number = candle_number
									)
