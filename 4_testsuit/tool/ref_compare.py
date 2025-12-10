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
        epilog += "    » python ref_compare.py --file1 linux.csv --file2 windows.csv --tag1 linux --tag2 windows \n"

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
                             default =   "performance_result_linux.csv",
                             metavar =   "",
                             help    =   "The 1st performance data")

        control.add_argument("--file2",
                             dest    =   "file2",
                             action  =   "store",
                             type    =   str,
                             default =   "performance_result_windows.csv",
                             metavar =   "",
                             help    =   "The 2nd performance data")

        control.add_argument("--ref",
                             dest    =   "ref_file",
                             action  =   "store",
                             type    =   str,
                             default =   "reference_performance.csv",
                             metavar =   "",
                             help    =   "The 2nd performance data")

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
    system = 'performance'

    if os.path.isfile(file1):
        usecols = ['Model', 'Result', 'FPS']
        df1 = pd.read_csv(file1,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'Result':str,
                                    'FPS':float})
        #print(df1)
        df1.columns = ['Model', 'chips', 'Avg FPS']
        for i in df1.index:
            res = df1.at[i,'Model'][:df1.at[i,'Model'].index(system) + len(system)]
            df1.at[i,'Model'] = res
            df1.at[i,'chips'] = 4
        df1.to_csv('modified_' + file1, sep=',', encoding='utf-8', index=False)


    if os.path.isfile(file2):
        usecols = ['Model', 'Result', 'FPS']
        df2 = pd.read_csv(file2,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'Result':str,
                                    'FPS':float})
        df2.columns = ['Model', 'chips', 'Avg FPS']
        for i in df2.index:
            res = df2.at[i,'Model'][:df2.at[i,'Model'].index(system) + len(system)]
            df2.at[i,'Model'] = res
            df2.at[i,'chips'] = 4
        df2.to_csv('modified_' + file2, sep=',', encoding='utf-8', index=False)

    if os.path.isfile(ref_file):
        usecols = ['#','Model','target_system','chips','Frames','Total Runs','Finished Runs','Min FPS','Max FPS','Avg FPS','Delta FPS','Min Latency','Max Latency','Avg Latency','Delta Latency','Commit','Start Time (UTC)']
        df3 = pd.read_csv(ref_file,
                          usecols = usecols,
                          dtype = {'#':int,
                                   'Model':str,
                                   'target_system':str,
                                   'chips':int,
                                   'Frames':int,
                                   'Total Runs':int,
                                   'Finished Runs':int,
                                   'Min FPS':float,
                                   'Max FPS':float,
                                   'Avg FPS':float,
                                   'Min Latency':float,
                                   'Max Latency':float,
                                   'Avg Latency':float,
                                   'Delta Latency':float,
                                   'Commit':str,
                                   'Start Time (UTC)':str
                                   })
        filter_id = df3['target_system'] == 'Cascade+'
        new_df3 = df3.loc[filter_id]
        new_df3 = new_df3.loc[df3['chips'] <= 4]
        new_df3 = new_df3.sort_values(by=['Model'])
        new_df3 = new_df3.filter(['Model','chips', 'Avg FPS'])

        for i in new_df3.index:
            res = new_df3.at[i,'Model'][:new_df3.at[i,'Model'].index(system) + len(system)]
            new_df3.at[i,'Model'] = res

        new_df3.to_csv('modified_' + ref_file, sep=',', encoding='utf-8', index=False)


def result_post_processing(cmd_arg):
    file1       = 'modified_' + cmd_arg.file1
    file2       = 'modified_' + cmd_arg.file2
    ref_file    = 'modified_' + cmd_arg.ref_file
    compare_file= 'performance_compared.csv'

    if os.path.isfile(ref_file):
        usecols = ['Model', 'chips', 'Avg FPS']
        dfr = pd.read_csv(ref_file,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'chips':int,
                                   'Avg FPS':float})
        dfr.columns = ['Model', 'chips', 'Sim Avg FPS']

    if os.path.isfile(file1):
        tag1 = cmd_arg.tag1
        usecols = ['Model', 'chips', 'Avg FPS']
        df1 = pd.read_csv(file1,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'chips':int,
                                   'Avg FPS':float})

        dfr.insert(3, tag1 + ' chips', 4)
        dfr.insert(4, tag1 + ' Avg FPS', np.nan)
        dfr.insert(5, tag1 + ' / Sim', np.nan)

        for i in df1.index:
            #print(df1['Model'][i])
            if df1['Model'][i] in dfr['Model'].values:
                idx = dfr.index[dfr['Model'] == df1['Model'][i]]
                #print(idx)
                dfr.loc[idx, tag1 + ' Avg FPS'] = df1['Avg FPS'][i]
                dfr.loc[idx, tag1 + ' / Sim'] = df1['Avg FPS'][i] / abs(dfr.loc[idx, 'Sim Avg FPS'])
            else:
                print("N/A")
        dfr[tag1 + ' / Sim'] = dfr[tag1 + ' / Sim'].map("{0:.2f}".format)
        dfr[tag1 + ' Avg FPS'] = dfr[tag1 + ' Avg FPS'].map("{0:.2f}".format)
        #print(dfr)

    if os.path.isfile(file2):
        tag2 = cmd_arg.tag2
        usecols = ['Model', 'chips', 'Avg FPS']
        df2 = pd.read_csv(file2,
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'chips':int,
                                   'Avg FPS':float})

        dfr.insert(6, tag2 + ' chips', 4)
        dfr.insert(7, tag2 + ' Avg FPS', np.nan)
        dfr.insert(8, tag2 + ' / Sim', np.nan)

        for i in df2.index:
            #print(df1['Model'][i])
            if df2['Model'][i] in dfr['Model'].values:
                idx = dfr.index[dfr['Model'] == df2['Model'][i]]
                #print(idx)
                dfr.loc[idx, tag2 + ' Avg FPS'] = df2['Avg FPS'][i]
                dfr.loc[idx, tag2 + ' / Sim'] = df2['Avg FPS'][i] / abs(dfr.loc[idx, 'Sim Avg FPS'])

            else:
                print("N/A")
        dfr[tag2 + ' / Sim'] = dfr[tag2 + ' / Sim'].map("{0:.2f}".format)
        dfr[tag2 + ' Avg FPS'] = dfr[tag2 + ' Avg FPS'].map("{0:.2f}".format)
        #print(dfr)

    dfr.to_csv(compare_file, sep=',', encoding='utf-8', index=False)

if __name__=="__main__":
    cmd_arg = __parse()
    result_pre_processing(cmd_arg)
    result_post_processing(cmd_arg)
