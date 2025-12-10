import os
import shutil
import pandas as pd
import numpy  as np
import math
import csv
import argparse

def __parse():
        """
        Read two memx_performance result and compare with reference_performance data
        """

        epilog = "Examples:\n"
        epilog += "\n"
        epilog += "    » python ref_compare.py --file1 sim_result.csv --file2 testing.csv --tag1 linux --tag2 windows \n"

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
        control.add_argument("--file1",
                             dest    =   "file1",
                             action  =   "store",
                             type    =   str,
                             default =   "model_explorer_perf_result_0305_staging.csv",
                             metavar =   "",
                             help    =   "The 1st performance data")

        control.add_argument("--file2",
                             dest    =   "file2",
                             action  =   "store",
                             type    =   str,
                             default =   "model_explorer_perf_result_0305_staging.csv",
                             metavar =   "",
                             help    =   "The 2nd performance data")

        control.add_argument("--ref",
                             dest    =   "ref_file",
                             action  =   "store",
                             type    =   str,
                             default =   "results_for_chip_bm_2_chips_2024_3_3.csv",
                             metavar =   "",
                             help    =   "The simulation performance data")

        control.add_argument("--result",
                             dest    =   "result_file",
                             action  =   "store",
                             type    =   str,
                             default =   "performance_result.csv",
                             metavar =   "",
                             help    =   "The output data file")

        control.add_argument("--compare",
                             dest    =   "compare_file",
                             action  =   "store",
                             type    =   str,
                             default =   "performance_compare.csv",
                             metavar =   "",
                             help    =   "The output data file 2")

        control.add_argument("--tag1",
                             dest    =   "tag1",
                             action  =   "store",
                             type    =   str,
                             default =   "Linux",
                             metavar =   "",
                             help    =   "File1 Tag")

        control.add_argument("--tag2",
                             dest    =   "tag2",
                             action  =   "store",
                             type    =   str,
                             default =   "Windows",
                             metavar =   "",
                             help    =   "File2 Tag")

        cmd_args = parser.parse_args()

        return cmd_args

def result_pre_processing(cmd_arg):
    file1  = cmd_arg.file1
    file2  = cmd_arg.file2
    ref_file   = cmd_arg.ref_file
    system = 'cascade_plus'

    if os.path.isfile(file1):
        usecols = ['Model', 'FPS']
        df1 = pd.read_csv(file1,
                          usecols = usecols,
                          dtype = {'Model':str,
                                    'FPS':float})
        #print(df1)
    
    if os.path.isfile(ref_file):
        usecols = ['model', 'chips', 'fps']
        df3 = pd.read_csv(ref_file,
                          usecols = usecols,
                          dtype = {'model':str,
                                   'chips':int,
                                   'fps':float
                                   })
        #print(df3)
    

def result_post_processing(cmd_arg):
    file1       = cmd_arg.file1
    file2       = cmd_arg.file2
    ref_file    = cmd_arg.ref_file
    compare_file= 'performance_compared.csv'

    if os.path.isfile(ref_file):
        usecols = ['model', 'chips', 'fps']
        dfr = pd.read_csv(ref_file,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'chips':int,
                                   'Avg FPS':float})
        before = len(dfr)
        dfr = dfr.loc[dfr['fps'] <= 2500]
        after = len(dfr)
        print('After remove {} Model Sim FPS > 2500 total {} Model Record'.format(before - after, after))
        dfr.columns = ['Model', 'chips', 'Sim Avg FPS']

    if os.path.isfile(file1):
        tag1 = cmd_arg.tag1
        usecols = ['Model', 'FPS']
        df1 = pd.read_csv(file1,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'FPS':float})

        dfr.insert(3, tag1 + ' chips', 2)
        dfr.insert(4, tag1 + ' Avg FPS', np.nan)
        dfr.insert(5, tag1 + ' / Sim', np.nan)

        for i in df1.index:
            #print(df1['Model'][i])
            if df1['Model'][i] in dfr['Model'].values:
                idx = dfr.index[dfr['Model'] == df1['Model'][i]]
                #print(idx)
                dfr.loc[idx, tag1 + ' Avg FPS'] = df1['FPS'][i]
                if df1['FPS'][i] > 0:
                    dfr.loc[idx, tag1 + ' / Sim'] = df1['FPS'][i] / abs(dfr.loc[idx, 'Sim Avg FPS'])
                else:
                    dfr.loc[idx, tag1 + ' / Sim'] = df1['FPS'][i]
            else:
                pass
                #print("N/A")
        dfr[tag1 + ' / Sim'] = dfr[tag1 + ' / Sim'].map("{0:.2f}".format)
        dfr[tag1 + ' Avg FPS'] = dfr[tag1 + ' Avg FPS'].map("{0:.2f}".format)
        #print(dfr)

    if os.path.isfile(file2):
        tag2 = cmd_arg.tag2
        usecols = ['Model', 'FPS']
        df2 = pd.read_csv(file2,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'FPS':float})

        dfr.insert(6, tag2 + ' chips', 2)
        dfr.insert(7, tag2 + ' Avg FPS', np.nan)
        dfr.insert(8, tag2 + ' / Sim', np.nan)

        for i in df2.index:
            #print(df1['Model'][i])
            if df2['Model'][i] in dfr['Model'].values:
                idx = dfr.index[dfr['Model'] == df2['Model'][i]]
                #print(idx)
                dfr.loc[idx, tag2 + ' Avg FPS'] = df2['FPS'][i]
                if df2['FPS'][i] > 0:
                    dfr.loc[idx, tag2 + ' / Sim'] = df2['FPS'][i] / abs(dfr.loc[idx, 'Sim Avg FPS'])
                else:
                    dfr.loc[idx, tag2 + ' / Sim'] = df2['FPS'][i]

            else:
                pass
                #print("N/A")
        dfr[tag2 + ' / Sim'] = dfr[tag2 + ' / Sim'].map("{0:.2f}".format)
        dfr[tag2 + ' Avg FPS'] = dfr[tag2 + ' Avg FPS'].map("{0:.2f}".format)
        #print(dfr)

    dfr.to_csv(compare_file, sep=',', encoding='utf-8', index=False)

if __name__=="__main__":
    cmd_arg = __parse()
    result_pre_processing(cmd_arg)
    result_post_processing(cmd_arg)
