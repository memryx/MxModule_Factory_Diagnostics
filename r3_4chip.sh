#!/bin/bash

rm -rf log/*.csv; python3 ./4_testsuit/memx_performance.py --dir ./4_testsuit/pat4chip -f 500
