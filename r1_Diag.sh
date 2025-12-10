#!/bin/bash
echo "rmtcmd 0 0x6d656d79 0x0" > /proc/memx0/debug; sleep 10; echo "fwlog 0" > /proc/memx0/cmd; sudo dmesg|tail -n 25
