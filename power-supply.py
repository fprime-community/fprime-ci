#!/usr/bin/env python3
import subprocess
import argparse

maxPowerOutlets = 8

def setPowerOutletState(ip: str, user: str, pword: str, outletNumber: int, state: bool):
  if outletNumber < 1 or outletNumber > maxPowerOutlets:
    print("[ERROR]: Specified Outlet Number {} is out of range [{}, {}].".format(outletNumber, 1, maxPowerOutlets))
    exit(2)

  stateStr = "true" if state else "false"
  print("output number {} state {}".format(outletNumber, stateStr))

  cmd = 'curl --digest -u {}:{} -X PUT -H "X-CSRF: x" --data "value={}" http://{}/restapi/relay/outlets/{}/state/'.format(user, pword, stateStr, ip, outletNumber)
  cmdToks = ['curl', '--digest', '-u', 'admin:1234', '-X', 'PUT', '-H', '"X-CSRF: x"', '--data', 'value=true', 'http://192.168.0.100/restapi/relay/outlets/1/state/']
  print(cmd)
  print(cmdToks)
  result = subprocess.run(cmdToks, capture_output=True, text=True)

  if result.returncode != 0:
    print("[Error]: {}".format(result.stderr))
    print("Failed to update outlet {} to {}. Exiting".format(outletNumber, stateStr))
    exit(3)

  print("Set outlet {} to {}.".format(outletNumber, stateStr))
  
def showPowerSupplyStatus(ip: str, user: str, pword: str):
  cmd = 'curl -k -u {}:{} -H "Accept:application/json" --digest https://{}/restapi/relay/outlets/all;/physical_state/'.format(user, pword, ip)
  cmdToks = cmd.split()
  print(cmd)
  print(cmdToks)
  result = subprocess.run(cmdToks, capture_output=True, text=True)

  if result.returncode != 0:
    print("[Error]: {}".format(result.stderr))
    print("Failed to get power supply status. Exiting")
    exit(1)

  for outlet in range(maxPowerOutlets):
    status = "ON" if result.stdout[outlet] == "true" else "OFF"
    print("Outlet {}: {}".format(outlet+1, status))
  
if __name__ == "__main__":
  ap = argparse.ArgumentParser("Tool to use CI Power Switch")
  ap.add_argument("--status", "-s", action="store_true", help="Show all power outlet's power on status")
  ap.add_argument("--on", "-t", type=int, help="Power on the specified power outlet. Range is [1,8].") 
  ap.add_argument("--off", "-f", type=int, help="Power off the specified power outlet. Range is [1,8].")
  ap.add_argument("--ip", "-i", type=str, default="192.168.0.100", help="Power outlet's IP. Default is %(default)s.")
  ap.add_argument("--user", "-u", type=str, default="admin", help="The user name. Default is %(default)s.")
  ap.add_argument("--pword", "-p", type=str, default="1234", help="The user name's pass. Default is %(default)s.")
  args = ap.parse_args()
  print(args)

  if(args.status):
    showPowerSupplyStatus(args.ip, args.user, args.pword)
  if(args.on):
    setPowerOutletState(args.ip, args.user, args.pword, args.on, True)
  if(args.off):
    setPowerOutletState(args.ip, args.user, args.pword, args.off, False)

'''
cmd = 'curl -k -u admin:1234 -H "Accept:application/json" --digest https://192.168.0.100/restapi/relay/outlets/2/physical_state/'
cmdToks = cmd.split()
result = subprocess.run(cmdToks, capture_output=True, text=True)

# Print the standard output and error
print("Output:", result.stdout)
#print("Error:", result.stderr)
#print("Return Code:", result.returncode)

'''

'''
import requests
from requests.auth import HTTPBasicAuth

with requests.Session() as se:
  url = "http://192.168.0.100"
  auth = HTTPBasicAuth("admin", "1234")
  response = se.get(url, auth=auth, verify=False)
  print(response)
  url = "http://192.168.0.100/outlet"
  params = {"1": "ON"}
  response = se.get(url, params=params, verify=False)
  print(response)


#response = requests.get(url, auth=auth, params=params, verify=False, timeout=30)
#response = requests.get(url, auth=auth, verify=False)

#print(response)
#print(response.text)
'''
