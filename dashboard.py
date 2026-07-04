import sys
import os
import itertools
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from PyQt6.QtWidgets import (QFileDialog, QApplication, QMainWindow, QWidget, QLabel, QSlider,
                              QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QDialog,
                              QListWidget, QMessageBox)
from PyQt6.QtCore import Qt

# Matplotlib PyQt backend imports
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D


# ============================================================
# MATPLOTLIB WIDGET
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARTICIPANTS_PATH = os.path.join(BASE_DIR, "participants.csv")
participant_df = pd.read_csv(PARTICIPANTS_PATH)
participant_df["Name"] = participant_df["Name"].astype(str).str.strip()
participant_df["BaselineCadence"] = pd.to_numeric(participant_df["BaselineCadence"], errors="coerce")
baseline_dict = participant_df.set_index("Name")["BaselineCadence"].to_dict()

class MatplotlibWidget(FigureCanvas):  # This is how we set up the graph so it can be used as a widget
    def __init__(self):
        self.fig = Figure(figsize=(6, 4), dpi=100)  # dpi is % of how much it takes up the space
        self.axes = self.fig.add_subplot(111)  # 111 means 1 row, 1 column, 1st subplot
        super().__init__(self.fig)  # No clue what this does

    def update_graph(self, x, y, title, ylabel, plot_type="plot", color='blue', ylim=None, ref_line=None):
        # when updating we clear the graph first
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)

        # We select if it's scatter or plot based on what it's in the array... dictionary?
        if plot_type == "scatter":
            self.axes.scatter(x, y, color=color, alpha=0.7, edgecolors='none')
        else:
            self.axes.plot(x, y, color=color, linestyle='-', linewidth=2)

        if ref_line is not None:
            self.axes.axhline(ref_line, color="gray", linestyle="--", alpha=0.5)
        if ylim is not None:
            self.axes.set_ylim(ylim)

        self.axes.set_title(title)
        self.axes.set_xlabel("Time (s)")
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True)
        self.draw()  # Actually draws the thing

    def set_x_limits(self, x_min, x_max):
        self.axes.set_xlim(x_min, x_max)
        self.draw()

    def update_3d_graph(self, x, y, z, title):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111, projection="3d")

        self.axes.plot(x, y, z)
        self.axes.set_xlabel("Cadence")
        self.axes.set_ylabel("RPA")
        self.axes.set_zlabel("R")

        self.axes.set_title(title)
        self.draw()

    def update_bar_with_error(self, categories, means, stds, title, ylabel, colors=None):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        x = np.arange(len(categories))
        colors = colors or ['steelblue'] * len(categories)
        self.axes.bar(x, means, yerr=stds, capsize=6, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
        self.axes.set_xticks(x)
        self.axes.set_xticklabels(categories)
        self.axes.set_title(title)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, axis='y', alpha=0.3)
        self.draw()

    def update_boxplot(self, data_by_category, labels, title, ylabel):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        self.axes.boxplot(data_by_category, tick_labels=labels)
        self.axes.set_title(title)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, axis='y', alpha=0.3)
        self.draw()

    def update_scatter_groups(self, x_by_cat, y_by_cat, labels, colors, title, xlabel, ylabel):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        for lbl, color in zip(labels, colors):
            self.axes.scatter(x_by_cat[lbl], y_by_cat[lbl], label=lbl, color=color, alpha=0.75, edgecolors='none', s=60)
        self.axes.legend()
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, alpha=0.3)
        self.draw()


# ============================================================
# CORE ANALYSIS (shared by single-run and multi-run modes)
# ============================================================
def process_run(filename):
    run_name = os.path.basename(filename)
    stem = os.path.splitext(run_name)[0]
    participant = stem.split("_")[0].strip()

    baseline = baseline_dict.get(participant, np.nan)
    if pd.isna(baseline):
        warnings.warn(
            f"No baseline cadence found for participant '{participant}' in {PARTICIPANTS_PATH}; using NaN for baseline metrics.",
            UserWarning,
        )

    df = pd.read_csv(filename)

    df["Step_Difference"] = df["Step"].diff()
    df["Step_Difference"] = df["Step_Difference"].fillna(df.iloc[0, 0])
    df["Rolling_Avg"] = df["Step_Difference"].rolling(window=3).mean()

    if pd.isna(df.loc[0, "Rolling_Avg"]):
        df.loc[0, "Rolling_Avg"] = (df.loc[0, "Step_Difference"] + df.loc[1, "Step_Difference"]) / 2
    if pd.isna(df.loc[1, "Rolling_Avg"]):
        df.loc[1, "Rolling_Avg"] = (df.loc[0, "Step_Difference"] + df.loc[1, "Step_Difference"] + df.loc[2, "Step_Difference"]) / 3

    df["Cadence"] = 120 * 1000 / df["Rolling_Avg"]
    df["Delta_Cadence"] = df["Cadence"] - baseline
    df["Beat-Step"] = df["Beat"] - df["Step"]

    steps = df["Step"].dropna().sort_values().values
    beats = df["Beat"].dropna().sort_values().values
    idx = np.searchsorted(beats, steps)

    idx_before = np.clip(idx - 1, 0, len(beats) - 1)
    idx_after = np.clip(idx, 0, len(beats) - 1)

    beats_before = beats[idx_before]
    beats_after = beats[idx_after]

    denom = beats_after - beats_before
    denom = np.where(denom == 0, np.nan, denom)

    rpa = 360 * (steps - beats_before) / denom
    rpa_norm = ((rpa + 180) % 360) - 180

    phase_mapping_df = pd.DataFrame({"Step": steps, "Phase_Deg": rpa_norm})
    df = df.merge(phase_mapping_df, on="Step", how="left")

    df["Phase_Rad"] = np.deg2rad(df["Phase_Deg"])
    df["Phase_Vector"] = np.exp(1j * df["Phase_Rad"])
    rolling_mean_vector = df["Phase_Vector"].rolling(window=3).mean()
    df["R"] = np.abs(rolling_mean_vector)

    avg_cadence = float(df["Cadence"].mean())
    if pd.notna(baseline) and baseline != 0:
        delta_cadence = avg_cadence - baseline
        percent_delta = (delta_cadence / baseline) * 100
    else:
        delta_cadence = np.nan
        percent_delta = np.nan

    return {
        "filename": filename,
        "run_name": os.path.basename(filename),
        "participant": participant,
        "baseline_cadence": baseline,
        "delta_cadence": delta_cadence,
        "percent_delta": percent_delta,
        "df": df,
        "time_axis": np.arange(len(df)),
        "steps_taken": len(df),
        "avg_cadence": avg_cadence,
        "std_cadence": float(df["Cadence"].std()),
        "avg_beat_step": float(df["Beat-Step"].mean()),
        "std_beat_step": float(df["Beat-Step"].std()),
        "avg_phase": float(df["Phase_Deg"].mean()),
        "std_phase": float(df["Phase_Deg"].std()),
        "avg_R": float(df["R"].mean()),
        "std_R": float(df["R"].std()),
    }


def build_graph_configs(df):
    """Builds the per-graph plotting config dict used by RunDetailWindow."""
    return {
        "Beat-Step": {
            "title": "Viewing Beat-Step Differences",
            "ylabel": "Beat-Step Difference (ms)",
            "y": df["Beat-Step"],
            "type": "scatter",
            "color": "purple"
        },
        "Cadence": {
            "title": "Viewing Cadence",
            "ylabel": "Cadence (spm)",
            "y": df["Cadence"],
            "type": "plot",
            "color": "teal"
        },
        "Delta_Cadence": {
            "title": "Viewing Delta Cadence",
            "ylabel": "ΔCadence (spm)",
            "y": df["Delta_Cadence"],
            "type": "plot",
            "color": "orange",
            "ref_line": 0
        },
        "Phase": {
            "title": "Relative Phase Angle (0° = Perfect Synchronization)",
            "ylabel": "Phase Angle (Degrees)",
            "y": df["Phase_Deg"],
            "type": "scatter",
            "color": "crimson",
            "ylim": (-190, 190),
            "ref_line": 0
        },
        "R": {
            "title": "Phase Locking Value",
            "ylabel": "R",
            "y": df["R"],
            "type": "plot",
            "color": "darkgreen"
        }
    }


# ============================================================
# SINGLE-RUN DETAIL VIEW (this is the original MainWindow,
# refactored to accept a pre-loaded run instead of always
# opening its own file dialog, so the multi-run synopsis can
# reuse it for drill-down too)
# ============================================================
class RunDetailWindow(QMainWindow):
    def __init__(self, run_info, title="Data Visualization Dashboard"):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(0, 0, 1000, 700)

        self.df = run_info["df"]
        self.time_axis = run_info["time_axis"]
        self.steps_taken = run_info["steps_taken"]
        self.avg_cadence = run_info["avg_cadence"]
        self.delta_cadence = run_info["delta_cadence"]
        self.avg_rpa = run_info["avg_phase"]
        self.graphs = build_graph_configs(self.df)

        self.init_ui()
        self.set_plot("Beat-Step")

    def init_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        main_layout = QHBoxLayout()
        self.main_widget.setLayout(main_layout)

        left_layout = QVBoxLayout()

        btn_beat_step = QPushButton("View Beat-Step")
        btn_cadence = QPushButton("View Cadence")
        btn_delta_cadence = QPushButton("View Delta Cadence")
        btn_phase = QPushButton("View Phase")
        btn_R = QPushButton("View R")
        btn_state = QPushButton("View State Space")

        btn_beat_step.clicked.connect(lambda: self.set_plot("Beat-Step"))
        btn_cadence.clicked.connect(lambda: self.set_plot("Cadence"))
        btn_delta_cadence.clicked.connect(lambda: self.set_plot("Delta_Cadence"))
        btn_phase.clicked.connect(lambda: self.set_plot("Phase"))
        btn_R.clicked.connect(lambda: self.set_plot("R"))
        btn_state.clicked.connect(lambda: self.set_plot("State Space"))

        left_layout.addWidget(btn_beat_step)
        left_layout.addWidget(btn_cadence)
        left_layout.addWidget(btn_delta_cadence)
        left_layout.addWidget(btn_phase)
        left_layout.addWidget(btn_R)
        left_layout.addWidget(btn_state)
        left_layout.addStretch()

        right_layout = QVBoxLayout()

        slider_layout = QHBoxLayout()

        self.lbl_min = QLabel("Min: 0")
        self.sld_min = QSlider(Qt.Orientation.Horizontal)
        self.sld_min.setRange(0, len(self.time_axis) - 2)
        self.sld_min.setValue(0)

        self.lbl_max = QLabel("Max: Max")
        self.sld_max = QSlider(Qt.Orientation.Horizontal)
        self.sld_max.setRange(1, len(self.time_axis))
        self.sld_max.setValue(len(self.time_axis))

        self.sld_min.valueChanged.connect(self.handle_slider_change)
        self.sld_max.valueChanged.connect(self.handle_slider_change)

        slider_layout.addWidget(self.lbl_min)
        slider_layout.addWidget(self.sld_min)
        slider_layout.addWidget(self.lbl_max)
        slider_layout.addWidget(self.sld_max)

        self.graph_widget = MatplotlibWidget()
        self.overview_widget = QTextBrowser()
        self.overview_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        right_layout.addWidget(self.graph_widget, stretch=6)
        right_layout.addLayout(slider_layout, stretch=1)
        right_layout.addWidget(self.overview_widget, stretch=3)

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=9)

    def handle_slider_change(self):
        min_val = self.sld_min.value()
        max_val = self.sld_max.value()

        if min_val >= max_val:
            min_val = max_val - 1
            self.sld_min.setValue(min_val)

        self.lbl_min.setText(f"Min: {min_val}s")
        self.lbl_max.setText(f"Max: {max_val}s")

        self.graph_widget.set_x_limits(min_val, max_val)

    def set_plot(self, graph_key):
        if graph_key == "State Space":
            self.graph_widget.update_3d_graph(
                self.df["Cadence"],
                self.df["Phase_Deg"],
                self.df["R"],
                "Synchronization State Space"
            )
            self.sld_min.hide()
            self.sld_max.hide()
            self.lbl_min.hide()
            self.lbl_max.hide()
            return

        self.sld_min.show()
        self.sld_max.show()
        self.lbl_min.show()
        self.lbl_max.show()

        graph_cfg = self.graphs[graph_key]

        self.graph_widget.update_graph(
            x=self.time_axis,
            y=graph_cfg["y"],
            title=graph_cfg["title"],
            ylabel=graph_cfg["ylabel"],
            plot_type=graph_cfg["type"],
            color=graph_cfg["color"],
            ylim=graph_cfg.get("ylim", None),
            ref_line=graph_cfg.get("ref_line", None)
        )

        self.handle_slider_change()

        self.overview_widget.setHtml(f"""
            <div style="font-family: sans-serif; font-size: 14px; color: #ffffff;">
                <h3>Run: DATE and TIME</h3>
                <hr>
                <p>Steps Taken: {self.steps_taken}</p>
                <p>Average Cadence: {self.avg_cadence:.1f}</p>
                <p>Delta Cadence: {self.delta_cadence:.1f}</p>
                <p>Average RPA: {self.avg_rpa:.1f}</p>
            </div>
        """)


# ============================================================
# MODE SELECT DIALOG
# ============================================================
class ModeSelectDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Choose Analysis Mode")
        self.mode = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("What would you like to do?"))

        btn_single = QPushButton("Analyze a Single Run")
        btn_multi = QPushButton("Multi-Run Synopsis (Steady / Inter / Anti)")

        btn_single.clicked.connect(self.choose_single)
        btn_multi.clicked.connect(self.choose_multi)

        layout.addWidget(btn_single)
        layout.addWidget(btn_multi)
        self.setLayout(layout)

    def choose_single(self):
        self.mode = "single"
        self.accept()

    def choose_multi(self):
        self.mode = "multi"
        self.accept()

    @staticmethod
    def get_mode():
        dlg = ModeSelectDialog()
        dlg.exec()
        return dlg.mode


# ============================================================
# MULTI-RUN SYNOPSIS
# ============================================================
CONDITIONS = ["Steady", "Inter", "Anti"]
CONDITION_COLORS = {"Steady": "#3B82F6", "Inter": "#F59E0B", "Anti": "#EF4444"}

# (summary_df column, short label, y-axis label)
METRICS = [
    ("Avg_Cadence", "Cadence", "Cadence (spm)"),
    ("Delta_Cadence", "ΔCadence", "ΔCadence (spm)"),
    ("Percent_Delta", "%ΔCadence", "Percent Change (%)"),
    ("Avg_Phase", "Phase", "Phase Angle (deg)"),
    ("Avg_R", "R", "Phase Locking Value (R)"),
    ("Avg_BeatStep", "Beat-Step", "Beat-Step Diff (ms)"),
]


class MultiRunWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Run Synopsis")
        self.setGeometry(0, 0, 1200, 800)
        self.open_windows = []  # keeps drill-down windows alive

        # --- Prompt for files, one category at a time ---
        self.runs = []
        for condition in CONDITIONS:
            files, _ = QFileDialog.getOpenFileNames(
                self, f"Select {condition} Runs", "", "Text Files (*.txt)"
            )
            for f in files:
                try:
                    info = process_run(f)
                except Exception as e:
                    print(f"Skipping {f}: {e}")
                    continue
                info["condition"] = condition
                self.runs.append(info)

        if not self.runs:
            QMessageBox.warning(self, "No Data", "No valid run files were selected.")
            sys.exit()

        missing_baselines = [r["participant"] for r in self.runs if pd.isna(r["baseline_cadence"])]
        if missing_baselines:
            QMessageBox.warning(
                self,
                "Missing Baseline Cadence",
                "Baseline cadence was not found for: " + ", ".join(sorted(set(missing_baselines))) + "\nUsing NaN values for those runs.",
            )

        self.summary_df = pd.DataFrame([
            {
                "Condition": r["condition"],
                "Run": r["run_name"],
                "Participant": r["participant"],
                "Baseline": r["baseline_cadence"],
                "Delta_Cadence": r["delta_cadence"],
                "Percent_Delta": r["percent_delta"],
                "Steps": r["steps_taken"],
                "Avg_Cadence": r["avg_cadence"],
                "Avg_Phase": r["avg_phase"],
                "Avg_R": r["avg_R"],
                "Avg_BeatStep": r["avg_beat_step"],
            }
            for r in self.runs
        ])

        self.init_ui()
        self.show_overview()

    def init_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        main_layout = QHBoxLayout()
        self.main_widget.setLayout(main_layout)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<b>Group Comparisons</b>"))

        btn_overview = QPushButton("Overview")
        btn_overview.clicked.connect(self.show_overview)
        left_layout.addWidget(btn_overview)

        for column, label, ylabel in METRICS:
            btn = QPushButton(f"Compare: {label}")
            btn.clicked.connect(
                lambda checked, col=column, lbl=label, yl=ylabel: self.show_metric_comparison(col, lbl, yl)
            )
            left_layout.addWidget(btn)

        btn_corr = QPushButton("Correlations")
        btn_corr.clicked.connect(self.show_correlations)
        left_layout.addWidget(btn_corr)

        left_layout.addWidget(QLabel("<b>Individual Runs</b> (double-click to open)"))
        self.run_list = QListWidget()
        for r in self.runs:
            self.run_list.addItem(f"[{r['condition']}] {r['run_name']}")
        self.run_list.itemDoubleClicked.connect(self.open_run_detail)
        left_layout.addWidget(self.run_list)
        left_layout.addStretch()

        right_layout = QVBoxLayout()
        self.graph_widget = MatplotlibWidget()
        self.stats_widget = QTextBrowser()
        right_layout.addWidget(self.graph_widget, stretch=6)
        right_layout.addWidget(self.stats_widget, stretch=4)

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=9)

    def open_run_detail(self, item):
        idx = self.run_list.row(item)
        run_info = self.runs[idx]
        detail_window = RunDetailWindow(run_info, title=f"Run Detail - [{run_info['condition']}] {run_info['run_name']}")
        detail_window.show()
        self.open_windows.append(detail_window)

    def show_overview(self):
        rows_html = ""
        for condition in CONDITIONS:
            sub = self.summary_df[self.summary_df["Condition"] == condition]
            if sub.empty:
                rows_html += f"<tr><td>{condition}</td><td colspan='3'>No runs loaded</td></tr>"
                continue
            rows_html += f"""
            <tr>
                <td><b>{condition}</b> (n={len(sub)})</td>
                <td>{sub['Avg_Cadence'].mean():.1f} &plusmn; {sub['Avg_Cadence'].std():.1f}</td>
                <td>{sub['Avg_Phase'].mean():.1f} &plusmn; {sub['Avg_Phase'].std():.1f}</td>
                <td>{sub['Avg_R'].mean():.3f} &plusmn; {sub['Avg_R'].std():.3f}</td>
            </tr>
            """
        html = f"""
        <div style="font-family: sans-serif; font-size: 13px; color: #ffffff;">
            <h3>Multi-Run Synopsis Overview</h3>
            <p>Total runs loaded: {len(self.runs)}</p>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
                <tr><th>Condition</th><th>Cadence (mean &plusmn; sd)</th><th>Phase (mean &plusmn; sd)</th><th>R (mean &plusmn; sd)</th></tr>
                {rows_html}
            </table>
            <p style="margin-top:10px;">Use the buttons on the left for t-tests and correlations on each metric.
            Double-click a run to open its full time series.</p>
        </div>
        """
        self.stats_widget.setHtml(html)
        # default graph: cadence bar chart
        self._draw_metric_bar("Avg_Cadence", "Cadence", "Cadence (spm)")

    def _draw_metric_bar(self, column, label, ylabel):
        categories, means, stds, colors = [], [], [], []
        for condition in CONDITIONS:
            sub = self.summary_df[self.summary_df["Condition"] == condition]
            if sub.empty:
                continue
            vals = pd.Series(sub[column].values).dropna()
            if vals.empty:
                continue
            categories.append(condition)
            means.append(float(vals.mean()))
            stds.append(float(vals.std(ddof=1)) if len(vals) > 1 else 0.0)
            colors.append(CONDITION_COLORS[condition])
        self.graph_widget.update_bar_with_error(categories, means, stds, f"{label} by Condition", ylabel, colors)

    def show_metric_comparison(self, column, label, ylabel):
        groups = {}
        for condition in CONDITIONS:
            sub = self.summary_df[self.summary_df["Condition"] == condition]
            if sub.empty:
                continue
            values = pd.Series(sub[column].values).dropna().to_numpy()
            if values.size:
                groups[condition] = values

        self._draw_metric_bar(column, label, ylabel)

        # descriptive stats
        desc_rows = ""
        for condition, vals in groups.items():
            sd = np.std(vals, ddof=1) if len(vals) > 1 else 0
            desc_rows += f"<tr><td>{condition}</td><td>n={len(vals)}</td><td>{np.mean(vals):.3f}</td><td>{sd:.3f}</td></tr>"

        # pairwise Welch's t-tests
        ttest_rows = ""
        for c1, c2 in itertools.combinations(groups.keys(), 2):
            v1, v2 = groups[c1], groups[c2]
            if len(v1) < 2 or len(v2) < 2:
                ttest_rows += f"<tr><td>{c1} vs {c2}</td><td colspan='2'>Need &ge;2 runs per group</td></tr>"
                continue
            t_stat, p_val = stats.ttest_ind(v1, v2, equal_var=False)
            sig = "significant (p&lt;0.05)" if p_val < 0.05 else "not significant"
            ttest_rows += f"<tr><td>{c1} vs {c2}</td><td>t = {t_stat:.3f}</td><td>p = {p_val:.4f} ({sig})</td></tr>"

        html = f"""
        <div style="font-family: sans-serif; font-size: 13px; color: #ffffff;">
            <h3>{label} — Group Comparison</h3>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
                <tr><th>Condition</th><th>N</th><th>Mean</th><th>SD</th></tr>
                {desc_rows}
            </table>
            <h4 style="margin-top:12px;">Welch's t-tests (unequal variance assumed)</h4>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
                <tr><th>Comparison</th><th>t-statistic</th><th>p-value</th></tr>
                {ttest_rows}
            </table>
        </div>
        """
        self.stats_widget.setHtml(html)

    def show_correlations(self):
        pairs = [
            ("Avg_Cadence", "Avg_R", "Cadence vs R"),
            ("Avg_Cadence", "Avg_Phase", "Cadence vs Phase"),
            ("Avg_Phase", "Avg_R", "Phase vs R"),
        ]
        rows_html = ""
        for col1, col2, label in pairs:
            x = pd.Series(self.summary_df[col1].values).dropna().to_numpy()
            y = pd.Series(self.summary_df[col2].values).dropna().to_numpy()
            if len(x) < 3 or len(y) < 3 or len(x) != len(y):
                rows_html += f"<tr><td>{label}</td><td colspan='2'>Need &ge;3 paired runs</td></tr>"
                continue
            r_val, p_val = stats.pearsonr(x, y)
            rows_html += f"<tr><td>{label}</td><td>r = {r_val:.3f}</td><td>p = {p_val:.4f}</td></tr>"

        html = f"""
        <div style="font-family: sans-serif; font-size: 13px; color: #ffffff;">
            <h3>Cross-Metric Correlations (all runs pooled)</h3>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
                <tr><th>Pair</th><th>Pearson r</th><th>p-value</th></tr>
                {rows_html}
            </table>
            <p style="margin-top:10px;">Graph shows Cadence vs R, colored by condition.</p>
        </div>
        """
        self.stats_widget.setHtml(html)

        x_by_cat, y_by_cat = {}, {}
        for condition in CONDITIONS:
            sub = self.summary_df[self.summary_df["Condition"] == condition]
            if sub.empty:
                continue
            x_vals = pd.Series(sub["Avg_Cadence"].values).dropna().to_numpy()
            y_vals = pd.Series(sub["Avg_R"].values).dropna().to_numpy()
            if x_vals.size and y_vals.size:
                x_by_cat[condition] = x_vals
                y_by_cat[condition] = y_vals
        labels = list(x_by_cat.keys())
        colors = [CONDITION_COLORS[l] for l in labels]
        self.graph_widget.update_scatter_groups(
            x_by_cat, y_by_cat, labels, colors, "Cadence vs R by Condition", "Cadence (spm)", "R"
        )


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    mode = ModeSelectDialog.get_mode()

    if mode == "single":
        filename, _ = QFileDialog.getOpenFileName(None, "Select Run File", "", "Text Files (*.txt)")
        if not filename:
            sys.exit()
        run_info = process_run(filename)
        if pd.isna(run_info["baseline_cadence"]):
            QMessageBox.warning(None, "Missing Baseline Cadence", "Baseline cadence was not found for this participant. Using NaN values.")
        window = RunDetailWindow(run_info, title="Data Visualization Dashboard")
        window.show()
    elif mode == "multi":
        window = MultiRunWindow()
        window.show()
    else:
        sys.exit()

    sys.exit(app.exec())