from .Config import accountConfig
from datetime import datetime

try:
	from MetaTrader5 import *
	import MetaTrader5 as mt5
except Exception as ex:
	print('login get data : ',ex)

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path, PurePosixPath
import os
import sys


if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'

#********* Methodes:

#login()
#getall()
#getone()
#writer()
#readone()
#readall()
#get_symbols()
#get_balance()
#initilizer()

#/////////////////////

main_path_dataset = Path(__file__).parent

class LoginGetData:

	def __init__(self): self.account_name = ''

	def getall(self, timeframe, number):

		symbols = self.get_symbols()
		symbol_data = {}

		for sym in symbols:
			try:
				data = self.getone(timeframe = timeframe, number = number, symbol = sym.name)
				symbol_data[sym.name] = data[sym.name]
				symbol_data['balance'] = data['balance']
				symbol_data['symbols'] = data['symbols']
			except Exception as ex:
				print("Get All Error: ", ex)
		return symbol_data

	def Update(self, timeframe, symbol, number):

		dataset_path = os.path.join(main_path_dataset , 'dataset' + path_slash + timeframe + path_slash + symbol + '.csv')
		dataset_path_dir = os.path.join(main_path_dataset , 'dataset' + path_slash + timeframe + path_slash)

		if not os.path.exists(dataset_path_dir):
			os.makedirs(dataset_path_dir)
			self.writer(symbol = symbol, timeframe = timeframe, number = number)

		if os.path.exists(dataset_path):

			print('Update Start ...')

			dataset_before = self.readone(symbol = symbol, number = 'all', timeframe = timeframe)

			
			self.initilizer()
			self.login()

			if timeframe == '5M':
				end = 99800
			elif timeframe == '15M':
				end = 33300
			elif timeframe == '1H':
				end = 8323
			elif timeframe == '4H':
				end = 60000
			elif timeframe == '1D':
				end = 10000

			dataset_now = self.getone(timeframe = timeframe, number = end, symbol = symbol)

			if timeframe == '5M':

				where_data = np.where(
										(dataset_before[symbol]['time'].iloc[-1].year == dataset_now[symbol]['time'].dt.year.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].month == dataset_now[symbol]['time'].dt.month.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].day == dataset_now[symbol]['time'].dt.day.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].hour == dataset_now[symbol]['time'].dt.hour.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].minute + 5 == dataset_now[symbol]['time'].dt.minute.to_numpy())
										)[0]

				dataset_before = pd.concat([dataset_before[symbol], dataset_now[symbol].iloc[where_data[0]:-1]], ignore_index = True)

				os.remove(dataset_path)
				dataset_before.to_csv(dataset_path)
				print('Finish Updating Dataset 5M')

			elif timeframe == '15M':

				where_data = np.where(
										(dataset_before[symbol]['time'].iloc[-1].year == dataset_now[symbol]['time'].dt.year.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].month == dataset_now[symbol]['time'].dt.month.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].day == dataset_now[symbol]['time'].dt.day.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].hour + 1 == dataset_now[symbol]['time'].dt.hour.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].minute == dataset_now[symbol]['time'].dt.minute.to_numpy())
										)[0]

				dataset_before = pd.concat([dataset_before[symbol], dataset_now[symbol].iloc[where_data[0]:-1]], ignore_index = True)

				os.remove(dataset_path)
				dataset_before.to_csv(dataset_path)
				print('Finish Updating Dataset 15M')

			elif timeframe == '1H':

				where_data = np.where(
										(dataset_before[symbol]['time'].iloc[-1].year == dataset_now[symbol]['time'].dt.year.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].month == dataset_now[symbol]['time'].dt.month.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].day == dataset_now[symbol]['time'].dt.day.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].hour + 1 == dataset_now[symbol]['time'].dt.hour.to_numpy())
										)[0]

				dataset_before = pd.concat([dataset_before[symbol], dataset_now[symbol].iloc[where_data[0]:-1]], ignore_index = True)

				os.remove(dataset_path)
				dataset_before.to_csv(dataset_path)
				print('Finish Updating Dataset 1H')
			
			elif timeframe == '4H':

				where_data = np.where(
										(dataset_before[symbol]['time'].iloc[-1].year == dataset_now[symbol]['time'].dt.year.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].month == dataset_now[symbol]['time'].dt.month.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].day == dataset_now[symbol]['time'].dt.day.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].hour + 4 == dataset_now[symbol]['time'].dt.hour.to_numpy())
										)[0]

				dataset_before = pd.concat([dataset_before[symbol], dataset_now[symbol].iloc[where_data[0]:-1]], ignore_index = True)

				os.remove(dataset_path)
				dataset_before.to_csv(dataset_path)
				print('Finish Updating Dataset 4H')

			elif timeframe == '1D':

				where_data = np.where(
										(dataset_before[symbol]['time'].iloc[-1].year == dataset_now[symbol]['time'].dt.year.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].month == dataset_now[symbol]['time'].dt.month.to_numpy()) &
										(dataset_before[symbol]['time'].iloc[-1].day + 1 == dataset_now[symbol]['time'].dt.day.to_numpy())
										)[0]

				print(dataset_now[symbol]['time'])
				print(dataset_before[symbol]['time'])

				dataset_before = pd.concat([dataset_before[symbol], dataset_now[symbol].iloc[where_data[0]:-1]], ignore_index = True)

				os.remove(dataset_path)
				dataset_before.to_csv(dataset_path)
				print('Finish Updating Dataset 1D')				


	def getone(self, timeframe, number, symbol):

		timeframe = self.timeframechecker(timeframe = timeframe)

		self.initilizer()
		self.login()

		account_info = mt5.account_info()

		if account_info != None:
			account_info_dict = mt5.account_info()._asdict()
		else:
			print("failed to connect to trade account %s, error code = " % (self.account_name), mt5.last_error())

		symbols = mt5.symbols_get()
		symbol_data = {}

		try:
			rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, number)
			rates_frame = pd.DataFrame(rates)
			# convert time in seconds into the datetime format
			rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')

			symbol_data[symbol] = pd.DataFrame({
												symbol: symbol,
												'open': rates_frame['open'],
												'close': rates_frame['close'],
												'low': rates_frame['low'],
												'high': rates_frame['high'],
												'HL/2': ((rates_frame['high']+rates_frame['low'])/2),
												'HLC/3': ((rates_frame['high']+rates_frame['low']+rates_frame['close'])/3),
												'HLCC/4': ((rates_frame['high']+rates_frame['low']+rates_frame['close']+rates_frame['close'])/4),
												'OHLC/4': ((rates_frame['high']+rates_frame['low']+rates_frame['close']+rates_frame['open'])/4),
												'volume': rates_frame['tick_volume'],
												'time': rates_frame['time']
												})
			symbol_data['balance'] = account_info_dict["balance"]
			symbol_data['symbols'] = symbols
			symbol_data['symbol'] = symbol

		except Exception as ex:
			print("get data one by one Error: ", ex)

		mt5.shutdown()

		return symbol_data

	def writer(self, symbol, timeframe, number):

		data = self.getone(timeframe = timeframe, number = number, symbol = symbol)

		dataset_path = os.path.join(main_path_dataset , 'dataset' + path_slash + timeframe + path_slash + symbol + '.csv')
		dataset_path_dir = os.path.join(main_path_dataset , 'dataset' + path_slash + timeframe + path_slash)

		if not os.path.exists(dataset_path_dir):
			os.makedirs(dataset_path_dir)

		if os.path.exists(dataset_path):
			os.remove(dataset_path)

		print(data)
		data[symbol].to_csv(dataset_path)

	def readone(self, timeframe, symbol, number):

		dataset_path = os.path.join(main_path_dataset , 'dataset' + path_slash + timeframe + path_slash + symbol + '.csv')
		
		symbols = symbol
		count=0
		symbol_data_5M = {}
		symbol_data_15M = {}
		symbol_data_1H = {}
		symbol_data_4H = {}
		symbol_data_1D = {}

		if os.path.exists(dataset_path):
			rates_frame = pd.read_csv(dataset_path)
			rates_frame['time'] = pd.to_datetime(rates_frame['time'])

			if number == 'all': number = len(rates_frame['open']) - 1

			if timeframe == '5M':
				symbol_data_5M[symbol] = pd.DataFrame({
													symbol: symbol,
													'open': rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
													'close': rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
													'low': rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
													'high': rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
													'HL/2': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/2),
													'HLC/3': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/3),
													'HLCC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
													'OHLC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
													'volume': rates_frame['volume'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
													'time': rates_frame['time'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)
													})
				#time_counter = 0
				#for ti in symbol_data_5M[symbol]['time']:
					#symbol_data_5M[symbol]['time'][time_counter] = datetime.strptime(symbol_data_5M[symbol]['time'][time_counter], "%Y-%m-%d %H:%M:%S")
					#time_counter += 1

				return symbol_data_5M

			elif timeframe == '15M':
				rates_frame = pd.read_csv(dataset_path)
				rates_frame['time'] = pd.to_datetime(rates_frame['time'])

				if number == 'all': number = len(rates_frame['open']) - 1

				symbol_data_15M[symbol] = pd.DataFrame({
														symbol: symbol,
														'open': rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'close': rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'low': rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'high': rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'HL/2': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/2),
														'HLC/3': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/3),
														'HLCC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'OHLC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'volume': rates_frame['volume'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'time': rates_frame['time'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)
														})

				return symbol_data_15M

			elif timeframe == '1H':
				rates_frame = pd.read_csv(dataset_path)
				rates_frame['time'] = pd.to_datetime(rates_frame['time'])

				if number == 'all': number = len(rates_frame['open']) - 1

				symbol_data_1H[symbol] = pd.DataFrame({
														symbol: symbol,
														'open': rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'close': rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'low': rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'high': rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'HL/2': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/2),
														'HLC/3': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/3),
														'HLCC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'OHLC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'volume': rates_frame['volume'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'time': rates_frame['time'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)
														})

				return symbol_data_1H

			elif timeframe == '4H':
				rates_frame = pd.read_csv(dataset_path)
				rates_frame['time'] = pd.to_datetime(rates_frame['time'])

				if number == 'all': number = len(rates_frame['open']) - 1

				symbol_data_4H[symbol] = pd.DataFrame({
														symbol: symbol,
														'open': rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'close': rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'low': rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'high': rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'HL/2': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/2),
														'HLC/3': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/3),
														'HLCC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'OHLC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'volume': rates_frame['volume'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'time': rates_frame['time'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)
														})

				#time_counter = 0
				#for ti in symbol_data_1H[symbol]['time']:
					#symbol_data_1H[symbol]['time'][time_counter] = datetime.strptime(symbol_data_1H[symbol]['time'][time_counter], "%Y-%m-%d %H:%M:%S")
					#time_counter += 1

				return symbol_data_4H

			elif timeframe == '1D':
				rates_frame = pd.read_csv(dataset_path)
				rates_frame['time'] = pd.to_datetime(rates_frame['time'])

				if number == 'all': number = len(rates_frame['open']) - 1

				symbol_data_1D[symbol] = pd.DataFrame({
														symbol: symbol,
														'open': rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'close': rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'low': rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'high': rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'HL/2': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/2),
														'HLC/3': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/3),
														'HLCC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'OHLC/4': ((rates_frame['high'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['low'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['close'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)+rates_frame['open'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True))/4),
														'volume': rates_frame['volume'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True),
														'time': rates_frame['time'][(len(rates_frame['open'])-number-1):-1].reset_index(drop=True)
														})

				#time_counter = 0
				#for ti in symbol_data_1H[symbol]['time']:
					#symbol_data_1H[symbol]['time'][time_counter] = datetime.strptime(symbol_data_1H[symbol]['time'][time_counter], "%Y-%m-%d %H:%M:%S")
					#time_counter += 1

				return symbol_data_1D
		
	def readall(self, symbol, number_5M, number_15M, number_1H, number_4H, number_1D):

		dataset_path_5M = os.path.join(main_path_dataset , 'dataset' + path_slash + '5M' + path_slash + symbol + '.csv')
		dataset_path_15M = os.path.join(main_path_dataset , 'dataset' + path_slash + '15M' + path_slash + symbol + '.csv')
		dataset_path_1H = os.path.join(main_path_dataset , 'dataset' + path_slash + '1H' + path_slash + symbol + '.csv')
		dataset_path_4H = os.path.join(main_path_dataset , 'dataset' + path_slash + '4H' + path_slash + symbol + '.csv')
		dataset_path_1D = os.path.join(main_path_dataset , 'dataset' + path_slash + '1D' + path_slash + symbol + '.csv')

		symbol_data_5M = self.readone(timeframe = '5M', symbol = symbol, number = number_5M)

		symbol_data_15M = self.readone(timeframe = '15M', symbol = symbol, number = number_15M)

		symbol_data_1H = self.readone(timeframe = '1H', symbol = symbol, number = number_1H)

		symbol_data_4H = self.readone(timeframe = '4H', symbol = symbol, number = number_4H)

		symbol_data_1D = self.readone(timeframe = '1D', symbol = symbol, number = number_1D)


		return symbol_data_5M, symbol_data_15M, symbol_data_1H, symbol_data_4H, symbol_data_1D

		
	def get_symbols(self):

		self.initilizer()
		
		self.login()

		symbols = mt5.symbols_get()

		mt5.shutdown()

		return symbols

	def get_balance(self):

		self.initilizer()
		
		self.login()

		account_info = mt5.account_info()

		if account_info!=None:
			account_info_dict = mt5.account_info()._asdict()

			return account_info_dict["balance"]
		else:
			print("failed to connect to trade account %s, error code =" % (self.account_name), mt5.last_error())

		mt5.shutdown()

	def initilizer(self):

		if not mt5.initialize():
			print("initialize() failed, error code =",mt5.last_error())
			quit()

	def login(self):
		mt5.login(login = accountConfig()[self.account_name]['username'], password = accountConfig()[self.account_name]['password'])

	def timeframechecker(self, timeframe):
		if timeframe == '5M':
			timeframe = mt5.TIMEFRAME_M5
		elif timeframe == '15M':
			timeframe = mt5.TIMEFRAME_M15
		elif timeframe == '1H':
			timeframe = mt5.TIMEFRAME_H1
		elif timeframe == '4H':
			timeframe = mt5.TIMEFRAME_H4
		elif timeframe == '1D':
			timeframe = mt5.TIMEFRAME_D1
		return timeframe

#login=51149098, server="Alpari-MT5-Demo",password="zyowt2zj"
# loging = LogingGetData()
# loging.account_name = 'mehrshadpc'
# loging.initilizer()
# loging.login()
# #print(mt5.TIMEFRAME_H1)

# for sym in loging.get_symbols():
#  	print(sym.name)

# print(loging.get_balance())
# data = loging.getone(timeframe = mt5.TIMEFRAME_M5, number = 500, symbol = 'XAUUSD_i')
# print(data['XAUUSD_i'])

# data = loging.getall(timeframe = mt5.TIMEFRAME_M5, number = 500)
# print(data)