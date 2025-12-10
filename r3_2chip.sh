#!/bin/bash

rm -rf log/*.csv; python3 ./4_testsuit/memx_performance.py --dir ./4_testsuit/pat2chip -f 2000
