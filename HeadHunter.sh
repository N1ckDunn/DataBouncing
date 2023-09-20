#!/bin/bash

# Pre-flight check to verify and install necessary utilities
for utility in curl parallel bc; do
  if ! command -v $utility &> /dev/null; then
    read -p "$utility is not installed. Would you like to install it? (y/N) " yn
    case $yn in
      [Yy]* )
        if [[ $EUID -ne 0 ]]; then
          echo "Please run this script as root or use sudo to install $utility."
          exit 1
        fi
        if command -v apt &> /dev/null; then
          apt update && apt install -y $utility
        elif command -v yum &> /dev/null; then
          yum install -y $utility
        else
          echo "Could not find a package manager to install $utility. Please install it manually."
          exit 1
        fi
        ;;
      * )
        echo "$utility is required for this script to run. Exiting."
        exit 1
        ;;
    esac
  fi
done

# Default OOB domain
oob_domain="OOB DOMAIN HERE"

# Parse command-line arguments for the OOB domain
while getopts ":oob:" opt; do
  case ${opt} in
    oob )
      oob_domain=$OPTARG
      ;;
    * )
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

# User agent to use in the requests
user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"

# Check if domains.txt file exists
if [[ ! -f domains.txt ]]; then
  echo "File domains.txt not found!"
  exit 1
fi

# Get the total number of non-empty lines in the domains.txt file
total_hosts=$(grep -c . domains.txt)

# Create a log file
log_file="script_log_$(date +"%Y%m%d_%H%M%S").txt"

# Export variables for access in parallel jobs
export user_agent
export oob_domain
export total_hosts
export log_file

# Define a function to process each domain, to be run in parallel
process_domain() {
  domain=$1
  current_host_number=$PARALLEL_SEQ

  # Skip empty lines
  [ -z "$domain" ] && return

  # Calculate the percentage of completion
  if (( total_hosts > 0 )); then
    percentage_complete=$(bc <<< "scale=2; ($current_host_number / $total_hosts) * 100")
  else
    percentage_complete=0
  fi

  # Append the special string to the truncated domain for the Host header

  
  # Set the origin to the current domain
  origin="https://$domain"
  
  # Set Host, Referer and X-Forwarded-For headers with "ref." and "xff." prefixes
  host_header="host.${domain}.${oob_domain}"
  Referer_header="ref.${domain}.${oob_domain}"
  x_forwarded_for_header="xff.${domain}.${oob_domain}"

  
  # Get the current timestamp
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")

  # Execute the curl command with the appropriate headers set
  curl -i -s -k -X $'GET' \
    --max-time 16 \
    -H $'User-Agent: '"${user_agent}" \
    -H $'Host: '"${host_header}" \
    -H $'Referer: '"${Referer_header}" \
    -H $'X-Forwarded-For: '"${x_forwarded_for_header}" \
    -H $'Connection: close' \
    -H $'Origin: '"${origin}" \
    $'http://'"${domain}"'/' > /dev/null 

  # Create a log message with the progress report
  log_message="$timestamp - Request sent to $domain - $current_host_number of $total_hosts ($percentage_complete% complete)"
  
  # Print the log message to the console
  echo "$log_message"
  
  # Log the message to the log file
  echo "$log_message" >> "$log_file"
}

export -f process_domain

# Run the process_domain function in parallel for each line in the domains.txt file
parallel -a domains.txt -j 100% process_domain
