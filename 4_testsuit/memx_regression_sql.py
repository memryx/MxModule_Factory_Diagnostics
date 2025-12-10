import mxa # mxa driver
import os, sys, glob, time, struct, argparse
from pathlib import Path
from io import BytesIO
import numpy as np
from utilities.dfp_inspect import dfp_inspect
from utilities.benchmark import Benchmark
import faulthandler
import pymssql, platform, psutil, subprocess, multiprocessing
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
        epilog += "    » python memx_regression_sql.py                            # run all dfp one time with default frequency/voltage'. \n"
        epilog += "    » python memx_regression_sql.py --burning                  # run all dfp repeatly with default frequency/voltage'. \n"
        epilog += "    » python memx_regression_sql.py -g 1                       # run all dfp on device group 1 with default frequency/voltage'. \n"
        epilog += "    » python memx_regression_sql.py -fs 600 -fe 700 -fp 50     # run all dfp on device with default voltage and frequency 600/650/700 MHz'. \n"
        epilog += "    » python memx_regression_sql.py -vs 700 -fe 600 -fp 50     # run all dfp on device with default frequency and voltage 700/650/600 mV'. \n"

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

        control.add_argument("-l",
                             dest    =   "loopAverage",
                             action  =   "store",
                             type    =   int,
                             default =   1,
                             help    =   "Loop for getting average fps")

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

        control.add_argument("--vo",
                             dest    =   "voltage",
                             action  =   "store",
                             type    =   int,
                             default =   0,
                             help    =   "Setup device voltage")

        cmd_args = parser.parse_args()

        return cmd_args

def get_cpu_name():
    cpu_name = "Unknown"
    try:
        result = subprocess.run(['lscpu'], stdout=subprocess.PIPE, text=True)
        for line in result.stdout.splitlines():
            if "Model name:" in line:
                cpu_name = line.split(":")[1].strip()
                return cpu_name

    except Exception as e:
        return f"Error: {str(e)}"

def run_benchmark(dfp_path, cmd_arg, ifmaps):
    with Benchmark(dfp=str(dfp_path), group=cmd_arg.device_group) as accl:
        ofmaps, latency, fps = accl.run(ifmaps, frames=100)
    return ofmaps, latency, fps

def upload_result_to_sql(OS_Name, OS_Version, CPU_Name, Logical_CPUs, Max_CPU_Frequency, Total_Memory,
                         Kdriver_Version, FW_CommitID, DateCode, ManufacturerID, MPU_PLL, Voltage,
                         Model, FPS, CPU_Usage, Power, Temperature, Result):
    try:
        Date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        conn = pymssql.connect(
            server='192.168.1.238',
            user='sa',
            password='MPU_rocks',
            database='TestResultDB',
            as_dict=True
        )
        cursor = conn.cursor()

        sql_insert_query = """
        INSERT INTO Measurement (OS_Name, OS_Version, CPU_Name, Logical_CPUs, Max_CPU_Frequency, Total_Memory,
                                Kdriver_Version, FW_CommitID, DateCode, ManufacturerID, MPU_PLL, Voltage,
                                Date, Model, FPS, CPU_Usage, Power, Temperature, Result)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        print('Result {}'.format(Result))

        cursor.execute(sql_insert_query, (OS_Name, OS_Version, CPU_Name, Logical_CPUs, Max_CPU_Frequency, Total_Memory,
                                          Kdriver_Version, FW_CommitID, DateCode, ManufacturerID, MPU_PLL, Voltage,
                                          Date, Model, FPS, CPU_Usage, Power, Temperature, Result))

        conn.commit()

        print("Test result inserted successfully.")

    except pymssql.DatabaseError as e:
        print(f"Database error occurred: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

def run_driver_regression(cmd_arg):
    num_frames = 2
    prefix = ["k", "onnx_", "pt_", "tf_", "tfl_", "model_"]
    error_count = 0

    testcase_dir = []
    for p in prefix:
        path_str = str(Path(cmd_arg.dataflow_dir, p + '*'))
        testcase_dir.extend(glob.glob(path_str))

    # Device information
    OS_Name = platform.system() + platform.release()
    OS_Version = platform.version()
    CPU_Name = get_cpu_name()
    Logical_CPUs = psutil.cpu_count(logical=True)
    Max_CPU_Frequency = psutil.cpu_freq().max
    Total_Memory = psutil.virtual_memory().total

    Kdriver_Version = mxa.get_kdriver_version(cmd_arg.device_group)
    FW_CommitID = mxa.get_fw_commit(cmd_arg.device_group)
    DateCode = mxa.get_date_code(cmd_arg.device_group)
    ManufacturerID = mxa.get_manufacturer_id(cmd_arg.device_group)
    Frequency = mxa.get_frequency(cmd_arg.device_group, 0)
    Voltage = mxa.get_voltage(cmd_arg.device_group)
    Thermal_threshold = mxa.get_thermal_threshold(cmd_arg.device_group)


    testcase_dir = sorted(testcase_dir)
    for t in testcase_dir:
        num_out_ports = 0
        path = Path(t)
        # Check if results failed  with exception
        print('{}: Running {}...'.format(time.strftime("%m-%d %H:%M:%S"), path.name))

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
                interval = 0.001
                fps_list = []
                cpu_list = []
                power_list = []
                temperature_lists = []
                for loop in range(cmd_arg.loopAverage):
                    startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    print('Loop {} Start run {}'.format(loop, startTime))

                    # FIX ME: Skip cpu usage/power/temperature calculate now, because of running with multi process will hang.
                    ofmaps, latency, fps = run_benchmark(dfp_path, cmd_arg, ifmaps)
                    fps_list.append(fps)
                    loop_cpu = 0
                    loop_power = 0
                    loop_temperature = 0
                    print(f"    fps={fps:.2f}, cpu={loop_cpu:.2f}, power={loop_power:.2f}, temperature={loop_temperature:.2f}")

                average_fps = fps
                average_cpu_usage = 0
                average_power = 0
                average_temperature = 0
            except Exception as e:
                print(e)
                return - 1

            if (ofmaps == None) and (latency == -1):  #accl.run fps finished
                print('{0:64s}, {1:4s}, {2:6.3f} FPS, CPU {3:.3f}, {4:.3f}mW, {5:.3f}C, {6:.3f}MHz, {7:.3f}mV, Thermal {8:.3f}C\n'.format(path.name, "PASS", average_fps, average_cpu_usage, average_power, average_temperature, Frequency, Voltage, Thermal_threshold))

        if ofmaps is not None:
            passed = []
            for f in range(num_frames):
                for j in range(num_out_ports):
                    if ofmaps[j].shape == ofmaps_t[j].shape:
                        if np.allclose(ofmaps[j], ofmaps_t[j], atol=1e-4, equal_nan=True):
                            passed.append(True)
                        else:
                            passed.append(False)

                    else:
                        passed.append(False)
                        result = -7

            if all(passed):
                result = 0
            else:
                result = 'FAIL_COMPARE'
        else:
            result = 'FAIL_OFMAP'

        if result == 0:
            num_frames = ofmaps[0].shape[0]
            result = 'PASS'
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

        upload_result_to_sql(OS_Name, OS_Version, CPU_Name, Logical_CPUs, Max_CPU_Frequency, Total_Memory,
                                        Kdriver_Version, hex(FW_CommitID), hex(DateCode), hex(ManufacturerID), Frequency, Voltage,
                                        path.name, average_fps, average_cpu_usage, average_power, average_temperature, result)

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
