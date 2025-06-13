#!/bin/bash

# Setup IP aliases for direct access to Tasmota devices
# This script creates loopback aliases so you can access devices via their "real" IP addresses

echo "Setting up IP aliases for Tasmota devices..."

# Add IP aliases for the devices
sudo ifconfig lo0 alias 172.25.0.100 up
sudo ifconfig lo0 alias 172.25.0.101 up  
sudo ifconfig lo0 alias 172.25.0.102 up

echo "IP aliases created:"
echo "- Device 1: http://172.25.0.100 (kitchen_001)"
echo "- Device 2: http://172.25.0.101 (kitchen_002)" 
echo "- Device 3: http://172.25.0.102 (kitchen_003)"
echo ""
echo "You can now access the devices directly via their IP addresses!"
echo ""
echo "Example commands:"
echo "curl http://172.25.0.100"
echo "curl -u admin:test1234! 'http://172.25.0.100/cm?cmnd=Power%20ON'"
echo ""
echo "To remove aliases later, run: ./remove-ip-aliases.sh" 