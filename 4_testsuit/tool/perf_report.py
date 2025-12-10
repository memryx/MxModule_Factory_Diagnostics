import os
import shutil
from pathlib import Path
import pandas as pd
import numpy  as np
import math
import csv
def result_processing(result_file):
    gloden_file = 'performance_gloden.csv'
    compare_file = 'performance_compare.csv'
    result_path = Path(result_file)
    gloden_path = Path(result_path.parent, gloden_file)
    compare_path = Path(result_path.parent, compare_file)
    print(result_path)
    print(gloden_path)
    print(compare_path)
    if gloden_path.is_file():
        usecols = ['Model', 'Result', 'FPS']
        df1 = pd.read_csv(str(gloden_path),
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'Result':str,
                                    'FPS':float})

        df2 = pd.read_csv(str(result_path),
                          usecols = usecols,
                          dtype = {'Model':str,
                                   'Result':str,
                                    'FPS':float})
        d1 = dict()
        for i in df1.index:
            d1[df1['Model'][i]] = df1['FPS'][i]
            #print(df1['Model'][i] + "is", df1['FPS'][i])
        d2 = dict()
        for i in df2.index:
            d2[df2['Model'][i]] = df2['FPS'][i]
            #print(df1['Model'][i] + "is", df1['FPS'][i])


        output_data = []
        output_data.append(['Model', 'Result', 'FPS', 'Testing', 'Percentage %'])
        for k,v in d2.items():
            if math.isnan(v) == False:
                if k in d1:
                    p = v/d1[k] * 100
                    if p > 90:
                        s = 'Good '
                    elif p > 70:
                        s = 'Check'
                    else:
                        s = 'Wrong'
                    output_data.append([k, s, d1[k], v, v/d1[k] * 100])
                else:
                    output_data.append([k, 'NEW ', v, v, 100])
            else:
                output_data.append([k, '----', '----', '----', '----'])


        with open(str(compare_path), 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(output_data)
    else:
        shutil.copy(str(result_path), str(gloden_path))

if __name__=="__main__":
    result_file = "performance_result.csv"
    result_processing(result_file)