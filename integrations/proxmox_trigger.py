import requests
import time
import datetime
import urllib3
from proxmoxer import ProxmoxAPI

# Disable SSL warnings for self-signed Proxmox certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
# Get your key from: https://rapidapi.com/cnorris1316/api/gridwatch-us-telemetry
RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY_HERE"
REGION = "ERCOT"

# Safety Thresholds
PRICE_CAP = 200        # Shut down if price > $200/MWh
STRESS_CAP = 90        # Shut down if grid stress > 90%
COOLDOWN_MINUTES = 15  # Minutes grid must be NORMAL before resuming

# Simulation Mode (Set to False to actually execute shutdowns)
SIMULATION_MODE = True

# --- PROXMOX CONFIGURATION ---
PROXMOX_ENABLED = True
PROXMOX_HOST = "192.168.1.X"      # IP address of your Proxmox Server
PROXMOX_USER = "root@pam"         # User (usually root@pam)
PROXMOX_PASSWORD = "YOUR_PASSWORD"
PROXMOX_NODE = "pve"              # Name of your node (check your web UI)
TARGET_VMS = [100, 101, 102]      # List of VM IDs to manage

# --- STATE TRACKING (DO NOT EDIT) ---
CURRENTLY_CURTAILED = False
LAST_NORMAL_TIME = None

def get_proxmox_connection():
    """Establishes a connection to the Proxmox API."""
    try:
        return ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False
        )
    except Exception as e:
        print(f"   [ERROR] Could not connect to Proxmox: {e}")
        return None

def stop_mining_rigs():
    """
    Executes GRACEFUL SHUTDOWN for Proxmox VMs.
    Protects filesystem integrity for AI/HPC workloads.
    """
    print(f"   [ACTION] 🛑 INITIATING GRACEFUL SHUTDOWN (SIGTERM)...")

    if PROXMOX_ENABLED:
        proxmox = get_proxmox_connection()
        if not proxmox: return

        for vmid in TARGET_VMS:
            try:
                # 1. Check status first
                status = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.current.get()
                if status.get('status') == 'running':
                    # 2. Send ACPI Shutdown (Soft Stop)
                    proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.shutdown.post()
                    print(f"      -> VM {vmid}: Shutdown signal sent.")
                else:
                    print(f"      -> VM {vmid}: Already stopped.")
            except Exception as e:
                print(f"      -> VM {vmid} Error: {e}")

def resume_mining_rigs():
    """
    Boots up Proxmox VMs.
    """
    print(f"   [ACTION] INITIATING VM STARTUP...")

    if PROXMOX_ENABLED:
        proxmox = get_proxmox_connection()
        if not proxmox: return

        for vmid in TARGET_VMS:
            try:
                status = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.current.get()
                if status.get('status') == 'stopped':
                    proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post()
                    print(f"      -> VM {vmid}: Start signal sent.")
                else:
                    print(f"      -> VM {vmid}: Already running.")
            except Exception as e:
                print(f"      -> VM {vmid} Error: {e}")

def check_grid_status():
    global CURRENTLY_CURTAILED, LAST_NORMAL_TIME

    url = "https://gridwatch-us-telemetry.p.rapidapi.com/api/curtailment"
    querystring = {"region": REGION, "price_cap": str(PRICE_CAP), "stress_cap": str(STRESS_CAP)}
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "gridwatch-us-telemetry.p.rapidapi.com"}

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
            # CASE 1: CRITICAL
            if not CURRENTLY_CURTAILED:
                print(f"\n[{timestamp}] 🔴 CURTAILMENT SIGNAL RECEIVED!")
                print(f"   Reason: {data['trigger_reason']}")
                print(f"   Price: ${data['metrics']['price_usd']}/MWh")

                if not SIMULATION_MODE:
                    stop_mining_rigs()
                    CURRENTLY_CURTAILED = True
                else:
                    print("   [SIMULATION] Proxmox Shutdown would fire.")
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
                    print(f"\n[{timestamp}] 🟢 Cooldown Complete. Resuming Operations.")
                    if not SIMULATION_MODE:
                        resume_mining_rigs()
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                    else:
                        print("   [SIMULATION] Proxmox Start command would fire.")
                        CURRENTLY_CURTAILED = False
                        LAST_NORMAL_TIME = None
                else:
                    print(f"\n[{timestamp}] 🟡 Waiting for cooldown ({int(remaining)}s)...")
            else:
                print(f"\n[{timestamp}] 🟢 Grid Normal. VMs Running.")

            print(f"   Price: ${data['metrics']['price_usd']}/MWh")

    except Exception as e:
        print(f"\nError connecting to GridWatch: {e}")

if __name__ == "__main__":
    print(f"--- GridWatch 'Proxmox Controller' Started ---")
    print(f"Targeting Node: {PROXMOX_NODE} | VMs: {TARGET_VMS}")
    print(f"Thresholds: Price > ${PRICE_CAP}")
    print(f"Press Ctrl+C to stop.\n")

    while True:
        check_grid_status()
        time.sleep(300)
