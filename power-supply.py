#!/usr/bin/env python3
import argparse
import requests
import subprocess

maxPowerOutlets = 8

def setPowerOutletState(ip: str, user: str, pword: str, outletNumber: int, state: bool):

  # Checkout outlet number is within expected range
  if outletNumber < 1 or outletNumber > maxPowerOutlets:
    print("[ERROR]: Specified Outlet Number {} is out of range [{}, {}].".format(outletNumber, 1, maxPowerOutlets))
    exit(2)

  # Convert boolean to string
  stateStr = "true" if state else "false"

  # Prepare the request to power on/off outlet
  powerOnUrl = "http://{}/restapi/relay/outlets/{}/state/".format(ip, outletNumber)
  payload = "value={}".format(stateStr)
  headers = {
    "X-CSRF": "x",  # Custom header
    "Content-Type": "application/x-www-form-urlencoded"  # Ensures correct encoding
  }
  auth = requests.auth.HTTPDigestAuth(args.user, args.pword)

  # Send request
  response = requests.put(powerOnUrl, data=payload, headers=headers, auth=auth)

  # Report of request was a success or failure
  if response.status_code == 200 or response.status_code == 204:
    print("Successfully set outlet {} to {}.".format(outletNumber, stateStr))
    print(response.text)
  else:
    print("Failed to set outlet {} to {}.".format(outletNumber, stateStr))
    print(response.text)

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

  if(args.status):
    showPowerSupplyStatus(args.ip, args.user, args.pword)
  if(args.on):
    setPowerOutletState(args.ip, args.user, args.pword, args.on, True)
  if(args.off):
    setPowerOutletState(args.ip, args.user, args.pword, args.off, False)
