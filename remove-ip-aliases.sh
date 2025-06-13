#!/bin/bash

# Remove IP aliases for Tasmota devices

echo "Removing IP aliases for Tasmota devices..."

# Remove IP aliases for the devices
sudo ifconfig lo0 -alias 172.25.0.100
sudo ifconfig lo0 -alias 172.25.0.101
sudo ifconfig lo0 -alias 172.25.0.102

echo "IP aliases removed." 