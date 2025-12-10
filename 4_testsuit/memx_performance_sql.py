import mxa # mxa driver
import os, sys, glob, time, struct, argparse
from pathlib import Path
from utilities.dfp_inspect import dfp_inspect
from utilities.benchmark import Benchmark
from tool.perf_report import result_processing
import multiprocessing
import psutil
import time
import pymssql
import platform
import subprocess

burning_test = 1

def __parse():
        """
        Setup the parser (`argparse`) and parse the command line arguments.
        """

        epilog = "Examples:\n"
        epilog += "\n"
        epilog += "    » python memx_performance_sql.py                            # run all dfp one time with default frequency/voltage'. \n"
        epilog += "    » python memx_performance_sql.py --burning                  # run all dfp repeatly with default frequency/voltage'. \n"
        epilog += "    » python memx_performance_sql.py -g 1                       # run all dfp on device group 1 with default frequency/voltage'. \n"
        epilog += "    » python memx_performance_sql.py -fs 600 -fe 700 -fp 50     # run all dfp on device with default voltage and frequency 600/650/700 MHz'. \n"
        epilog += "    » python memx_performance_sql.py -vs 700 -fe 600 -fp 50     # run all dfp on device with default frequency and voltage 700/650/600 mV'. \n"

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
                             default =   500,
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
        control.add_argument("-l",
                             dest    =   "loopAverage",
                             action  =   "store",
                             type    =   int,
                             default =   1,
                             help    =   "Loop for getting average fps")

        control.add_argument("-fs",
                             dest    =   "frequency_start",
                             action  =   "store",
                             type    =   int,
                             default =   None,
                             help    =   "Mpu pll frequency start")

        control.add_argument("-fe",
                             dest    =   "frequency_end",
                             action  =   "store",
                             type    =   int,
                             default =   None,
                             help    =   "Mpu pll frequency end")

        control.add_argument("-fp",
                             dest    =   "frequency_step",
                             action  =   "store",
                             type    =   int,
                             default =   None,
                             help    =   "Mpu pll frequency end")

        control.add_argument("-vs",
                             dest    =   "mpu_voltage_start",
                             action  =   "store",
                             type    =   int,
                             default =   None,
                             help    =   "Mpu voltage end")

        control.add_argument("-ve",
                             dest    =   "mpu_voltage_end",
                             action  =   "store",
                             type    =   int,
                             default =   None,
                             help    =   "Mpu voltage end")

        control.add_argument("-vp",
                             dest    =   "mpu_voltage_step",
                             action  =   "store",
                             type    =   int,
                             default =   None,
                             help    =   "Mpu voltage end")

        control.add_argument("-t",
                             dest    =   "mpu_thermal_threshold",
                             action  =   "store",
                             type    =   int,
                             default =   None,
                             help    =   "Mpu pll frequency end")

        cmd_args = parser.parse_args()

        return cmd_args

def run_benchmark(dfp_path, cmd_arg, result_queue):
    with Benchmark(dfp=str(dfp_path), group=cmd_arg.device_group, frames=cmd_arg.frames) as accl:
        ofmaps, latency, fps = accl.run(frames=cmd_arg.frames, threading=True)
    result_queue.put((ofmaps, latency, fps))

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

def parse_verinfo():
    try:
        result = subprocess.run(['cat', '/sys/memx0/verinfo'], stdout=subprocess.PIPE, text=True)
        output = result.stdout

        # Initialize variables to store the extracted values
        kdriver_version = None
        fw_commit_id = None
        date_code = None
        manufacturer_id = None

        # Parse the output line by line
        for line in output.splitlines():
            if "kdriver version:" in line:
                kdriver_version = line.split(":")[1].strip()
            elif "FW_CommitID" in line:
                parts = line.split()
                fw_commit_id = parts[0].split("=")[1].strip()
                date_code = parts[1].split("=")[1].strip()
            elif "ManufacturerID" in line:
                manufacturer_id = line.split("=")[1].strip()

        # Return the parsed values
        return {
            "kdriver_version": kdriver_version,
            "FW_CommitID": fw_commit_id,
            "DateCode": date_code,
            "ManufacturerID": manufacturer_id
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

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

def frequency_check(cmd_arg):
    frequency_start = 0
    frequency_end = 0
    frequency_step = 0
    set_frequency = False

    if cmd_arg.frequency_start and cmd_arg.frequency_end and cmd_arg.frequency_step:
            frequency_start = cmd_arg.frequency_start
            if cmd_arg.frequency_start > cmd_arg.frequency_end:
                frequency_step = -cmd_arg.frequency_step
                frequency_end = cmd_arg.frequency_end-1
            else:
                frequency_step = cmd_arg.frequency_step
                frequency_end = cmd_arg.frequency_end+1

            set_frequency = True

    return frequency_start, frequency_end, frequency_step, set_frequency

def voltage_check(cmd_arg):
    mpu_voltage_start = 0
    mpu_voltage_end = 0
    mpu_voltage_step = 0
    set_voltage = False

    if cmd_arg.mpu_voltage_start and cmd_arg.mpu_voltage_end and cmd_arg.mpu_voltage_step:
            mpu_voltage_start = cmd_arg.mpu_voltage_start
            if cmd_arg.mpu_voltage_start > cmd_arg.mpu_voltage_end:
                mpu_voltage_step = -cmd_arg.mpu_voltage_step
                mpu_voltage_end = cmd_arg.mpu_voltage_end-1
            else:
                mpu_voltage_step = cmd_arg.mpu_voltage_step
                mpu_voltage_end = cmd_arg.mpu_voltage_end+1

            set_voltage = True

    return mpu_voltage_start, mpu_voltage_end, mpu_voltage_step, set_voltage

def main(cmd_arg, loop):
    #parameter setting
    prefix = ["k", "onnx_", "pt_", "tf_", "tfl_", "model_"]
    dfp_name = "model.dfp"
    result_file = 'performance_result.csv'

    # search dir
    testcase_dir = []
    for p in prefix:
        path_str = str(Path(cmd_arg.dataflow_dir, p + '*'))
        testcase_dir.extend(glob.glob(path_str))
    #check already_ran in output file or not
    result_path = Path(cmd_arg.log_dir, result_file)
    if burning_test or (Path.is_file(result_path) == False):
        already_ran = []
        with open(str(result_path), 'w') as f:
            f.write('{},{},{},{},{},{}\n'.format("Model", "Result", "FPS", "CPU", "Power", "Temperature"))
    else:
        with open(str(result_path), 'r') as f:
            already_ran = f.read().split('\n')[:-1]
            already_ran = [a.split(',')[0] for a in already_ran]

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
                try:
                    interval = 0.001
                    fps_list = []
                    cpu_list = []
                    power_list = []
                    temperature_lists = []
                    for loop in range(cmd_arg.loopAverage):
                        startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        print('Loop {} Start run {}'.format(loop, startTime))
                        result_queue = multiprocessing.Queue()
                        worker_process = multiprocessing.Process(target=run_benchmark, args=(dfp_path, cmd_arg, result_queue))
                        worker_process.start()
                        p = psutil.Process(worker_process.pid)
                        while worker_process.is_alive():
                            cpu_list.append(p.cpu_percent())
                            power = mxa.get_power(0)
                            power_list.append(power)
                            temperature = mxa.get_temperature(0)
                            temperature_lists.append(temperature)
                            time.sleep(interval)
                        worker_process.join()
                        ofmaps, latency, fps = result_queue.get()
                        fps_list.append(fps)
                        loop_cpu = sum(cpu_list) / len(cpu_list)
                        loop_power = sum(power_list) / len(power_list)
                        loop_temperature = sum(temperature_lists) / len(temperature_lists)
                        print(f"    fps={fps:.2f}, cpu={loop_cpu:.2f}, power={loop_power:.2f}, temperature={loop_temperature:.2f}")

                    average_fps = sum(fps_list) / len(fps_list)
                    average_cpu_usage = sum(cpu_list) / len(cpu_list) / 2
                    average_power = sum(power_list) / len(power_list)
                    average_temperature = sum(temperature_lists) / len(temperature_lists)

                except Exception as e:
                    print(e)
                    return - 1

                if (ofmaps == None) and (latency == -1):  #accl.run fps finished
                    print('{0:64s}, {1:4s}, {2:6.3f} FPS, CPU {3:.3f}, {4:.3f}mW, {5:.3f}C, {6:.3f}MHz, {7:.3f}mV, Thermal {8:.3f}C\n'.format(path.name, "PASS", average_fps, average_cpu_usage, average_power, average_temperature, Frequency, Voltage, Thermal_threshold))

                    with open(str(result_path), 'a') as f:
                        f.write('{},{},{},{},{},{}\n'.format(path.name, "PASS", average_fps, average_cpu_usage, average_power, average_temperature))

                    result = 'PASS'

                    upload_result_to_sql(OS_Name, OS_Version, CPU_Name, Logical_CPUs, Max_CPU_Frequency, Total_Memory,
                                         Kdriver_Version, hex(FW_CommitID), hex(DateCode), hex(ManufacturerID), Frequency, Voltage,
                                         path.name, average_fps, average_cpu_usage, average_power, average_temperature, result)
            else:
                continue

    #Post-processing
    if not cmd_arg.burning:
        result_processing(str(result_path))

    print('{}: Test Finished'.format(time.strftime("%m-%d %H:%M:%S")))
    return 0

if __name__=="__main__":
    cmd_arg = __parse()
    set_frequency = False
    result = 0
    loop = 1

    if cmd_arg.mpu_voltage_start:
        result = mxa.set_mpu_voltage(cmd_arg.device_group, cmd_arg.mpu_voltage_start)
    if cmd_arg.mpu_thermal_threshold:
        result = mxa.set_mpu_thermal_threshold(cmd_arg.device_group, cmd_arg.mpu_thermal_threshold)

    if cmd_arg.burning:
        burning_test = 1
        start_time = time.time()
        if cmd_arg.hours > 0:
            end_time = time.time() + 3600 * cmd_arg.hours
            while time.time() < end_time:
                print('{}: Round {}'.format(time.strftime("%m-%d %H:%M:%S"), loop))
                result = main(cmd_arg, loop)
                loop += 1
            print("time is up")
        else:
            while cmd_arg.burning:
                print('{}: Round {}'.format(time.strftime("%m-%d %H:%M:%S"), loop))
                result = main(cmd_arg, loop)
                loop += 1
    else:
        frequency_start, frequency_end, frequency_step, set_frequency = frequency_check(cmd_arg)
        voltage_start, voltage_end, voltage_step, set_voltage = voltage_check(cmd_arg)
        if set_frequency == True:
            if set_voltage == True:
                for frequency in range(frequency_start, frequency_end, frequency_step):
                    result = mxa.set_mpu_frequency(cmd_arg.device_group, 0xFF, frequency)
                    for voltage in range(voltage_start, voltage_end, voltage_step):
                        print('Frequency {}.{}.{}.{}.{} Voltage {}.{}.{}.{}.{}'.format(frequency_start, frequency_end, frequency_step, set_frequency, frequency, voltage_start, voltage_end, voltage_step, set_voltage, voltage))
                        result = mxa.set_mpu_voltage(cmd_arg.device_group, voltage)
                        result = main(cmd_arg, loop)
            else:
                for frequency in range(frequency_start, frequency_end, frequency_step):
                    print('Frequency {}.{}.{}.{}.{} Voltage {}.{}.{}.{}'.format(frequency_start, frequency_end, frequency_step, set_frequency, frequency, voltage_start, voltage_end, voltage_step, set_voltage))
                    result = mxa.set_mpu_frequency(cmd_arg.device_group, 0xFF, frequency)
                    result = main(cmd_arg, loop)
        else:
            if set_voltage == True:
                for voltage in range(voltage_start, voltage_end, voltage_step):
                    print('Frequency {}.{}.{}.{} Voltage {}.{}.{}.{}.{}'.format(frequency_start, frequency_end, frequency_step, set_frequency, voltage_start, voltage_end, voltage_step, set_voltage, voltage))
                    result = mxa.set_mpu_voltage(cmd_arg.device_group, voltage)
                    result = main(cmd_arg, loop)
            else:
                print('Frequency {}.{}.{}.{} Voltage {}.{}.{}.{}'.format(frequency_start, frequency_end, frequency_step, set_frequency, voltage_start, voltage_end, voltage_step, set_voltage))
                result = main(cmd_arg, loop)

    sys.exit(result)
