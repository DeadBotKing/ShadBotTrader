from src.utils.MLModelGenerator.Image.Config import Config
import os

def ModelNames():

	print()
	print()
	print('Model Names: ***************')
	print('buy_sell')
	print('buy_no_trade')
	print('sell_no_trade')
	print('full_image_model_complex')
	print('full_image_model_straight')
	print('double_full_image_model')
	print()
	print('final_image_model_buy_sell')
	print('final_image_model_buy_no_trade')
	print('final_image_model_sell_no_trade')
	print('final_image_model_full_image_model_complex')
	print('final_image_model_full_image_model_straight')
	print('final_image_model_double_full_image_model')
	print('/////////////////////////////')
	print()

	image_config = Config()
	if os.path.exists(image_config.cfg['path_PreTrainedModels']):
		print('Pre Models That Exist: ******')
		for elm in os.listdir(image_config.cfg['path_PreTrainedModels']):
			print('Exist Pre Mdels: ', elm)
		print('/////////////////////////////')

	if os.path.exists(image_config.cfg['path_FinalTrainedModels']):
		print('Final Models Taht Exist: ****')
		for elm in os.listdir(image_config.cfg['path_FinalTrainedModels']):
			print('Exist Final Mdels: ', elm)
		print('/////////////////////////////')
	print()
	print()