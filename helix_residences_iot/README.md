# IoT-Based Environmental Comfort and Air Quality Monitoring for The Helix Residences

## Overview

This project is a simulated IoT system for **The Helix Residences** in **Helix Park**. It focuses on **Environmental Comfort & Air Quality** in shared residential spaces such as the lobby, gym, co-working space, corridor, and rooftop lounge.

The main idea is to show how a small IoT monitoring system could help facilities staff move from reactive complaint handling to more proactive monitoring. The system simulates environmental readings, classifies conditions, raises alerts, stores logs, and gives simple operational recommendations.

The project has two linked parts:

- a Python desktop dashboard
- a Wokwi ESP32 sensing node

## What the System Monitors

- temperature
- humidity
- air quality proxy
- light level proxy
- vent or window state

The air quality figure in the dashboard is a **simulated indoor air-quality proxy** in ppm-style units. It is meant to behave like a combined CO2/VOC trend indicator rather than a real certified AQI reading.

## Main Features

- live dashboard for five communal zones
- Safe / Warning / Danger classification
- alerts and recommendation messages
- recent history and trend charts
- anomaly injection
- CSV and JSON logging
- chart export
- deterministic simulation using a fixed seed
- basic unit tests

## Project Structure

```text
helix_residences_iot/
├── config/
├── data/
├── outputs/
├── report/
├── src/
├── tests/
├── wokwi/
├── gitlog.txt
├── README.md
└── requirements.txt
```

## Install

```bash
pip install -r requirements.txt
```

## Run the Dashboard

From the project root:

```bash
python3 -m src.main
```

## How to Use It

1. Open the dashboard.
2. Click `Start Simulation`.
3. Watch the live table update across the zones.
4. Pick a zone and metric to inspect its trend.
5. Apply a scenario such as `ventilation_failure` or `poor_air_quality`.
6. Review alerts, recommendations, and exported logs.

## How the Simulation Works

The simulator is not just random. Each zone has its own baseline values and behaviour:

- the gym tends to run warmer and more humid
- the co-working space tends to suffer air-quality decline during busier periods
- the corridor can show lower lighting
- the lobby fluctuates more with ventilation state
- the rooftop lounge varies more with environmental cycles

Time-of-day effects, small fluctuations, and anomaly scenarios are added on top of those baseline patterns so the outputs are more believable and easier to analyse.

## Wokwi Node

The Wokwi folder contains an ESP32-based node with:

- DHT22
- potentiometer used as an air-quality proxy input
- photoresistor
- vent/window switch
- green, yellow, and red LEDs
- buzzer

The basic split is:

- **Wokwi** shows the embedded sensing side
- **Python** shows the monitoring, logging, analytics, and decision-support side

Included files:

- `wokwi/main.py`
- `wokwi/diagram.json`
- `wokwi/helix_residences_wokwi.zip`

## Output Files

Running the dashboard creates:

- `data/readings.csv`
- `data/readings.json`
- `data/alerts.csv`
- `data/alerts.json`
- chart images in `outputs/charts/`

These are useful as evidence for the report and for screenshots.

## Testing

```bash
python3 -m unittest discover -s tests -v
```

## Notes on Privacy and Scope

The system only monitors communal areas. It does not collect personal resident data, audio, video, or apartment-level tracking data. That matters because the brief highlights privacy and data minimisation in residential environments.

## Limitations

- it is a simulation rather than a live deployment
- the air-quality value is a proxy, not a calibrated sensor measurement
- there is no real HUIL integration
- the Wokwi node represents one example sensing node rather than a full building network

## Future Improvements

- MQTT or REST communication between node and dashboard
- role-based access for staff
- better long-term analytics
- more than one edge node
- stronger production security controls

## Included Submission Files

- source code
- config files
- tests
- Wokwi files
- sample output files
- report draft
- git log export

For final submission, the report should be exported separately as a PDF.
