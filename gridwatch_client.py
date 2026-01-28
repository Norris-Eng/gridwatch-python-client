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

# Simulation Mode (Set to False to actually execute commands)
SIMULATION_MODE = True

# --- STATE TRACKING (DO NOT EDIT) ---
# These variables track the "Live" state of your farm.
# Modifying them manually will break the auto-resume logic.
CURRENTLY_CURTAILED = False
LAST_NORMAL_TIME = None

def stop_mining_rigs():
    """
    Place your specific shutdown logic here.
    Examples:
    - Call a smart plug API (Tasmota/Kasa/Shelly)
    - SSH into a management node
    - Execute a local shell command
    """
    print("   [ACTION] 🛑 SENDING SHUTDOWN SIGNAL TO RIGS...")

def resume_mining_rigs():
    """
    Place your specific resume/start logic here.
    """
    print("   [ACTION] SENDING RESUME SIGNAL TO RIGS...")

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

        # --- LOGIC ENGINE ---
        if data.get('curtail'):
            # CASE 1: Grid is CRITICAL
            if not CURRENTLY_CURTAILED:
                print(f"\n[{timestamp}] 🔴 CURTAILMENT SIGNAL RECEIVED!")
                print(f"   Reason: {data['trigger_reason']}")
                print(f"   Price: ${data['metrics']['price_usd']}/MWh | Load: {data['metrics']['load_mw']} MW")

                if not SIMULATION_MODE:
                    stop_mining_rigs()
                    CURRENTLY_CURTAILED = True
                else:
                    print("   [SIMULATION] Shutdown command sent.")
                    CURRENTLY_CURTAILED = True

            # Reset cooldown timer because grid is bad again
            LAST_NORMAL_TIME = None

        else:
            # CASE 2: Grid is NORMAL
            if CURRENTLY_CURTAILED:
                # We are currently stopped, check if we can resume
                if LAST_NORMAL_TIME is None:
                    print(f"\n[{timestamp}] 🟡 Grid Normal. Starting {COOLDOWN_MINUTES}m cooldown timer...")
                    LAST_NORMAL_TIME = datetime.datetime.now()

                # Check how long it has been normal
                elapsed = datetime.datetime.now() - LAST_NORMAL_TIME
                remaining = (COOLDOWN_MINUTES * 60) - elapsed.total_seconds()

                if remaining <= 0:
                    print(f"\n[{timestamp}] 🟢 Cooldown Complete. Resuming Operations.")
                    if not SIMULATION_MODE:
                        resume_mining_rigs()
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                    else:
                        print("   [SIMULATION] Resume command sent.")
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                else:
                    # Still waiting
                    print(f"\n[{timestamp}] 🟡 Grid Normal. Waiting {int(remaining/60)}m {int(remaining%60)}s for safety cooldown.")

            else:
                # Normal Operation (Already Running)
                print(f"\n[{timestamp}] 🟢 Grid Normal. Operations Nominal.")

            print(f"   Price: ${data['metrics']['price_usd']}/MWh | Utilization: {data['metrics']['utilization_pct']}%")

    except Exception as e:
        print(f"\nError connecting to GridWatch: {e}")

if __name__ == "__main__":
    print(f"--- GridWatch 'Kill Switch' Monitor Started ---")
    print(f"Monitoring: {REGION}")
    print(f"Thresholds: Price > ${PRICE_CAP} | Stress > {STRESS_CAP}%")
    print(f"Cooldown: {COOLDOWN_MINUTES} Minutes")
    print(f"Press Ctrl+C to stop.\n")

    while True:
        check_grid_status()
        # Check every 5 minutes (300 seconds)
        time.sleep(300)
