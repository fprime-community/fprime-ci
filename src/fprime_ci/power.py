""" fprime_ci.power: network power supply functions

@author ortega
"""
import argparse
import logging
import requests

maxPowerOutlets = 8

def setPowerOutletState(ip: str, user: str, pword: str, outletNumber: int, state: bool):

  # Checkout outlet number is within expected range
  if outletNumber < 0 or outletNumber >= maxPowerOutlets:
    raise Exception("Specified Outlet Number {} is out of range [{}, {}].".format(outletNumber, 0, maxPowerOutlets-1))

  # Convert boolean to string
  stateStr = "true" if state else "false"

  # Prepare the request to power on/off outlet
  powerOnUrl = "http://{}/restapi/relay/outlets/{}/state/".format(ip, outletNumber)
  payload = "value={}".format(stateStr)
  headers = {
    "X-CSRF": "x",  # Custom header
    "Content-Type": "application/x-www-form-urlencoded"  # Ensures correct encoding
  }
  auth = requests.auth.HTTPDigestAuth(user, pword)

  # Send request
  response = requests.put(powerOnUrl, data=payload, headers=headers, auth=auth)
  response.raise_for_status()

  logging.info("Successfully set outlet {} to {}.".format(outletNumber, stateStr))

def showPowerSupplyStatus(ip: str, user: str, pword: str):

  # Prepare the request to power on/off outlet
  powerStatusUrl = "http://{}/restapi/relay/outlets/all;/physical_state/".format(ip)
  headers = {
    "Accept": "application/json"
  }
  auth = requests.auth.HTTPDigestAuth(user, pword)

  # Send request
  response = requests.get(powerStatusUrl, headers=headers, auth=auth, verify=False)
  response.raise_for_status()

  toks = response.text[1:-1].split(",")

  for outlet in range(maxPowerOutlets):
    status = "ON" if toks[outlet] == "true" else "OFF"
    print("Outlet {}: {}".format(outlet, status))

def main():
  """ Entry point """
  ap = argparse.ArgumentParser("Tool to use CI Power Switch")
  ap.add_argument("--status", "-s", action="store_true", help="Show all power outlet's power on status")
  ap.add_argument("--on", "-t", type=int, help="Power on the specified power outlet. Range is [0,7].")
  ap.add_argument("--off", "-f", type=int, help="Power off the specified power outlet. Range is [0,7].")
  ap.add_argument("--ip", "-i", type=str, default="192.168.0.100", help="Power outlet's IP. Default is %(default)s.")
  ap.add_argument("--user", "-u", type=str, default="admin", help="The user name. Default is %(default)s.")
  ap.add_argument("--pword", "-p", type=str, default="1234", help="The user name's pass. Default is %(default)s.")
  args = ap.parse_args()

  logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="power-supply.log",
    filemode="w"
  )

  try:
    if(args.status):
      showPowerSupplyStatus(args.ip, args.user, args.pword)
    if(args.on != None):
      setPowerOutletState(args.ip, args.user, args.pword, args.on, True)
    if(args.off != None):
      setPowerOutletState(args.ip, args.user, args.pword, args.off, False)
  except Exception as exc:
    logging.error(f"{exc}")
 
if __name__ == "__main__":
  main()
