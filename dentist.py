#!/usr/bin/env python

# An extractor script for/from John & Dave's Data-Bouncing project:	https://thecontractor.io/data-bouncing/
# This script will extract JSON data and write to an output file for the bouncer. If you dont know what you're doing, go read the posts :) 
# Have fun, dont be a dick... Seriously... don't. 

import json
import re
import sys

def usage():
    print("Usage: " + sys.argv[0] + " <path_to_json_file> <string_to_remove>")
    exit(1)

# Check for cmdline arguments
if (len(sys.argv[:]) < 2):
    usage()
elif(not sys.argv[1] or not sys.argv[2]):
    usage()

# Assign arguments to variables
json_file = sys.argv[1]
string_to_remove = sys.argv[2]

# Array to hold final output
output_lines = []
data = []

# Process the JSON file and write the output to output file
with open(json_file, 'r') as input_file:
    for json_obj in input_file:
        data = json.loads(json_obj)

        # Extract data
        target = data.get("full-id", [])
        parts = target.split(".")[0:3]

        # Remove specified string
        joined_string = '.'.join(parts)
        lowercase_string = joined_string.lower()
        processed_string = lowercase_string.replace(string_to_remove, "")
    
        if re.match('^(host\.|xff\.|ref\.|wafp\.|cfcon\.|root@\.|rip\.|trip\.|xclip\.|ff\.|origip\.|clip\.)', processed_string):
            output_lines.append(processed_string)

# Sort results and write to output file
output_lines.sort()
output_lines = list(set(output_lines))

with open('DataBouncers.txt', 'w') as output_file:
    output_file.write('\n'.join(output_lines))

# Inform user that data has been written to output file
print("Data has been written to DataBouncers.txt")
