from __future__ import annotations

from collections import defaultdict, deque
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Deque, Dict, List

MPL_CONFIG_DIR = Path(__file__).resolve().parents[1] / ".matplotlib"
MPL_CONFIG_DIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .alerts import AlertManager
from .analytics import AnalyticsEngine
from .config_loader import BASE_DIR, load_simulation_config, load_thresholds, load_zone_configs
from .logger_manager import DataLogger
from .models import STATUS_DANGER, STATUS_SAFE, AlertEvent, SensorReading, ZoneAssessment
from .rules import RuleEngine
from .simulator import EnvironmentalSimulator


class HelixDashboard:
    """Tkinter desktop application for communal-area IoT monitoring."""

    METRIC_LABELS = {
        "temperature": "Temperature (°C)",
        "humidity": "Humidity (%)",
        "air_quality": "Air Quality Proxy",
        "light_level": "Light Level (lux proxy)",
    }

    STATUS_COLOURS = {
        "Safe": "#2f7d4a",
        "Warning": "#c48717",
        "Danger": "#b23a2b",
        "Idle": "#52606d",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Helix Residences Environmental Comfort Dashboard")
        self.root.geometry("1450x900")
        self.root.minsize(1200, 780)
        self.root.configure(bg="#f5f1ea")

        simulation_config = load_simulation_config()
        self.zone_configs = load_zone_configs()
        self.thresholds = load_thresholds()
        self.simulator = EnvironmentalSimulator(
            self.zone_configs,
            seed=simulation_config["seed"],
            step_minutes=simulation_config["step_minutes"],
        )
        self.rule_engine = RuleEngine(self.thresholds)
        self.alert_manager = AlertManager(self.thresholds["repeated_warning_count"])
        self.logger = DataLogger(BASE_DIR)
        self.analytics = AnalyticsEngine(BASE_DIR)

        self.history_limit = 72
        self.reading_history: Dict[str, Deque[SensorReading]] = defaultdict(lambda: deque(maxlen=self.history_limit))
        self.assessment_history: Dict[str, Deque[ZoneAssessment]] = defaultdict(lambda: deque(maxlen=self.history_limit))
        self.zone_rows: Dict[str, Dict[str, str]] = {}
        self.running = False
        self.loop_job: str | None = None
        self.speed_multiplier = tk.DoubleVar(value=simulation_config["default_speed_multiplier"])
        self.selected_zone = tk.StringVar(value=self.zone_configs[0].name)
        self.selected_metric = tk.StringVar(value="temperature")
        self.scenario_var = tk.StringVar(value="normal")

        self.summary_var = tk.StringVar(value="Simulation ready. No live data yet.")
        self.zone_detail_var = tk.StringVar(value="Select a zone and start the simulation.")
        self.recommendation_var = tk.StringVar(value="Recommendations will appear when data is available.")
        self.status_var = tk.StringVar(value="Paused")
        self.overall_status_var = tk.StringVar(value="Idle")
        self.alert_count_var = tk.StringVar(value="0")
        self.worst_zone_var = tk.StringVar(value="No issues yet")
        self.scenario_status_var = tk.StringVar(value="Normal operation")
        self.metric_card_vars = {
            "Temperature": tk.StringVar(value="-- °C"),
            "Humidity": tk.StringVar(value="-- %"),
            "Air Quality": tk.StringVar(value="-- ppm proxy"),
            "Vent State": tk.StringVar(value="--"),
        }
        self.status_badge_var = tk.StringVar(value="PAUSED")
        self.summary_card_value_labels: Dict[str, tk.Label] = {}

        self._build_layout()
        self._initialise_table()
        self._refresh_chart()

    def _build_layout(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#f5f1ea", foreground="#21313c")
        style.configure("Treeview", rowheight=30, font=("Helvetica", 10), background="#fffdf9", fieldbackground="#fffdf9")
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#dbe7e4", foreground="#1e3642")
        style.configure("Header.TLabel", background="#f5f1ea", foreground="#123142", font=("Helvetica", 24, "bold"))
        style.configure("SubHeader.TLabel", background="#f5f1ea", foreground="#5d6c77", font=("Helvetica", 10))
        style.configure("Panel.TLabelframe", background="#fffdf9", borderwidth=0)
        style.configure("Panel.TLabelframe.Label", background="#fffdf9", foreground="#173648", font=("Helvetica", 11, "bold"))
        style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#144a52"), ("!disabled", "#1b676f")], foreground=[("!disabled", "white")])
        style.map("TButton", background=[("active", "#e2ebe8")])

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=5)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(2, weight=3)
        main.rowconfigure(3, weight=2)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="The Helix Residences | Environmental Comfort & Air Quality", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.summary_var, style="SubHeader.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.status_badge_label = tk.Label(
            header,
            textvariable=self.status_badge_var,
            bg="#1e3642",
            fg="white",
            padx=14,
            pady=8,
            font=("Helvetica", 10, "bold"),
        )
        self.status_badge_label.grid(row=0, column=1, rowspan=2, sticky="e")

        cards = ttk.Frame(main)
        cards.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for index in range(4):
            cards.columnconfigure(index, weight=1)

        self._create_summary_card(cards, 0, "Overall Status", self.overall_status_var, "#f3faf5")
        self._create_summary_card(cards, 1, "Active Alerts", self.alert_count_var, "#fff8eb")
        self._create_summary_card(cards, 2, "Worst Zone", self.worst_zone_var, "#eef6f8")
        self._create_summary_card(cards, 3, "Selected Scenario", self.scenario_status_var, "#fbf1ef")

        left_top = ttk.Frame(main)
        left_top.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        left_top.rowconfigure(1, weight=1)
        left_top.columnconfigure(0, weight=1)

        controls = ttk.LabelFrame(left_top, text="Simulation Controls", padding=12, style="Panel.TLabelframe")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for index in range(8):
            controls.columnconfigure(index, weight=1)

        ttk.Button(controls, text="Start Simulation", command=self.start, style="Accent.TButton").grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(controls, text="Pause", command=self.pause).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(controls, text="Reset", command=self.reset).grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        ttk.Label(controls, text="Zone").grid(row=0, column=3, padx=(12, 4), sticky="e")
        zone_menu = ttk.Combobox(controls, textvariable=self.selected_zone, values=[zone.name for zone in self.zone_configs], state="readonly", width=18)
        zone_menu.grid(row=0, column=4, padx=4, sticky="ew")
        zone_menu.bind("<<ComboboxSelected>>", lambda _event: self._refresh_zone_focus())

        ttk.Label(controls, text="Metric").grid(row=0, column=5, padx=(12, 4), sticky="e")
        metric_menu = ttk.Combobox(
            controls,
            textvariable=self.selected_metric,
            values=["temperature", "humidity", "air_quality", "light_level"],
            state="readonly",
            width=16,
        )
        metric_menu.grid(row=0, column=6, padx=4, sticky="ew")
        metric_menu.bind("<<ComboboxSelected>>", lambda _event: self._refresh_chart())

        speed = ttk.Scale(controls, from_=0.5, to=4.0, variable=self.speed_multiplier, orient=tk.HORIZONTAL)
        speed.grid(row=1, column=0, columnspan=3, padx=4, pady=8, sticky="ew")
        ttk.Label(controls, text="Simulation speed").grid(row=1, column=3, sticky="e")
        ttk.Label(controls, text="0.5x to 4.0x").grid(row=1, column=4, sticky="w")

        ttk.Label(controls, text="Scenario").grid(row=1, column=5, padx=(12, 4), sticky="e")
        scenario_menu = ttk.Combobox(
            controls,
            textvariable=self.scenario_var,
            values=["normal", "ventilation_failure", "overheating", "poor_air_quality", "sensor_fault", "stuck_vent"],
            state="readonly",
            width=18,
        )
        scenario_menu.grid(row=1, column=6, padx=4, sticky="ew")
        ttk.Button(controls, text="Apply Scenario", command=self.apply_scenario).grid(row=1, column=7, padx=4, sticky="ew")

        live_frame = ttk.LabelFrame(left_top, text="Live Monitoring Dashboard", padding=12, style="Panel.TLabelframe")
        live_frame.grid(row=1, column=0, sticky="nsew")
        live_frame.rowconfigure(0, weight=1)
        live_frame.columnconfigure(0, weight=1)

        columns = ("zone", "timestamp", "temperature", "humidity", "air_quality", "light_level", "vent_state", "status")
        self.tree = ttk.Treeview(live_frame, columns=columns, show="headings")
        headers = {
            "zone": "Zone",
            "timestamp": "Timestamp",
            "temperature": "Temp (°C)",
            "humidity": "Humidity (%)",
            "air_quality": "Air Proxy",
            "light_level": "Light",
            "vent_state": "Vent",
            "status": "Status",
        }
        for column, heading in headers.items():
            self.tree.heading(column, text=heading)
            self.tree.column(column, anchor=tk.CENTER, width=110 if column != "timestamp" else 150)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(live_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        ttk.Label(
            live_frame,
            text="Air proxy values represent a simulated indoor CO2/VOC concentration index in ppm-style units.",
            style="SubHeader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        right = ttk.Frame(main)
        right.grid(row=2, column=1, rowspan=2, sticky="nsew")
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        selected_cards = ttk.LabelFrame(right, text="Selected Zone Snapshot", padding=12, style="Panel.TLabelframe")
        selected_cards.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for index in range(2):
            selected_cards.columnconfigure(index, weight=1)
        self._create_metric_card(selected_cards, 0, 0, "Temperature", self.metric_card_vars["Temperature"])
        self._create_metric_card(selected_cards, 0, 1, "Humidity", self.metric_card_vars["Humidity"])
        self._create_metric_card(selected_cards, 1, 0, "Air Quality", self.metric_card_vars["Air Quality"])
        self._create_metric_card(selected_cards, 1, 1, "Vent State", self.metric_card_vars["Vent State"])

        detail = ttk.LabelFrame(right, text="Selected Zone Overview", padding=12, style="Panel.TLabelframe")
        detail.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.zone_detail_message = tk.Message(
            detail,
            textvariable=self.zone_detail_var,
            width=390,
            justify=tk.LEFT,
            bg="#fffdf9",
            fg="#21313c",
            font=("Helvetica", 10),
        )
        self.zone_detail_message.pack(fill=tk.X)

        recommendations = ttk.LabelFrame(right, text="Operational Recommendations", padding=12, style="Panel.TLabelframe")
        recommendations.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        recommendation_label = tk.Message(
            recommendations,
            textvariable=self.recommendation_var,
            width=390,
            justify=tk.LEFT,
            bg="#fffdf9",
            fg="#20313b",
            font=("Helvetica", 10),
        )
        recommendation_label.pack(fill=tk.X)

        alerts_frame = ttk.LabelFrame(right, text="Recent Alerts", padding=12, style="Panel.TLabelframe")
        alerts_frame.grid(row=3, column=0, sticky="nsew")
        alerts_frame.rowconfigure(0, weight=1)
        alerts_frame.columnconfigure(0, weight=1)
        self.alerts_list = tk.Listbox(
            alerts_frame,
            height=14,
            font=("Helvetica", 10),
            activestyle="none",
            bg="#fffdf9",
            fg="#21313c",
            relief=tk.FLAT,
            highlightthickness=0,
            selectbackground="#dceee7",
            selectforeground="#123142",
        )
        self.alerts_list.grid(row=0, column=0, sticky="nsew")

        bottom = ttk.LabelFrame(main, text="Historical Trends & Analytics", padding=12, style="Panel.TLabelframe")
        bottom.grid(row=3, column=0, sticky="nsew", padx=(0, 8))
        bottom.rowconfigure(0, weight=1)
        bottom.columnconfigure(0, weight=2)
        bottom.columnconfigure(1, weight=1)

        self.figure = Figure(figsize=(7.6, 3.8), dpi=100, facecolor="#fffdf9")
        self.axis = self.figure.add_subplot(111)
        self.axis.set_facecolor("#fffdf9")
        self.canvas = FigureCanvasTkAgg(self.figure, master=bottom)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        analytics_frame = ttk.Frame(bottom)
        analytics_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        analytics_frame.columnconfigure(0, weight=1)

        self.analytics_text = tk.Text(
            analytics_frame,
            height=15,
            wrap=tk.WORD,
            font=("Helvetica", 10),
            bg="#fffdf9",
            fg="#21313c",
            relief=tk.FLAT,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.analytics_text.grid(row=0, column=0, sticky="nsew")
        ttk.Button(analytics_frame, text="Export Current Chart", command=self.export_chart, style="Accent.TButton").grid(row=1, column=0, pady=(8, 0), sticky="ew")

    def _create_summary_card(self, parent: ttk.Frame, column: int, title: str, value_var: tk.StringVar, background: str) -> None:
        card = tk.Frame(parent, bg=background, padx=16, pady=14, highlightbackground="#e1ddd5", highlightthickness=1)
        card.grid(row=0, column=column, padx=6, sticky="ew")
        tk.Label(card, text=title.upper(), bg=background, fg="#5c6b75", font=("Helvetica", 9, "bold")).pack(anchor="w")
        value_label = tk.Label(card, textvariable=value_var, bg=background, fg="#173648", font=("Helvetica", 16, "bold"))
        value_label.pack(anchor="w", pady=(8, 0))
        self.summary_card_value_labels[title] = value_label

    def _create_metric_card(self, parent: ttk.LabelFrame, row: int, column: int, title: str, value_var: tk.StringVar) -> None:
        card = tk.Frame(parent, bg="#f7f5f0", padx=12, pady=10, highlightbackground="#e3dfd8", highlightthickness=1)
        card.grid(row=row, column=column, padx=6, pady=6, sticky="ew")
        tk.Label(card, text=title, bg="#f7f5f0", fg="#66727d", font=("Helvetica", 9, "bold")).pack(anchor="w")
        tk.Label(card, textvariable=value_var, bg="#f7f5f0", fg="#123142", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(8, 0))

    def _initialise_table(self) -> None:
        for zone in self.zone_configs:
            item_id = self.tree.insert("", tk.END, values=(zone.name, "-", "-", "-", "-", "-", "-", "Idle"))
            self.zone_rows[zone.name] = {"item_id": item_id}

    def _next_interval_ms(self) -> int:
        base_ms = 1200
        return max(250, int(base_ms / max(self.speed_multiplier.get(), 0.5)))

    def start(self) -> None:
        if not self.running:
            self.running = True
            self.status_var.set("Running")
            self.status_badge_var.set("RUNNING")
            self._tick()

    def pause(self) -> None:
        self.running = False
        self.status_var.set("Paused")
        self.status_badge_var.set("PAUSED")
        if self.loop_job:
            self.root.after_cancel(self.loop_job)
            self.loop_job = None

    def reset(self) -> None:
        self.pause()
        self.simulator.reset()
        self.alert_manager = AlertManager(self.thresholds["repeated_warning_count"])
        self.logger.reset_logs()
        self.reading_history.clear()
        self.assessment_history.clear()
        self.alerts_list.delete(0, tk.END)
        self.summary_var.set("Simulation reset. Logs cleared and deterministic seed restored.")
        self.overall_status_var.set("Idle")
        self.alert_count_var.set("0")
        self.worst_zone_var.set("No issues yet")
        self.scenario_status_var.set("Normal operation")
        self.zone_detail_var.set("Select a zone and start the simulation.")
        self.recommendation_var.set("Recommendations will appear when data is available.")
        self.analytics_text.delete("1.0", tk.END)
        for value in self.metric_card_vars.values():
            value.set("--")
        self.metric_card_vars["Temperature"].set("-- °C")
        self.metric_card_vars["Humidity"].set("-- %")
        self.metric_card_vars["Air Quality"].set("-- ppm proxy")
        for zone_name, row in self.zone_rows.items():
            self.tree.item(row["item_id"], values=(zone_name, "-", "-", "-", "-", "-", "-", "Idle"), tags=())
        self._update_status_colours("Idle")
        self._refresh_chart()

    def apply_scenario(self) -> None:
        zone = self.selected_zone.get()
        scenario = self.scenario_var.get()
        self.simulator.set_scenario(zone, None if scenario == "normal" else scenario)
        self.scenario_status_var.set(f"{zone}: {scenario.replace('_', ' ').title()}")
        messagebox.showinfo("Scenario Applied", f"{zone} scenario set to: {scenario.replace('_', ' ')}")

    def _tick(self) -> None:
        readings = self.simulator.step()
        all_assessments: List[ZoneAssessment] = []
        all_alerts: List[AlertEvent] = []

        for reading in readings:
            assessment = self.rule_engine.assess(reading)
            base_alerts = self.rule_engine.build_alerts(reading, assessment)
            alerts = self.alert_manager.process_assessment(assessment, base_alerts, reading.scenario)

            self.reading_history[reading.zone].append(reading)
            self.assessment_history[reading.zone].append(assessment)
            self.logger.log_reading(reading)
            self.logger.log_alerts(alerts)

            self._update_table_row(reading, assessment)
            all_assessments.append(assessment)
            all_alerts.extend(alerts)

        self._update_summary(all_assessments)
        self._refresh_alerts()
        self._refresh_zone_focus()

        if self.running:
            self.loop_job = self.root.after(self._next_interval_ms(), self._tick)

    def _update_table_row(self, reading: SensorReading, assessment: ZoneAssessment) -> None:
        row = self.zone_rows[reading.zone]
        values = (
            reading.zone,
            reading.timestamp.strftime("%H:%M:%S"),
            f"{reading.temperature:.1f}",
            f"{reading.humidity:.1f}",
            f"{reading.air_quality:.0f}",
            f"{reading.light_level:.0f}",
            reading.vent_state,
            assessment.status,
        )
        tags = (assessment.status.lower(),)
        self.tree.item(row["item_id"], values=values, tags=tags)
        self.tree.tag_configure("safe", background="#e8f5e9")
        self.tree.tag_configure("warning", background="#fff8e1")
        self.tree.tag_configure("danger", background="#ffebee")

    def _update_summary(self, assessments: List[ZoneAssessment]) -> None:
        danger_count = sum(assessment.status == STATUS_DANGER for assessment in assessments)
        warning_count = sum(assessment.status == "Warning" for assessment in assessments)
        overall = "Danger" if danger_count else "Warning" if warning_count else STATUS_SAFE

        flat_assessments = [item for zone_items in self.assessment_history.values() for item in zone_items]
        worst_zone = self.analytics.worst_performing_zone(flat_assessments)
        frequent_alert = self.analytics.most_frequent_alert_type(self.alert_manager.alert_history)
        self.overall_status_var.set(overall)
        self.alert_count_var.set(str(sum(assessment.status != STATUS_SAFE for assessment in assessments)))
        self.worst_zone_var.set(worst_zone)
        self._update_status_colours(overall)
        self.summary_var.set(
            f"Overall building status: {overall} | Danger zones: {danger_count} | Warning zones: {warning_count} | Worst-performing zone: {worst_zone} | Most frequent alert: {frequent_alert}"
        )

    def _refresh_alerts(self) -> None:
        self.alerts_list.delete(0, tk.END)
        for alert in reversed(self.alert_manager.recent_alerts(12)):
            entry = f"[{alert.timestamp.strftime('%H:%M')}] {alert.severity} | {alert.zone} | {alert.message}"
            self.alerts_list.insert(tk.END, entry)
            index = self.alerts_list.size() - 1
            fg = self.STATUS_COLOURS.get(alert.severity, "#21313c")
            self.alerts_list.itemconfig(index, fg=fg)

    def _refresh_zone_focus(self) -> None:
        zone = self.selected_zone.get()
        readings = list(self.reading_history.get(zone, []))
        assessments = list(self.assessment_history.get(zone, []))
        if not readings or not assessments:
            self.zone_detail_var.set(f"{zone}: waiting for live readings.")
            self.recommendation_var.set("Recommendations will appear when the selected zone has enough data.")
            self._refresh_chart()
            return

        latest_reading = readings[-1]
        latest_assessment = assessments[-1]
        trend = "rising" if len(readings) > 1 and readings[-1].air_quality > readings[-2].air_quality else "stable/falling"
        self.metric_card_vars["Temperature"].set(f"{latest_reading.temperature:.1f} °C")
        self.metric_card_vars["Humidity"].set(f"{latest_reading.humidity:.1f} %")
        self.metric_card_vars["Air Quality"].set(f"{latest_reading.air_quality:.0f} ppm proxy")
        self.metric_card_vars["Vent State"].set(latest_reading.vent_state)
        self.zone_detail_var.set(
            f"{zone} at {latest_reading.timestamp.strftime('%H:%M:%S')}: status {latest_assessment.status}. "
            f"Temperature {latest_reading.temperature:.1f}°C, humidity {latest_reading.humidity:.1f}%, air proxy {latest_reading.air_quality:.0f} ppm-style units, "
            f"light {latest_reading.light_level:.0f} lux proxy, vent {latest_reading.vent_state}. Air quality trend is {trend}."
        )
        self.recommendation_var.set(latest_assessment.recommendation)
        self._refresh_chart()
        self._refresh_analytics_panel()

    def _refresh_chart(self) -> None:
        zone = self.selected_zone.get()
        metric = self.selected_metric.get()
        readings = list(self.reading_history.get(zone, []))

        self.axis.clear()
        self.axis.set_facecolor("#fffdf9")
        metric_label = self.METRIC_LABELS.get(metric, metric.replace("_", " ").title())
        self.axis.set_title(f"{zone} {metric_label} Trend")
        self.axis.set_xlabel("Time")
        self.axis.set_ylabel(metric_label)
        self.axis.grid(alpha=0.25, color="#cfd8dc")

        if readings:
            timestamps = [reading.timestamp.strftime("%H:%M") for reading in readings]
            values = [getattr(reading, metric) for reading in readings]
            smoothed = self.analytics.rolling_average(readings, metric)
            self.axis.plot(timestamps, values, color="#1f6f78", linewidth=2.2, label="Reading")
            self.axis.plot(timestamps, smoothed, color="#d98b3a", linestyle="--", linewidth=2, label="Rolling average")
            self.axis.legend()
            for label in self.axis.get_xticklabels():
                label.set_rotation(45)
        else:
            self.axis.text(0.5, 0.5, "No data yet", ha="center", va="center", color="#76848e")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _refresh_analytics_panel(self) -> None:
        zone = self.selected_zone.get()
        assessments = list(self.assessment_history.get(zone, []))
        if not assessments:
            return

        breaches = sum(assessment.status != STATUS_SAFE for assessment in assessments)
        danger_count = sum(assessment.status == STATUS_DANGER for assessment in assessments)
        readings = list(self.reading_history.get(zone, []))
        avg_temp = sum(reading.temperature for reading in readings) / len(readings)
        avg_air = sum(reading.air_quality for reading in readings) / len(readings)
        alert_count = sum(alert.zone == zone for alert in self.alert_manager.alert_history)

        self.analytics_text.delete("1.0", tk.END)
        self.analytics_text.insert(
            tk.END,
            (
                f"Zone analytics: {zone}\n\n"
                f"Samples collected: {len(readings)}\n"
                f"Threshold breaches: {breaches}\n"
                f"Danger states: {danger_count}\n"
                f"Average temperature: {avg_temp:.2f} °C\n"
                f"Average air proxy: {avg_air:.2f} ppm-style units\n"
                f"Alerts raised: {alert_count}\n"
                f"Current recommendation: {assessments[-1].recommendation}\n"
            ),
        )

    def _update_status_colours(self, overall_status: str) -> None:
        status_colour = self.STATUS_COLOURS.get(overall_status, "#173648")
        overall_label = self.summary_card_value_labels.get("Overall Status")
        if overall_label:
            overall_label.configure(fg=status_colour)
        alerts_label = self.summary_card_value_labels.get("Active Alerts")
        if alerts_label:
            alerts_label.configure(fg=self.STATUS_COLOURS["Warning"] if self.alert_count_var.get() != "0" else "#173648")
        badge_colour = "#1e3642" if self.status_var.get() == "Paused" else status_colour
        self.status_badge_var.set(self.status_var.get().upper())
        self.status_badge_label.configure(bg=badge_colour)

    def export_chart(self) -> None:
        zone = self.selected_zone.get()
        metric = self.selected_metric.get()
        readings = list(self.reading_history.get(zone, []))
        if not readings:
            messagebox.showwarning("Export unavailable", "No readings available for the selected zone.")
            return
        path = self.analytics.export_zone_chart(zone, readings, metric)
        messagebox.showinfo("Chart exported", f"Saved chart to:\n{path}")

    def on_close(self) -> None:
        self.pause()
        self.root.destroy()


def launch_dashboard() -> None:
    root = tk.Tk()
    app = HelixDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
