# Wokwi Node Summary

This folder contains the embedded sensing node for the Helix Residences project.

## Purpose

The Wokwi circuit represents a single communal-area sensing node that would be deployed in a shared building zone. It complements the Python dashboard:

- `Wokwi`: embedded sensing, local threshold classification, actuator response
- `Python dashboard`: building-wide monitoring, analytics, logging, and decision support

## Components

- `ESP32 DevKit V1`
- `DHT22` for temperature and humidity
- `Potentiometer` used as a controllable gas / CO2-VOC proxy input
- `Photoresistor sensor` for light level
- `Slide switch` for vent or window state
- `Green LED` for Safe
- `Yellow LED` for Warning
- `Red LED` for Danger
- `Buzzer` for danger-state audible alert

## Logic

The thresholds intentionally mirror the Python artefact:

- temperature: safe `19–24°C`, warning `17–27°C`
- humidity: safe `35–60%`, warning `30–70%`
- air quality proxy: safe `<=800`, warning `<=1200`
- light level proxy: safe `>=250`, warning `>=150`

The node prints JSON-style serial output so it can be explained as an edge device that would forward readings to the wider monitoring platform in a real deployment.
