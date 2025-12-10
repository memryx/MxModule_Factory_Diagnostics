import mxa # mxa driver
import os, sys, glob, time, struct, argparse
from pathlib import Path
from io import BytesIO
import numpy as np
from utilities.dfp_inspect import dfp_inspect
from utilities.benchmark import Benchmark
import faulthandler
from collections import defaultdict
ATOL = 1e-4

faulthandler.enable()
burning_test = 0

result_file = 'regression_result.csv'

def __parse():
        """
        Setup the parser (`argparse`) and parse the command line arguments.
        """

        epilog = "Examples:\n"
        epilog += "\n"
        epilog += "    » python memx_regression                         # run all dfp under default folder one time'. \n"
        epilog += "    » python memx_regression --dir test              # run all dfp under test folder one time'. \n"
        epilog += "    » python memx_regression --burning               # run all dfp repeatly'. \n"
        epilog += "    » python memx_regression --burning  --hours 3    # run all dfp repeatly about 3 hours'. \n"
        epilog += "    » python memx_regression -g 1                    # run all dfp on device group 1'. \n"

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
        control.add_argument("--dir",
                             dest    =   "dataflow_dir",
                             action  =   "store",
                             type    =   str,
                             default =   "dfp",
                             metavar =   "",
                             help    =   "the root folder to put DFP file")

        control.add_argument("--log",
                             dest    =   "log_dir",
                             action  =   "store",
                             type    =   str,
                             default =   "log",
                             metavar =   "",
                             help    =   "the root folder to put log file")

        control.add_argument("-g",
                             dest    =   "device_group",
                             action  =   "store",
                             type    =   int,
                             default =   0,
                             metavar =   "",
                             help    =   "the device group index for running")

        control.add_argument("--burning",
                             dest    =   "burning",
                             action  =   "store_true",
                             default =   False,
                             help    =   "infinite run or not")

        control.add_argument("--hours",
                             dest    =   "hours",
                             action  =   "store",
                             type    =   int,
                             default =   0,
                             help    =   "How many hours to burning 0 means non-stop")

        cmd_args = parser.parse_args()

        return cmd_args

def run_driver_regression(cmd_arg):
    num_frames = 2
    prefix = ["k", "onnx_", "pt_", "tf_", "tfl_", "model_"]
    error_count = 0
    # prefix = [
            # "k_real_dce_performance"
            #   "tfl_real_bodypix_mobilenet_performance",
            #   "k_real_yolov3_tiny_performance"
            #   ]

    testcase_dir = []
    for p in prefix:
        path_str = str(Path(cmd_arg.dataflow_dir, p + '*'))
        testcase_dir.extend(glob.glob(path_str))


    # Setup save file / or load exisiting one
    result_path = Path(cmd_arg.log_dir, result_file)
    if burning_test or (Path.is_file(result_path) == False):
        #print('Creating {}'.format(str(result_path)))
        already_ran = []
        with open(str(result_path), 'w') as f:
            f.write('{},{},{}\n'.format("Model", "Result", "FPS"))
    else:
        #print('Reading {}'.format(str(result_path)))
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
                #print(v)
                fmap = []
                for f in range(num_frames):
                    fname = t+'/fmaps/ifmap_truth_{}_{}'.format(i, f)
                    fmap.append(np.loadtxt(fname).reshape(v['shape'])[:,:,:,:])

                if v['packing_format'] == 'rgb888':
                    ifmaps.append(np.array(fmap).astype(np.uint8))
                else:
                    ifmaps.append(np.array(fmap).astype(np.float32))

            # Load ofmaps
            ofmaps_t = []
            for i,(k,v) in enumerate(dfp_info['output_ports'].items()):
                if not v['active']:
                    continue
                #print(v)
                fmap = []
                num_out_ports = num_out_ports + 1
                fmap = []
                for f in range(num_frames):
                    fname = t+'/fmaps/ofmap_{}_{}'.format(i, f)
                    fmap.append(np.loadtxt(fname).reshape(v['shape']))
                ofmaps_t.append(np.array(fmap))
            try:
                with Benchmark(dfp=str(dfp_path), group = cmd_arg.device_group) as accl:
                    ofmaps, __, fps = accl.run(ifmaps, frames=1)
            except:
                return -1

        if ofmaps is not None:
            passed = []
            for f in range(num_frames):
                for j in range(num_out_ports):
                    if ofmaps[j].shape == ofmaps_t[j].shape:
                        if np.allclose(ofmaps[j], ofmaps_t[j], atol=1e-4):
                            passed.append(True)
                            #print('>>>>>>>>>>>>>>> compare true')
                        else:
                            passed.append(False)
                            #print('>>>>>>>>>>>>>>> compare false')

                    else:
                        #print('>>>>>>>>>>>>>>> shape mismatch')
                        passed.append(False)
                        result = -7

            if all(passed):
                result = 0
            else:
                result = -2
        else:
            result = -6

        if result == 0:
            num_frames = ofmaps[0].shape[0]
            print('Passed!')
        else:
            if ofmaps is not None:
                for f in range(num_frames):
                    for p,port_ofmap in enumerate(ofmaps):
                        file_name = "{}/fmaps/ofmap_chip_{}_{}".format(t, p, f)
                        np.savetxt(file_name, port_ofmap[f,...].flatten(), fmt="%f")
            result_map = {
              -1: 'Ofmap timeout',
              -2: 'Compare failed',
              -3: 'IGR not empty',
              -4: 'Multi in/out flow',
              -5: 'DFP missing',
              -6: 'No sim ofmap',
              -7: 'Ofmap shape mismatch',
            }
            error_count += 1
            outputs_file.write('{},{}\n'.format(path.name, result_map[result]))
            print('Failed: {}'.format(result_map[result]))
            
    outputs_file.close()
    return error_count

if __name__=="__main__":
    cmd_arg = __parse()
    result = 0
    if cmd_arg.burning:
        loop = 1
        burning_test = 1
        start_time = time.time();
        if cmd_arg.hours > 0:
            end_time = time.time() + 3600 * cmd_arg.hours
            while time.time() < end_time:
                print('{}: Round {}'.format(time.strftime("%m-%d %H:%M:%S"), loop))
                result = run_driver_regression(cmd_arg)
                loop += 1
        else:
            while cmd_arg.burning:
                print('{}: Round {}'.format(time.strftime("%m-%d %H:%M:%S"), loop))
                result = run_driver_regression(cmd_arg)
                loop += 1
    else:
        result = run_driver_regression(cmd_arg)

    sys.exit(result)
