import mxa # mxa driver
import os, sys, glob, time, struct, argparse
from pathlib import Path
from utilities.dfp_inspect import dfp_inspect
from utilities.benchmark import Benchmark
from tool.perf_report import result_processing

burning_test = 0

def __parse():
        """
        Setup the parser (`argparse`) and parse the command line arguments.
        """

        epilog = "Examples:\n"
        epilog += "\n"
        epilog += "    » python memx_performance                                # run all dfp one time'. \n"
        epilog += "    » python memx_regression --dir test                      # run all dfp under test folder one time'. \n"
        epilog += "    » python memx_performance --burning                      # run all dfp repeatly'. \n"
        epilog += "    » python memx_regression --burning  --hours 3            # run all dfp repeatly about 3 hours'. \n"
        epilog += "    » python memx_performance -g 1                           # run all dfp on device group 1'. \n"

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

        control.add_argument("-f",
                             dest    =   "frames",
                             action  =   "store",
                             type    =   int,
                             default =   100,
                             metavar =   "",
                             help    =   "the frames count for performance test")

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

        control.add_argument("--fps",
                             dest    =   "fps",
                             action  =   "store",
                             type    =   int,
                             default =   0,
                             help    =   "Constraint fps for specific value")

        cmd_args = parser.parse_args()

        return cmd_args

def main(cmd_arg):
    #parameter setting
    prefix = ["k", "onnx_", "pt_", "tf_", "tfl_", "model_"]
    dfp_name = "model.dfp"
    result_file = 'performance_result.csv'

    # search dir
    testcase_dir = []
    for p in prefix:
        path_str = str(Path(cmd_arg.dataflow_dir, p + '*'))
        testcase_dir.extend(glob.glob(path_str))
    #print(testcase_dir)
    #check already_ran in output file or not
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

    #print(already_ran)

    #running for each file
    for t in testcase_dir:
        path = Path(t)
        if path.name in already_ran:
            print('Skip Already ran {}...'.format(path.name))
            continue
        else:
            print('{}: Running {}...'.format(time.strftime("%m-%d %H:%M:%S"), path.name))
            dfp_path = Path(path, dfp_name)

            if Path.is_file(dfp_path):
                pass
            else:
                raise Exception("dfp_path is not file")

        try:
            with Benchmark(dfp=str(dfp_path), group = cmd_arg.device_group, frames = cmd_arg.frames, fps=cmd_arg.fps) as accl:
                ofmaps, latency, fps = accl.run(frames=cmd_arg.frames, threading=True) # threading=True without inputs to run fps
        except Exception as e:
            print(e)
            return - 1

        if (ofmaps == None) and (latency == -1):  #accl.run fps finished
            print('{0:64s}, {1:4s}, {2:6.3f}\n'.format(path.name, "PASS", float(fps)))
            with open(str(result_path), 'a') as f:
                f.write('{}, {}, {}\n'.format(path.name, "PASS", fps))

    #Post-processing
    if not cmd_arg.burning:
        result_processing(str(result_path))

    print('{}: Test Finished'.format(time.strftime("%m-%d %H:%M:%S")))

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
                result = main(cmd_arg)
                loop += 1
            print("time is up")
        else:
            while cmd_arg.burning:
                print('{}: Round {}'.format(time.strftime("%m-%d %H:%M:%S"), loop))
                result = main(cmd_arg)
                loop += 1
    else:
        result = main(cmd_arg)

    sys.exit(result)