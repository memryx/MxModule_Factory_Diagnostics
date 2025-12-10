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
                             default =   "4chips_source_models",
                             metavar =   "",
                             help    =   "the source folder to handle bulk folder")

        control.add_argument("-d",
                             dest    =   "dest_folder",
                             action  =   "store",
                             type    =   str,
                             default =   "4chips",
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
    
    model_list = load_model_list_from_txt(cmd_arg.source_file)
    
    print('get {} models from the txt'.format(len(model_list)))
    
    prefix = ["model_", "k_", "onnx_", "pt_", "tf_", "tfl_"]
    
    testcase_dir = []
    for p in prefix:
        path_str = str(Path(cmd_arg.work_folder, p + '*'))
        testcase_dir.extend(glob.glob(path_str))
    #print(testcase_dir)   
    
    print('get {} folder from the {}'.format(len(testcase_dir), cmd_arg.work_folder))

    
    dfp_prefix = "dfp_"
    dfp_folder_dir = []
    for t in testcase_dir:
        path_str = str(Path(t, dfp_prefix + '*'))
        dfp_folder_dir.extend(glob.glob(path_str))
    
    if len(dfp_folder_dir):
    	for t in dfp_folder_dir:
    	    #print(t)   
    	    shutil.rmtree(t, ignore_errors=True)
    del dfp_folder_dir
    
    
    found = 0;
    other = 0;
    move_model_name = []
    for t in testcase_dir:
        path = Path(t)
        if path.name in model_list:
            found += 1
            model_list.remove(path.name)
            move_model_name.append(str(path.name))
        else:
            other += 1
            
    print('found match model {} in model_list missing model {}'.format(found, len(model_list)))
    if len(model_list):
        print(model_list)
    

    if found:        
        #start to move
        dfp_name = 'model.dfp'
        src_folder = cmd_arg.work_folder
        des_folder = cmd_arg.dest_folder
        for t in move_model_name:
            dfp_path = Path(src_folder,t,dfp_name)
            if dfp_path.exists():
                des_path = Path(des_folder,t,dfp_name)
                if des_path.parent.exists():
                    dfp_path.replace(des_path)
                else:
                    des_path.parent.mkdir(parents=True, exist_ok=True)
                    dfp_path.replace(des_path)
                print('moved to {}'.format(des_path))
            else:
               print('missing {}'.format(dfp_path))

    '''
    num_frames = 2
    
    # prefix = [
            # "k_real_dce_performance"
            #   "tfl_real_bodypix_mobilenet_performance",
            #   "k_real_yolov3_tiny_performance"
            #   ]

    



    # Setup save file / or load exisiting one
    result_path = Path(cmd_arg.log_dir, result_file)
    if skip_alread_run or (Path.is_file(result_path) == False):
        print('Creating {}'.format(str(result_path)))
        already_ran = []
        with open(str(result_path), 'w') as f:
            f.write('{},{},{}\n'.format("Model", "Result", "FPS"))
    else:
        print('Reading {}'.format(str(result_path)))
        with open(str(result_path), 'r') as f:
            already_ran = f.read().split('\n')[:-1]
            already_ran = [a.split(',')[0] for a in already_ran]

    testcase_dir = sorted(testcase_dir)
    for t in testcase_dir:
        num_out_ports = 0
        path = Path(t)
        # Check if results failed  with exception
        outputs_file = open(str(result_path), 'a')
        if path.name in already_ran:
            print('Skipping {} (already ran)...'.format(path.name))
            continue
        else:
            print('Running {}...'.format(path.name))

        # Open
        result = 0
        dfp_path = Path(t, "model.dfp")

        if Path.is_file(dfp_path) == False:
            print('Skipping {} (is Not file)...'.format(dfp_path))
            result = -5
        else:
            dfp_info = dfp_inspect(str(dfp_path))
            if dfp_info is None:
                print('Skipping {} (dfp_info None)...'.format(path.name))
                result = -5

        if result == 0:
            # Load ifmaps
            ifmaps = []
            for i,(k,v) in enumerate(dfp_info['input_ports'].items()):
                if not v['active']:
                    continue
                print(v)
                fmap = []
                for f in range(num_frames):
                    fname = t+'/fmaps/ifmap_truth_{}_{}'.format(i, f)
                    fmap.append(np.loadtxt(fname).reshape(v['shape'])[:,:,:,:])

                if v['format'] == 'rgb888':
                    ifmaps.append(np.array(fmap).astype(np.uint8))
                else:
                    ifmaps.append(np.array(fmap).astype(np.float32))

            # Load ofmaps
            ofmaps_t = []
            for i,(k,v) in enumerate(dfp_info['output_ports'].items()):
                if not v['active']:
                    continue
                print(v)
                fmap = []
                num_out_ports = num_out_ports + 1
                fmap = []
                for f in range(num_frames):
                    fname = t+'/fmaps/ofmap_{}_{}'.format(i, f)
                    fmap.append(np.loadtxt(fname).reshape(v['shape']))
                ofmaps_t.append(np.array(fmap))
            with Benchmark(dfp=str(dfp_path), group = cmd_arg.device_group) as accl:
                ofmaps, __, fps = accl.run(ifmaps, frames=1)

        if ofmaps is not None:
            for f in range(num_frames):
                for p,port_ofmap in enumerate(ofmaps):
                    file_name = "{}/fmaps/ofmap_chip_{}_{}".format(t, p, f)
                    np.savetxt(file_name, port_ofmap[f,...].flatten(), fmt="%f")

        if ofmaps is not None:
            passed = []
            for f in range(num_frames):
                for j in range(num_out_ports):
                    if ofmaps[j].shape == ofmaps_t[j].shape:
                        if np.allclose(ofmaps[j], ofmaps_t[j], atol=1e-4):
                            passed.append(True)
                            print('>>>>>>>>>>>>>>> compare true')
                        else:
                            passed.append(False)
                            print('>>>>>>>>>>>>>>> compare false')

                    else:
                        print('>>>>>>>>>>>>>>> shape mismatch')
                        passed.append(False)
                        result = -7

            if all(passed):
                result = 0
            else:
                result = -2

        if result == 0:
            outputs_file.write('{}, {}\n'.format(path.name, "PASS"))
            outputs_file.close()
            num_frames = ofmaps[0].shape[0]

            print('Passed!')
        else:
            result_map = {
              -1: 'Ofmap timeout',
              -2: 'Compare failed',
              -3: 'IGR not empty',
              -4: 'Multi in/out flow',
              -5: 'DFP missing',
              -6: 'No sim ofmap',
              -7: 'Ofmap shape mismatch',
            }

            outputs_file.write('{},{}\n'.format(path.name, result_map[result]))
            outputs_file.close()
            print('Failed: ', result_map[result])
            #return -1
    '''
    return 0

if __name__=="__main__":
    cmd_arg = __parse()
    create_model_folder(cmd_arg)
