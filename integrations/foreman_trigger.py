import requests
import time
import datetime
import os

# --- CONFIGURATION ---
# Get your key from: https://rapidapi.com/cnorris1316/api/gridwatch-us-telemetry
RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY_HERE"

# Region Options: PJM, MISO, ERCOT, SPP, NYISO, ISONE, CAISO
REGION = "ERCOT"

# Safety Thresholds
PRICE_CAP = 200        # Shut down if price > $200/MWh
STRESS_CAP = 90        # Shut down if grid stress > 90%

# Hysteresis / Safety Settings
COOLDOWN_MINUTES = 15  # Minutes grid must be NORMAL before resuming

# Simulation Mode (Set to False to actually execute shutdown commands)
SIMULATION_MODE = True

# --- FOREMAN CONFIGURATION ---
FOREMAN_ENABLED = True
FOREMAN_API_TOKEN = "YOUR_FOREMAN_TOKEN"
FOREMAN_MINER_IDS = [123, 456] # List of Miner IDs to control (Required)

# --- STATE TRACKING (DO NOT EDIT) ---
CURRENTLY_CURTAILED = False
LAST_NORMAL_TIME = None

def stop_mining_rigs():
    """
    Executes shutdown logic for Foreman.
    """
    print(f"   [ACTION] 🛑 SENDING SHUTDOWN SIGNAL TO FOREMAN...")

    if FOREMAN_ENABLED:
        try:
            url = "https://api.foreman.mn/api/v2/miners/command"
            headers = {"Authorization": f"Token {FOREMAN_API_TOKEN}"}
            # 'stop' pauses mining; usually safer than full power off
            payload = {"command": "stop", "miner_ids": FOREMAN_MINER_IDS}

            requests.post(url, json=payload, headers=headers)
            print("      -> Foreman: Stop command sent.")
        except Exception as e:
            print(f"      -> Foreman Error: {e}")

def resume_mining_rigs():
    """
    Executes resume logic for Foreman.
    """
    print(f"   [ACTION] SENDING RESUME SIGNAL TO FOREMAN...")

    if FOREMAN_ENABLED:
        try:
            url = "https://api.foreman.mn/api/v2/miners/command"
            headers = {"Authorization": f"Token {FOREMAN_API_TOKEN}"}
            payload = {"command": "start", "miner_ids": FOREMAN_MINER_IDS}

            requests.post(url, json=payload, headers=headers)
            print("      -> Foreman: Start command sent.")
        except Exception as e:
            print(f"      -> Foreman Error: {e}")

def check_grid_status():
    global CURRENTLY_CURTAILED, LAST_NORMAL_TIME

    url = "https://gridwatch-us-telemetry.p.rapidapi.com/api/curtailment"

    querystring = {
        "region": REGION,
        "price_cap": str(PRICE_CAP),
        "stress_cap": str(STRESS_CAP)
    }

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "gridwatch-us-telemetry.p.rapidapi.com"
    }

    try:
        print(f"Checking {REGION} grid status...", end="\r")
        response = requests.get(url, headers=headers, params=querystring, timeout=10)

        if response.status_code != 200:
            print(f"\n❌ API Error: {response.status_code} - {response.text}")
            return

        data = response.json()
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        if data.get('curtail'):
            # CASE 1: CRITICAL
            if not CURRENTLY_CURTAILED:
                print(f"\n[{timestamp}] 🔴 CURTAILMENT SIGNAL RECEIVED!")
                print(f"   Reason: {data['trigger_reason']}")
                print(f"   Price: ${data['metrics']['price_usd']}/MWh | Load: {data['metrics']['load_mw']} MW")

                if not SIMULATION_MODE:
                    stop_mining_rigs()
                    CURRENTLY_CURTAILED = True
                else:
                    print("   [SIMULATION] Foreman Stop command would fire.")
                    CURRENTLY_CURTAILED = True

            LAST_NORMAL_TIME = None

        else:
            # CASE 2: NORMAL
            if CURRENTLY_CURTAILED:
                if LAST_NORMAL_TIME is None:
                    print(f"\n[{timestamp}] 🟡 Grid Normal. Starting {COOLDOWN_MINUTES}m cooldown...")
                    LAST_NORMAL_TIME = datetime.datetime.now()

                elapsed = datetime.datetime.now() - LAST_NORMAL_TIME
                remaining = (COOLDOWN_MINUTES * 60) - elapsed.total_seconds()

                if remaining <= 0:
                    print(f"\n[{timestamp}] 🟢 Cooldown Complete. Resuming Foreman.")
                    if not SIMULATION_MODE:
                        resume_mining_rigs()
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                    else:
                        print("   [SIMULATION] Foreman Start command would fire.")
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                else:
                    print(f"\n[{timestamp}] 🟡 Waiting for cooldown ({int(remaining)}s)...")
            else:
                print(f"\n[{timestamp}] 🟢 Grid Normal. Foreman Running.")

            print(f"   Price: ${data['metrics']['price_usd']}/MWh")

    except Exception as e:
        print(f"\nError connecting to GridWatch: {e}")

if __name__ == "__main__":
    print(f"--- GridWatch 'Kill Switch' (Foreman) Started ---")
    print(f"Monitoring: {REGION}")
    print(f"Thresholds: Price > ${PRICE_CAP} | Stress > {STRESS_CAP}%")
    print(f"Cooldown: {COOLDOWN_MINUTES} Minutes")
    print(f"Press Ctrl+C to stop.\n")

    while True:
        check_grid_status()
        time.sleep(300)
