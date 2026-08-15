from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata


def DatasetUpdate(
					pc_name = 'DeadBot',
					symbol = 'XAUUSD_i',
					timeframe = '5M',
					candle_number = 99800
					):

	loging = getdata()


	loging.account_name = pc_name
	loging.initilizer()
	loging.login()

	loging.Update(symbol = symbol, timeframe = timeframe, number = candle_number)