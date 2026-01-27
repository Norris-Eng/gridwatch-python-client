import requests
import time
import datetime
import os

# --- CONFIGURATION ---
# Get your key from: https://rapidapi.com/cnorris1316/api/gridwatch-us-telemetry
RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY_HERE"

# Region Options: PJM, MISO, ERCOT, SPP, NYISO, ISO-NE
REGION = "ERCOT"

# Safety Thresholds
PRICE_CAP = 200        # Shut down if price > $200/MWh
STRESS_CAP = 90        # Shut down if grid stress > 90%

# Hysteresis / Safety Settings
COOLDOWN_MINUTES = 15  # Minutes grid must be NORMAL before resuming

# Simulation Mode (Set to False to actually execute shutdown commands)
SIMULATION_MODE = True

# --- HIVEOS CONFIGURATION ---
HIVE_ENABLED = True
HIVE_TOKEN = "YOUR_HIVE_API_TOKEN"
HIVE_FARM_ID = 123456
HIVE_WORKER_IDS = [112233, 445566] # List of IDs to manage

# --- STATE TRACKING (DO NOT EDIT) ---
CURRENTLY_CURTAILED = False
LAST_NORMAL_TIME = None

def stop_mining_rigs():
    """
    Executes shutdown logic for HiveOS (Miner Stop).
    """
    print(f"   [ACTION] 🛑 SENDING STOP SIGNAL TO HIVEOS...")

    if HIVE_ENABLED:
        try:
            url = f"https://api2.hiveos.farm/api/v2/farms/{HIVE_FARM_ID}/workers/command"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {HIVE_TOKEN}"
            }
            payload = {
                "worker_ids": HIVE_WORKER_IDS,
                "data": {
                    "command": "miner",
                    "data": { "action": "stop" }
                }
            }
            requests.post(url, json=payload, headers=headers, timeout=5)
            print("      -> HiveOS: Miner Stop sent.")
        except Exception as e:
            print(f"      -> HiveOS Error: {e}")

def resume_mining_rigs():
    """
    Executes resume logic for HiveOS (Miner Start).
    """
    print(f"   [ACTION] SENDING START SIGNAL TO HIVEOS...")

    if HIVE_ENABLED:
        try:
            url = f"https://api2.hiveos.farm/api/v2/farms/{HIVE_FARM_ID}/workers/command"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {HIVE_TOKEN}"
            }
            payload = {
                "worker_ids": HIVE_WORKER_IDS,
                "data": {
                    "command": "miner",
                    "data": { "action": "start" }
                }
            }
            requests.post(url, json=payload, headers=headers, timeout=5)
            print("      -> HiveOS: Miner Start sent.")
        except Exception as e:
            print(f"      -> HiveOS Error: {e}")

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
                    print("   [SIMULATION] HiveOS Stop command would fire.")
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
                    print(f"\n[{timestamp}] 🟢 Cooldown Complete. Resuming HiveOS.")
                    if not SIMULATION_MODE:
                        resume_mining_rigs()
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                    else:
                        print("   [SIMULATION] HiveOS Start command would fire.")
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                else:
                    print(f"\n[{timestamp}] 🟡 Waiting for cooldown ({int(remaining)}s)...")
            else:
                print(f"\n[{timestamp}] 🟢 Grid Normal. HiveOS Running.")

            print(f"   Price: ${data['metrics']['price_usd']}/MWh")

    except Exception as e:
        print(f"\nError connecting to GridWatch: {e}")

if __name__ == "__main__":
    print(f"--- GridWatch 'Kill Switch' (HiveOS) Started ---")
    print(f"Monitoring: {REGION}")
    print(f"Thresholds: Price > ${PRICE_CAP} | Stress > {STRESS_CAP}%")
    print(f"Cooldown: {COOLDOWN_MINUTES} Minutes")
    print(f"Press Ctrl+C to stop.\n")

    while True:
        check_grid_status()
        time.sleep(300)
