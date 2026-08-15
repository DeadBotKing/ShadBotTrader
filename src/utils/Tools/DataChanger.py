import numpy as np
try:
	import cudf as pd
except:
	try:
		import modin.pandas as pd
	except:
		import pandas as pd

class DataChanger:

	def Spliter(
				self,
				data,
				length
				):

		data_splited = pd.DataFrame()
		cut_first = 0

		if (
			int(len(data.low)-1) > length
			):

			cut_first = int(len(data.low)-1) - length

		data_splited = data.truncate(before=cut_first, after=int(len(data.low)-1), axis=None, copy=True).reset_index(drop=True)

		return data_splited

	def SpliterSyncPR(
						self,
						dataset_5M,
						dataset_15M,
						dataset_1H,
						dataset_4H,
						dataset_1D,
						loc_end_5M,
						length_5M,
						length_15M,
						length_1H,
						length_4H,
						length_1D,
						reset_index = True,
						):

		dataset_pr_5M = pd.DataFrame()
		dataset_pr_15M = pd.DataFrame()
		dataset_pr_1H = pd.DataFrame()

		cut_first = 0
		if (loc_end_5M > length_5M):
			cut_first = int(loc_end_5M) - length_5M


		dataset_pr_5M = dataset_5M.truncate(before=cut_first, after=int(loc_end_5M-1), axis=None, copy=True).reset_index(drop=reset_index)
		#/////////////////////////////////

		#**************************
		location_15M = -1
		list_time = np.where(
							(dataset_15M['time'].dt.year.to_numpy() == dataset_5M['time'][int(loc_end_5M)].year) &
							(dataset_15M['time'].dt.month.to_numpy() == dataset_5M['time'][int(loc_end_5M)].month) &
							(dataset_15M['time'].dt.day.to_numpy() == dataset_5M['time'][int(loc_end_5M)].day) &
							(dataset_15M['time'].dt.hour.to_numpy() == dataset_5M['time'][int(loc_end_5M)].hour) &
							(dataset_15M['time'].dt.minute.to_numpy() <= dataset_5M['time'][int(loc_end_5M)].minute)
							)[0]
		try:
			location_15M = list_time[0] + 1
		except:
			location_15M = 0

		if location_15M <= 1: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

		cut_first_15M = 0
		if location_15M >= length_15M:
			cut_first_15M = location_15M - length_15M

		dataset_pr_15M = dataset_15M.truncate(before=cut_first_15M, after=int(location_15M-1), axis=None, copy=True).reset_index(drop=reset_index)
		#//////////////////////////////////////////

		#**************************
		location_1H = -1
		list_time = np.where(
							(dataset_1H['time'].dt.year.to_numpy() == dataset_5M['time'][int(loc_end_5M)].year) &
							(dataset_1H['time'].dt.month.to_numpy() == dataset_5M['time'][int(loc_end_5M)].month) &
							(dataset_1H['time'].dt.day.to_numpy() == dataset_5M['time'][int(loc_end_5M)].day) &
							(dataset_1H['time'].dt.hour.to_numpy() == dataset_5M['time'][int(loc_end_5M)].hour)
							)[0]
		try:
			location_1H = list_time[0] + 1
		except:
			location_1H = 0

		if location_1H <= 1: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

		cut_first_1H = 0
		if location_1H >= length_1H:
			cut_first_1H = location_1H - length_1H

		dataset_pr_1H = dataset_1H.truncate(before=cut_first_1H, after=int(location_1H-1), axis=None, copy=True).reset_index(drop=reset_index)
		#//////////////////////////////////////////

		#**************************
		location_4H = -1
		list_time = np.where(
							(dataset_4H['time'].dt.year.to_numpy() == dataset_5M['time'][int(loc_end_5M)].year) &
							(dataset_4H['time'].dt.month.to_numpy() == dataset_5M['time'][int(loc_end_5M)].month) &
							(dataset_4H['time'].dt.day.to_numpy() == dataset_5M['time'][int(loc_end_5M)].day) &
							(dataset_4H['time'].dt.hour.to_numpy() == dataset_5M['time'][int(loc_end_5M)].hour)
							)[0]
		try:
			location_4H = list_time[0] + 1
		except:
			location_4H = 0

		if location_4H <= 1: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

		cut_first_4H = 0
		if location_4H >= length_4H:
			cut_first_4H = location_4H - length_4H

		dataset_pr_4H = dataset_4H.truncate(before=cut_first_4H, after=int(location_4H-1), axis=None, copy=True).reset_index(drop=reset_index)
		#//////////////////////////////////////////

		#**************************
		location_1D = -1
		list_time = np.where(
							(dataset_1D['time'].dt.year.to_numpy() == dataset_5M['time'][int(loc_end_5M)].year) &
							(dataset_1D['time'].dt.month.to_numpy() == dataset_5M['time'][int(loc_end_5M)].month) &
							(dataset_1D['time'].dt.day.to_numpy() == dataset_5M['time'][int(loc_end_5M)].day)
							)[0]
		try:
			location_1D = list_time[0] + 1
		except:
			location_1D = 0

		if location_1D <= 1: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

		cut_first_1D = 0
		if location_1D >= length_1D:
			cut_first_1D = location_1D - length_1D

		dataset_pr_1D = dataset_1D.truncate(before=cut_first_1D, after=int(location_1D-1), axis=None, copy=True).reset_index(drop=reset_index)
		#//////////////////////////////////////////

		return dataset_pr_5M, dataset_pr_15M, dataset_pr_1H, dataset_pr_4H, dataset_pr_1D