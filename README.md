# GridWatch Python Client (Official)

A lightweight, automated "Kill Switch" for Bitcoin miners, datacenters, and homelabbers.
This script monitors real-time US Power Grid telemetry via the [GridWatch API](https://rapidapi.com/cnorris1316/api/gridwatch-us-telemetry) and triggers a curtailment (shutdown) signal when electricity prices spike or grid reliability is at risk.

## Why use this?
* **Save Money:** Automatically pause high-wattage equipment when wholesale (LMP) prices exceed your profitability threshold (e.g., > $200/MWh).
* **Prevent Blackouts:** Reduce load during critical "Grid Stress" events (like Winter Storms) to support grid stability.
* **Redundancy:** Acts as a cloud-based backup watchdog if your local facility sensors fail.

## Supported Regions
### Real-Time ISOs (5-min updates)
* **PJM** (Mid-Atlantic)
* **ERCOT** (Texas)
* **MISO** (Midwest)
* **SPP** (Southwest)
* **NYISO** (New York)
* **ISO-NE** (New England)

### Regional Utilities (Hourly / EIA Data)
* **CAISO** (California)
* **Duke Energy** (Carolinas/Florida)
* **TVA** (Tennessee Valley)
* **Southern Company**
* *Plus 12+ others (FPL, NV Energy, PacifiCorp, etc.)*

## Quick Start

1.  **Get an API Key**
    You need a RapidAPI Key to fetch live data.
    [Get a Free API Key Here](https://rapidapi.com/cnorris1316/api/gridwatch-us-telemetry)

2.  **Install Requirements**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure & Run (Basic Mode)**
    Open `gridwatch_kill_switch.py` and set your thresholds:
    ```python
    RAPIDAPI_KEY = "YOUR_KEY_HERE"
    REGION = "ERCOT"
    PRICE_CAP = 150  # Shut down if price > $150
    ```
    Then run the monitor:
    ```bash
    python gridwatch_kill_switch.py
    ```

## Enterprise Integrations
Running a commercial farm? We have pre-built integrations for major management platforms.

* **Foreman Users:** [`integrations/foreman_trigger.py`](integrations/foreman_trigger.py)
    * *Native integration that triggers a "Pause" event via the Foreman API.*
* **HiveOS Users:** [`integrations/hiveos_trigger.py`](integrations/hiveos_trigger.py)
    * *Triggers a Flight Sheet change or Miner Stop command via HiveOS API.*

## Customization
The basic script includes a `stop_mining_rigs()` function.
You can modify this function to:
* Trigger a Tasmota/Shelly smart plug via HTTP.
* Send a shutdown command via SSH to your mining management node (Foreman, Awesome Miner, etc.).
* Send a webhook to Home Assistant.

## License
MIT License.
Feel free to fork and modify for your specific facility needs.
