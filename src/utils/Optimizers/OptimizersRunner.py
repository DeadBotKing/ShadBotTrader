from src.utils.Optimizers import Optimizers
from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
import threading
import time

class OptimizersRunner():

	def __init__(self):

		self.symbol = 'XAUUSD_i'
		self.timeframe = '5M'
		self.turn = 100

	def TaskMACD(self, timeframe, sigtype, sigpriority):
		loging = getdata()

		if timeframe == '5M':
			dataset, _, _, _, _ = loging.readall(symbol = self.symbol, number_5M = 'all', number_15M = 0, number_1H = 0, number_4H = 0, number_1D = 0)
		if timeframe == '15M':
			_, dataset, _, _, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 'all', number_1H = 0, number_4H = 0, number_1D = 0)
		if timeframe == '1H':
			_, _, dataset, _, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 'all', number_4H = 0, number_1D = 0)
		if timeframe == '4H':
			_, _, _, dataset, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 0, number_4H = 'all', number_1D = 0)
		if timeframe == '1D':
			_, _, _, _, dataset = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 0, number_4H = 0, number_1D = 'all')

		optimizers = Optimizers.Optimizers() 

		optimizers.symbol = self.symbol
		optimizers.sigpriority = sigpriority
		optimizers.sigtype = sigtype
		optimizers.turn = self.turn
		optimizers.dataset = dataset.copy()
		optimizers.timeframe = timeframe

		job_thread = threading.Thread(target = optimizers.MacdOptimizer)

		return job_thread

	def MACDRunner(self):

		try:
		 	self.TaskMACD(timeframe = self.timeframe, sigtype = 'buy', sigpriority = 'primary').start()
		 	self.TaskMACD(timeframe = self.timeframe, sigtype = 'buy', sigpriority = 'secondry').start()
		 	self.TaskMACD(timeframe = self.timeframe, sigtype = 'sell', sigpriority = 'primary').start()
		 	self.TaskMACD(timeframe = self.timeframe, sigtype = 'sell', sigpriority = 'secondry').start()

		except Exception as ex:
			print('MACD Optimizer ERROR: ', ex)


	def TaskStochAstic(self, timeframe, sigtype, sigpriority):
		loging = getdata()

		if timeframe == '5M':
			dataset, _, _, _, _ = loging.readall(symbol = self.symbol, number_5M = 'all', number_15M = 0, number_1H = 0, number_4H = 0, number_1D = 0)
		if timeframe == '15M':
			_, dataset, _, _, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 'all', number_1H = 0, number_4H = 0, number_1D = 0)
		if timeframe == '1H':
			_, _, dataset, _, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 'all', number_4H = 0, number_1D = 0)
		if timeframe == '4H':
			_, _, _, dataset, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 0, number_4H = 'all', number_1D = 0)
		if timeframe == '1D':
			_, _, _, _, dataset = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 0, number_4H = 0, number_1D = 'all')


		optimizers = Optimizers.Optimizers() 

		optimizers.symbol = self.symbol
		optimizers.sigpriority = sigpriority
		optimizers.sigtype = sigtype
		optimizers.turn = self.turn
		optimizers.dataset = dataset.copy()
		optimizers.timeframe = timeframe

		job_thread = threading.Thread(target = optimizers.StochAsticOptimizer)

		return job_thread

	def StochAsticRunner(self):

		try:

		 	self.TaskStochAstic(timeframe = self.timeframe, sigtype = 'buy', sigpriority = 'primary').start()
		 	self.TaskStochAstic(timeframe = self.timeframe, sigtype = 'buy', sigpriority = 'secondry').start()
		 	self.TaskStochAstic(timeframe = self.timeframe, sigtype = 'sell', sigpriority = 'primary').start()
		 	self.TaskStochAstic(timeframe = self.timeframe, sigtype = 'sell', sigpriority = 'secondry').start()

		except Exception as ex:
			print('StochAstic Optimizer ERROR: ', ex)


	def TaskRSI(self, timeframe, sigtype, sigpriority):
		loging = getdata()

		if timeframe == '5M':
			dataset, _, _, _, _ = loging.readall(symbol = self.symbol, number_5M = 'all', number_15M = 0, number_1H = 0, number_4H = 0, number_1D = 0)
		if timeframe == '15M':
			_, dataset, _, _, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 'all', number_1H = 0, number_4H = 0, number_1D = 0)
		if timeframe == '1H':
			_, _, dataset, _, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 'all', number_4H = 0, number_1D = 0)
		if timeframe == '4H':
			_, _, _, dataset, _ = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 0, number_4H = 'all', number_1D = 0)
		if timeframe == '1D':
			_, _, _, _, dataset = loging.readall(symbol = self.symbol, number_5M = 0, number_15M = 0, number_1H = 0, number_4H = 0, number_1D = 'all')


		optimizers = Optimizers.Optimizers() 

		optimizers.symbol = self.symbol
		optimizers.sigpriority = sigpriority
		optimizers.sigtype = sigtype
		optimizers.turn = self.turn
		optimizers.dataset = dataset.copy()
		optimizers.timeframe = timeframe

		job_thread = threading.Thread(target = optimizers.RSIOptimizer)

		return job_thread

	def RSIRunner(self):

		try:

		 	self.TaskRSI(timeframe = self.timeframe, sigtype = 'buy', sigpriority = 'primary').start()
		 	self.TaskRSI(timeframe = self.timeframe, sigtype = 'buy', sigpriority = 'secondry').start()
		 	self.TaskRSI(timeframe = self.timeframe, sigtype = 'sell', sigpriority = 'primary').start()
		 	self.TaskRSI(timeframe = self.timeframe, sigtype = 'sell', sigpriority = 'secondry').start()

		except Exception as ex:
			print('RSI Optimizer ERROR: ', ex)


	def Run(self):

		self.MACDRunner()
		self.StochAsticRunner()
		self.RSIRunner()

		
