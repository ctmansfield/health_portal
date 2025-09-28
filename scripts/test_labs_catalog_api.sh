#!/bin/bash

API_URL="http://localhost:8800/labs/metrics-catalog"

# Count total metrics
curl -s "$API_URL" | jq '. | length'

# List metric and label pairs
curl -s "$API_URL" | jq '.[] | {metric, label}' | less
