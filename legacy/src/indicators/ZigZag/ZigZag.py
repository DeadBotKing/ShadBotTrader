#from zigzag import peak_valley_pivots
import pandas as pd

def Find(dataset, index_first, index_last, percent = 0.4):

	ZigZag = peak_valley_pivots(
								dataset['OHLC/4'][index_first : index_last], 
								# abs(dataset['close'][index_first : index_last].pct_change(1)).mean(),
								# -abs(dataset['close'][index_first : index_last].pct_change(1)).mean()
								percent/100,
								-percent/100
								)
	ts_ZigZag = pd.Series(dataset['OHLC/4'][index_first:index_last], index=dataset['OHLC/4'][index_first : index_last].index)
	ts_ZigZag = ts_ZigZag[ZigZag != 0]

	return ts_ZigZag