#!/bin/bash

# Wait for RabbitMQ to be ready
echo "Waiting for RabbitMQ to be ready..."
timeout=60
counter=0
while ! nc -z $RABBITMQ_HOST 5672; do
  if [ $counter -ge $timeout ]; then
    echo "Timeout waiting for RabbitMQ after ${timeout} seconds"
    exit 1
  fi
  echo "Waiting for RabbitMQ... ($counter/$timeout)"
  sleep 2
  counter=$((counter + 2))
done

# Additional wait to ensure RabbitMQ is fully initialized
echo "RabbitMQ is responding, waiting additional 10 seconds for full initialization..."
sleep 10
echo "Starting device simulator..."

# Start the CLI application
python -m tasmota_sim.cli 