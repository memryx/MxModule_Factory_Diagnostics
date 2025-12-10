import os, sys, glob, time, struct
import argparse
import shutil
from pathlib import Path
from io import BytesIO
import numpy as np
import faulthandler
from collections import defaultdict
ATOL = 1e-4

faulthandler.enable()
skip_alread_run = 1

result_file = 'regression_result.csv'

def __parse():
        """
        Load a txt file and sepearate the model file and dfp file
        """

        epilog = "Examples:\n"
        epilog += "\n"
        epilog += "    » python memx_regression                 # run all dfp one time'. \n"
        epilog += "    » python memx_regression --burning       # run all dfp repeatly'. \n"
        epilog += "    » python memx_regression -g 1            # run all dfp on device group 1'. \n"

        parser = argparse.ArgumentParser(
                 description = "\033[34mMemryX Driver Test Suite\033[0m",
                 formatter_class = argparse.RawDescriptionHelpFormatter,
                 epilog=epilog)

        visual = parser.add_argument_group("Visualization")
        control = parser.add_argument_group("Control")
        #-- Verbosity ---------------------------------------------------------
        visual.add_argument("-v",
                            dest = "verbose",
                            action  = "count",
                            default = 0,
                            help    = "Verbose messaging")

        #-- Control -----------------------------------------------------------
        control.add_argument("-s",
                             dest    =   "source_file",
                             action  =   "store",
                             type    =   str,
                             default =   "results_for_chip_bm_4_chips.txt",
                             metavar =   "",
                             help    =   "the source txt")

        control.add_argument("-w",
                             dest    =   "work_folder",
                             action  =   "store",
                             type    =   str,
                             default =   "performance_all",
                             metavar =   "",
                             help    =   "the source folder to handle bulk folder")

        control.add_argument("-d",
                             dest    =   "dest_folder",
                             action  =   "store",
                             type    =   str,
                             default =   "performance_dfp",
                             metavar =   "",
                             help    =   "the dest folder to put seperate file")

        cmd_args = parser.parse_args()

        return cmd_args

'''
read source txt
scan current folder to get corresponding folder
if model.dfp file exist move to target folder else do nothing.
'''
def load_model_list_from_txt(fname):
    model_list = []
    with open(fname, "r") as f:
        for line in f.readlines():
            line = line.strip()
            model_list.append(line)
    return model_list

def create_model_folder(cmd_arg):
    prefix = ["model_", "k_", "onnx_", "pt_", "tf_", "tfl_"]

    testcase_dir = []
    for p in prefix:
        path_str = str(Path(cmd_arg.work_folder, p + '*'))
        testcase_dir.extend(glob.glob(path_str))
    #print(testcase_dir)

    print('get {} folder from the {}'.format(len(testcase_dir), cmd_arg.work_folder))

    #start to move

    dfp_name = 'model.dfp'
    src_folder = cmd_arg.work_folder
    des_folder = cmd_arg.dest_folder
    for t in testcase_dir:
        t_path = Path(t)
        dfp_path = Path(t_path,dfp_name)
        end_index = t_path.name.find('_cascade')
        taget_folder = t_path.name[:end_index]
        if dfp_path.exists():
            des_path = Path(des_folder, taget_folder, dfp_name)
            #print(des_path)
            if des_path.parent.exists():
                dfp_path.replace(des_path)
            else:
                des_path.parent.mkdir(parents=True, exist_ok=True)
                dfp_path.replace(des_path)
            print('{} moved to {}'.format(dfp_path, des_path))
        else:
            print('missing DFP in {}'.format(t_path.name[:end_index]))
    '''

    dfp_prefix = "dfp_"
    dfp_folder_dir = []
    for t in testcase_dir:
        path_str = str(Path(t, dfp_prefix + '*'))
        dfp_folder_dir.extend(glob.glob(path_str))
        dfp_folder_dir.extend(glob.glob(str(Path(t, 'performance'))))
        dfp_folder_dir.extend(glob.glob(str(Path(t, 'progress'))))

    if len(dfp_folder_dir):
    	for t in dfp_folder_dir:
    	    #print(t)
    	    shutil.rmtree(t, ignore_errors=True)
    del dfp_folder_dir

    for t in testcase_dir:
        path = Path(t, '0.dfp')
        if path.exists():
            path.unlink()
        path = Path(t, 'ofmap_chip')
        if path.exists():
            path.unlink()

    api_lut = ["onnx_model_", "tflite_model_", "tf_model_" , "keras_model_"]
    target_file = []
    for t in testcase_dir:
        for pre_fix in api_lut:
            path_str = str(Path(t, pre_fix + '*'))
            target_file.extend(glob.glob(path_str))

    if len(target_file):
    	for t in target_file:
            try:
                os.remove(t)
            except:
                print("File doesn't exist")
    del target_file

    for t in testcase_dir:
        end = t.find('cascade_plus')
        length = len('cascade_plus4x')
        new_dir = t[:end + length]
        Path(t).rename(new_dir)
    '''
    return 0

if __name__=="__main__":
    cmd_arg = __parse()
    create_model_folder(cmd_arg)
