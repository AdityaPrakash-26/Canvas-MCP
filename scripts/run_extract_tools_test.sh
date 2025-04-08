#!/bin/bash
# Script to run the extract tools test and save the output to a file

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the test and redirect output to a log file
python scripts/extract_tools_test.py --test > logs/extract_tools_test_$(date +%Y%m%d_%H%M%S).log 2>&1

echo "Test completed. Check the logs directory for results."
