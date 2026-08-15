from src.utils.DataReader.MetaTraderReader5.LoginGetData import LoginGetData as getdata
from src.utils.Optimizers import OptimizersRunner
from src.utils.Optimizers import NoiseCanceller
from src.utils.Optimizers import Optimizers
import sys

optimizersrunner = OptimizersRunner.OptimizersRunner() 

optimizersrunner.symbol = 'XAUUSD_i'
optimizersrunner.turn = 200

optimizersrunner.timeframe = '5M'
optimizersrunner.Run()

optimizersrunner.timeframe = '15M'
optimizersrunner.Run()

optimizersrunner.timeframe = '1H'
optimizersrunner.Run()

# optimizersrunner.timeframe = '4H'
# optimizersrunner.Run()

# optimizersrunner.timeframe = '1D'
# optimizersrunner.Run()

sys.exit()

dataset_5M, dataset_15M, dataset_1H = loging.readall(symbol = 'XAUUSD_i', number_5M = 'all', number_15M = 'all', number_1H = 'all')
symbol = 'XAUUSD_i'

# dataset_5M_real, _ = loging.readall(symbol = 'XAUUSD_i', number_5M = 'all', number_1H = 0)
# dataset_5M_real = dataset_5M_real[parameters.elements['symbol']]

optimizers = Optimizers.Optimizers() 

noise_canceller = NoiseCanceller.NoiseCanceller()
dataset_5M['XAUUSD_i']['close'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'close')
dataset_5M['XAUUSD_i']['open'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'open')
dataset_5M['XAUUSD_i']['high'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'high')
dataset_5M['XAUUSD_i']['low'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'low')
dataset_5M['XAUUSD_i']['HL/2'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'HL/2')
dataset_5M['XAUUSD_i']['HLC/3'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'HLC/3')
dataset_5M['XAUUSD_i']['HLCC/4'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'HLCC/4')
dataset_5M['XAUUSD_i']['OHLC/4'] = noise_canceller.NoiseWavelet(dataset = dataset_5M['XAUUSD_i'], applyto = 'OHLC/4')

print('Data Ready .... ')
# sys.exit()

for i in range(0, 10):

	print('Turn = ', i)
	optimizers.symbol = 'XAUUSD_i'
	optimizers.sigpriority = 'primary'
	optimizers.sigtype = 'buy'
	optimizers.turn = 400
	optimizers.dataset = dataset_5M.copy()
	optimizers.timeframe = '5M'

	optimizers.MacdOptimizer()

	optimizers.symbol = 'XAUUSD_i'
	optimizers.sigpriority = 'secondry'
	optimizers.sigtype = 'buy'
	optimizers.turn = 400
	optimizers.dataset = dataset_5M.copy()
	optimizers.timeframe = '5M'

	optimizers.MacdOptimizer()

	optimizers.symbol = 'XAUUSD_i'
	optimizers.sigpriority = 'primary'
	optimizers.sigtype = 'sell'
	optimizers.turn = 400
	optimizers.dataset = dataset_5M.copy()
	optimizers.timeframe = '5M'

	optimizers.MacdOptimizer()

	optimizers.symbol = 'XAUUSD_i'
	optimizers.sigpriority = 'secondry'
	optimizers.sigtype = 'sell'
	optimizers.turn = 400
	optimizers.dataset = dataset_5M.copy()
	optimizers.timeframe = '5M'

	optimizers.MacdOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'primary'
# optimizers.sigtype = 'buy'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.StochAsticOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'secondry'
# optimizers.sigtype = 'buy'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.StochAsticOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'primary'
# optimizers.sigtype = 'sell'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.StochAsticOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'secondry'
# optimizers.sigtype = 'sell'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.StochAsticOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'primary'
# optimizers.sigtype = 'buy'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.RSIOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'secondry'
# optimizers.sigtype = 'buy'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.RSIOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'primary'
# optimizers.sigtype = 'sell'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.RSIOptimizer()

# optimizers.symbol = 'XAUUSD_i'
# optimizers.sigpriority = 'secondry'
# optimizers.sigtype = 'sell'
# optimizers.turn = 100
# optimizers.dataset = dataset_5M.copy()
# optimizers.timeframe = '5M'

# optimizers.RSIOptimizer()