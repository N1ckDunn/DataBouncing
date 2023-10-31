#!/usr/bin/env python

# A rebuilder script for/from John & Dave's Data-Bouncing project:	https://thecontractor.io/data-bouncing/
# This script will ingest bounced output and rebuild and/or process the content. If you dont know what you're doing, go read the posts :) 
# Have fun, dont do anything illegal... Seriously... don't. 

import os
import sys
import getopt
import time
import json
import base64
import math

from cryptography.fernet import Fernet


# Global variables
# Some can be changed on the command line, at some point they will be changed using a config file too
verbose = False
log_file = "therapist_log_" + time.strftime("%Y%m%d_%H%M%S") + ".log"		# Log file for each run
uuid_key = ""
key_file = "keyfile.key"
key = bytearray()
input_source = ""
output_stream = "outputdata.txt"
binary_file = True			# This will determine whether we write to a binary file or text file
write_to_file = True	# This will determine whether we write to a file or to a binary stream

CHUNK_SIZE = 63  # Size of data chunk in bytes

# Make the unique IDs and the chunk data available to other functions and processes
chunk_data = {}

# Not sure if we need this right now...
# Possibly allow change from the command line later
dns_root = "bc.53i.uk."
ignored_dns_records = [dns_root, "ns1" + dns_root, "ns2" + dns_root]


# Print usage
def usage():
	print("Therapist")
	print()
	print("Usage: therapist.py -i <input_stream> [options]")
	print("-i --input-source <input_stream>\tName of data input stream")
	print("-o --output-stream <output_stream>\tName of desired output stream")
	print("-k --key <AES_key>\t\t\tKey for AES decryption")
	print("-f --key-file <filename>\t\File holding AES decryption key")
	print("-u --uuid <uuid_key>\t\t\tUUID key for the file")
	print("-l --logfile <filename>\t\t\tWrite debug info to <filename>")
	print("-v --verbose\t\t\t\tExecute in verbose mode.")
	print("-h --help\t\t\t\tShow this help.")
	print()
	sys.exit(0)
	

# Check commandline args and replace any defaults with specified args
def parse_cmdline_args():

	arg_list = sys.argv[1:]
 
	# Options
	options = "i:o:k:f:u:l:hv"
	# Long options
	long_options = ["input-source", "output-stream", "key", "key-file", "uuid", "logfile", "verbose", "help"]
	 
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
		elif current_arg in ("-i", "--input-source"):
			# Specify input source
			globals()["input_source"] = current_val
		elif current_arg in ("-o", "--output-stream"):
			# Specify desired output location
			globals()["output_stream"] = current_val
		elif current_arg in ("-k", "--key"):
			#globals()["key"] =  bytes(current_val, "uft-8")
			globals()["key"] = current_val
		elif current_arg in ("-f", "--key-file"):
			globals()["key_file"] =  current_val
		elif current_arg in ("-u", "--uuid"):
			globals()["uuid_key"] =  current_val
		elif current_arg in ("-l", "--logfile"):
			# Change logfile name if required
			globals()["logfile"] =  current_val
		elif current_arg in ("-v", "--verbose"):
			# Verbose output
			globals()["verbose"] = True
	
	# Check that user has provided an an input stream
	if globals()["output_stream"].strip() == "":
		print("Provide an output destination to send data to.")
		exit(1)
	if globals()["uuid_key"] == "":
		print("Provide a UUID key for your data.")
		exit(1)
	if (globals()["key"] == b'') and (not os.path.isfile(globals()["key_file"])):
		print("Provide a key or key file for AES encryption.")
		exit(1)
	# Check if input file exists
	if not os.path.isfile(globals()["input_source"]):
		print("Input file '" + input_source + "' not found! Unable to continue...")
		exit(1)


# Decrypt the data using the provded info
def decrypt_data(data):

	# Get crypto key 
	if not (globals()["key"] == b''):
		fkey = globals()["key"]
	elif (os.path.isfile(globals()["key_file"])):
		with open(globals()["key_file"], "rb") as in_file: 
			fkey = in_file.read()
		in_file.close()
	
	print(type(fkey))
	print(fkey)
	print(len(fkey))

	fernet = Fernet(fkey)
	decrypted_data = fernet.decrypt(data)

	return decrypted_data


# Process the JSON file
def parse_input_data(data, uuid, output_stream, verbose, log_file, chunk_data, write_to_file, binary_file):

	# Check for valid usable JSON
	if data.startswith(uuid):
		# Extract chunk information
		parts = data.split('.')
		print("Splitting parts")
		print(parts)
		# Check if DNS request matches expected format
		# Should follow this format:	"0099.bc99b4f53d.1.204.wjfihfvp7bngmoids2vpaenoqbtucqkbifaue3coonfumtdigbgda3tskjzxcm2.cmvc3vf2vtc0000qv010gkpsb7wyyyyyb"
		if len(parts) != 6:
			print("Wrong format for full-id data.")
			return
		try:
			#"{uuid_key}.{file_id}.{chunk_id}.{total_chunks}.{encoded_data}.{exfil}"
			random_hex, file_id, position, total_chunks, chunk, = parts[0], parts[1], int(parts[2]), int(parts[3]), parts[4]
		except ValueError:
			# Exit if the expected integer values are not integers
			print("Unexpected formatting of value in DNS reord.")
			return

		# Initialize or update chunk_data
		if random_hex not in globals()["chunk_data"]:
			chunk_data[random_hex] = {"total_chunks": total_chunks, "received_chunks": {}}

		if position not in chunk_data[random_hex]["received_chunks"]:
			print("Received chunk" + str(position) + " for target: " + random_hex)
			sys.stdout.flush()

			# Store chunk
			chunk_data[random_hex]["received_chunks"][position] = chunk

		# Check if all chunks have been received
		if len(chunk_data[random_hex]["received_chunks"]) == total_chunks:

			if verbose == True:
				print("All chunks received. Reconstructing data.")

			# Reconstruct the decoded strings
			reconstructed = "".join([chunk_data[random_hex]["received_chunks"][index+1] for index in range(total_chunks)])

			# Base32 unencode the chunk (pad if necessary
			pad_length = math.ceil(len(reconstructed) / 8) * 8 - len(reconstructed)
			print("Pad length:	" + str(pad_length))

			reconstructed += ('=' * pad_length)
			fulldata =  reconstructed.upper()

			# Restore to binary before the decode takes place
			decoded_data = b''
			decoded_data = base64.b32decode(fulldata)

			# Decrypt data
			decrypted_data = decrypt_data(decoded_data)

			# Save to output stream as appropriate (text file or binary stream)
			if write_to_file == True:
				if binary_file == False:
					if verbose == True:
						print("Writing tp text file.")
					with open(output_stream, "w") as out_file:  # Save as .txt for ascii data
						out_file.write(decrypted_data)
				else:
					if verbose == True:
						print("Writing tp binary file.")
					# At some point in the future, allow further options for proper stream redirection
					with open(output_stream, "wb") as out_file:  # Save as .bin for binary data
						out_file.write(decrypted_data)
			else:
				# Write to stream
				print("Functionality not yet implemented.")		# Populating the else block to avoid error

			# Cleanup chunk_data for this random_hex
			del chunk_data[random_hex]

		else:
			if verbose == True:
				print("Processing chunk: " + str(position))
			# If the last chunk is received but not all chunks are received
			if position == total_chunks:
				all_positions = set(range(1, total_chunks + 1))
				received_positions = set(chunk_data[random_hex]["received_chunks"].keys())
				missing_positions = all_positions - received_positions
				print(f"Missing chunks {' '.join(map(str, sorted(missing_positions)))} for {random_hex}")


# Application entry point
if __name__ == "__main__":
	
	# Read cmdline args
	parse_cmdline_args()
	
	# Array to hold JSON data, and array of arrays of JSON to be passed to cores
	json_data = {}
	all_data = []

	# Read lines from the JSON file into array of JSON objects
	with open(globals()["input_source"], 'r') as input_file:
		index =1
		# Populate array with JSON data
		for json_obj in input_file:
			print(index)
			index += 1
			# Process JSON data
			try:
				json_content = json.loads(json_obj)

				# We do this as interactsh server renders all JSON content inside the app attribute 
				if "app" in json_content:
					temp_data = json_content["app"]
					json_data = json.loads(temp_data)
				else:
					json_data = json_content
			except:
				print("Error reading and parsing data from JSON file.")

	for data in json_data["data"]:
		parse_input_data(data["full-id"], globals()["uuid_key"], globals()["output_stream"], globals()["verbose"], globals()["log_file"], globals()["chunk_data"], globals()["write_to_file"], globals()["binary_file"])
		
	# Close log file after checking processes have completed
