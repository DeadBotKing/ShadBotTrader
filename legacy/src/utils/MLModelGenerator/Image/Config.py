from pathlib import Path, PurePosixPath
import os
import sys


if 'win' in sys.platform:
	path_slash = '\\'
elif 'linux' in sys.platform:
	path_slash = '/'



class Config:

	def __init__(cls):
		
		cls.cfg = dict({

						#************** Feature Engineering:

						'path_PreTrainedModels': os.path.join(Path(__file__).parent , 'Models' + path_slash + 'PreTrainedModels' + path_slash),
                        'path_FinalTrainedModels': os.path.join(Path(__file__).parent , 'Models' + path_slash + 'FinalTrainedModels' + path_slash),

                        'path_TensorBoard': os.path.join(Path(__file__).parent , 'Models' + path_slash + 'TensorBoard' + path_slash),
                        'path_FlowChart': os.path.join(Path(__file__).parent , 'Models' + path_slash + 'FlowChart' + path_slash),

						#/////////////////////////////

						})