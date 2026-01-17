#!/bin/bash

# Navigate to your script directory
cd /root/Bot/

# Activate virtual environment if you have one (optional)
# source /path/to/your/venv/bin/activate

# Run the Python script
python3 generate.py

# Log the execution
echo "$(date): Smile.One order script executed" >> /root/Documents/cron.log
