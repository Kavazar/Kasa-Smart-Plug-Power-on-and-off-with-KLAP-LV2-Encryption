# Script to SWITCH (on/off) the power state of a Kasa Smart Plug that uses KLAP LV2 encryption.
#   Developers: Andrew Anguish and Forrest Doddington -- version 26.3.1 (Sept 25, 2026)
#   License: see LICENSE

## SHELL Command information:
#
#  Example:
#  ~/kasa-env/bin/python ~/Documents/Kasa_Plug_Control/switch.py --ip 192.168.169.234 --var Stage_TV_Kasa_State --mode on
#
#  Explanation:
#  * First part tells Python script to run within a virtual environment.
#  * Second part calls the script that performs the Kasa Smart Plug action.
#  * Required parameters are:
#    --ip (IP address of the Kasa plug.)
#    --var (Name of a custom Variable within Bitfocus Companion that will store the power state.)
#    --mode (options: 'on', 'off')
#
#  Return value:
#  Sets the Bitfocus Companion custom variable to either "On" or "Off" based on the switch's power state.
#
##


## Load functionality
import asyncio
import requests
import argparse
from kasa import Discover
from kasa.transports.klaptransport import KlapTransportV2
from kasa.protocols import IotProtocol
from kasa.iot import IotPlug

## Load configuration for accessing Kasa and Bitfocus Companion
import config

## Parse required parameters
parser = argparse.ArgumentParser(description="Script to set or check the On/Off power state of a Kasa smart plug.")
parser.add_argument("--ip", required=True, type=str, help="IP address for the Kasa smart plug.")
parser.add_argument("--var", required=True, type=str, help="Custom variable name where Bitfocus Companion will store the state.")
parser.add_argument("--mode", required=True, type=str, help="Operation mode for the script: power on (on), power off (off), or check power state (state).")
args = parser.parse_args()

## Variable for Python script operation
OP = args.mode  # Operation to perform (turn on / turn off); values: on/off

## Variables for Kasa access
HOST = args.ip  # IP Address for the Kasa Smart Plug
USER = config.K_USER  # E-mail address for encrypted access to the Kasa Smart Plug
PASS = config.K_PASS  # Password for encrypted access to the Kasa Smart Plug

## Variables for Bitfocus Companion access
COMP_IP = config.BC_IP  # Bitfocus Companion IP address (localhost: 127.0.0.1)
COMP_PORT = config.BC_PORT  # Bitfocus Companion server port (default: 8000)
COMP_VAR = args.var  # Custom variable name used for button feedback

## Check Kasa smart plug power status (Power On = True; Power Off = False)
# Define the asynchronous program.
async def main():
    # Connect to a Kasa smart plug.
    disc = await Discover.discover_single(HOST, username=USER, password=PASS)
    protocol = IotProtocol(transport=KlapTransportV2(config=disc.config))
    plug = IotPlug(host=HOST, protocol=protocol)

    try: # Interact with the connected plug.
        # Get current plug state.
        await plug.update()
        if plug.is_on == True:
          state_before = 'On'
        elif plug.is_on == False:
          state_before = 'Off'
        else:
            state_before = 'Error'

        # Perform operation -- state check or state change
        if OP == 'on': # Turn plug power on.
          await plug.turn_on()
          await plug.update()
          if plug.is_on == True:
            state_after = 'On'
          elif plug.is_on == False:
            state_after = 'Off'
          else:
              state_after = 'Error'
          msgout = f"Kasa SWITCH '{OP}' called. Power changed from '{state_before}' to '{state_after}'. Updated custom variable '{COMP_VAR}' in Bitfocus Companion.'"

        elif OP == 'off': # Turn plug power off.
          await plug.turn_off()
          await plug.update()
          if plug.is_on == True:
            state_after = 'On'
          elif plug.is_on == False:
            state_after = 'Off'
          else:
              state_after = 'Error'
          msgout = f"Kasa SWITCH '{OP}' called. Power changed from '{state_before}' to '{state_after}'. Updated custom variable '{COMP_VAR}' in Bitfocus Companion.'"

        else:  # All other mode values are invalid. Don't change the power state.
          state_after = state_before
          msgout = f"Kasa Control SWITCH called with invalid --mode parameter: {OP}. (Valid options are 'on' or 'off'.) Toggle not performed and plug remains in power state '{state_after}'."


        # Send the ending state to Bitfocus Companion for storage as a custom variable value.
        try:
            url = f'http://{COMP_IP}:{COMP_PORT}/api/custom-variable/{COMP_VAR}/value?value={state_after}'
            response = requests.post(url)
            if response.status_code == 200:
                print(msgout)
            else:
                print(f"Failed. Status code: {response.status_code}, Response: {response.text}")

        except request.exceptions.RequestException as e:
            print(f"Error connecting to Bitfocus Companion: {e}")

    finally: # Close connection to the plug.
        await plug.disconnect()

# Execute the asynchronous program.
asyncio.run(main())
