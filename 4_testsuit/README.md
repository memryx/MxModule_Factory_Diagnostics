# Runtime Software Development Toolkit (RSDT)

Note : udriver, kdriver, pymodule are built by system_driver repo

Python Version
- 3.10.x
- 3.11.x

DFP Generated
- See MIX

Linux
- Install kernel module
- Install udriver.so
- Put Pymodule at root folder

Windows
- Install kernel driver
- Put udriver.dll at root folder
- Put Pymodule at root folder

**Please update the udriver and pymodule base on your requirement**
Tested Version Record
- system/driver 031cc1cdd802d447fb7dfb1162b95b5151533e90 (origin/master)

Python Module Requirement
- Numpy
- Pandas

See usage by "python script.py -h"
- python memx_performance                                                                     # run all dfp one time'.
- python memx_performance --burning                                                           # run all dfp repeatly'.
- python memx_performance --dir [folder path]                                                 # run test case under specific folder path'.
- python memx_performance_sql -fs [frequency start] -fe [frequency end] -fp [frequency step]  # run all dfp on device with default voltage and specific frequency range'
