import sys
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (QFileDialog, QApplication, QMainWindow, QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser)
from PyQt6.QtCore import Qt

# Matplotlib PyQt backend imports
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MatplotlibWidget(FigureCanvas): #This is how we set up the graph so it can be used as a widget
    def __init__(self):
        fig = Figure(figsize=(6, 4), dpi=100) #dpi is % of how much it takes up the space
        self.axes = fig.add_subplot(111) #111 means 1 row, 1 column, 1st subplot
        super().__init__(fig) #No clue what this does
        
    def update_graph(self, x, y, title, ylabel, plot_type="plot", color='blue', ylim=None, ref_line=None):
        #when updating we clear the graph first
        self.axes.clear()
        
        #We select if it's scatter or plot based on what it's in the array... dictionary?
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
        self.draw() #Actually draws the thing

    def set_x_limits(self, x_min, x_max):
        self.axes.set_xlim(x_min, x_max)
        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() #Also no clue
        self.setWindowTitle("Data Visualization Dashboard")
        self.setGeometry(0, 0, 1000, 700) #0,0 on the monitor; then it's x,y is 1000,700
        
        #intake the data and then process it
        filename, _ = QFileDialog.getOpenFileName(self,"Select Run File","","CSV Files (*.csv)")

        if filename:
            self.process_data(filename)
        else:
            sys.exit()
        
        # initilize the ui, so this will set up the widget format, 
        self.init_ui()
        
        # 3. Load the initial default plot
        self.set_plot("Beat-Step")
        
        #process_data is all from analysis.py
    def process_data(self, filename):
        
        self.df = pd.read_csv(filename)
        
        self.df["Step_Difference"] = self.df["Step"].diff()
        self.df["Step_Difference"] = self.df["Step_Difference"].fillna(self.df.iloc[0, 0])
        self.df["Rolling_Avg"] = self.df["Step_Difference"].rolling(window=3).mean()
        
        if pd.isna(self.df.loc[0, "Rolling_Avg"]):
            self.df.loc[0, "Rolling_Avg"] = (self.df.loc[0, "Step_Difference"] + self.df.loc[1, "Step_Difference"]) / 2
        if pd.isna(self.df.loc[1, "Rolling_Avg"]):
            self.df.loc[1, "Rolling_Avg"] = (self.df.loc[0, "Step_Difference"] + self.df.loc[1, "Step_Difference"] + self.df.loc[2, "Step_Difference"]) / 3
            
        self.df["Cadence"] = 60 / self.df["Rolling_Avg"]
        self.df["Beat-Step"] = self.df["Beat"] - self.df["Step"]

        steps = self.df["Step"].dropna().sort_values().values
        beats = self.df["Beat"].dropna().sort_values().values
        idx = np.searchsorted(beats, steps)

        idx_before = np.clip(idx - 1, 0, len(beats) - 1)
        idx_after = np.clip(idx, 0, len(beats) - 1)

        beats_before = beats[idx_before]
        beats_after = beats[idx_after]

        denom = beats_after - beats_before
        denom = np.where(denom == 0, np.nan, denom)

        rpa = 360 * (steps - beats_before) / denom
        rpa_norm = ((rpa + 180) % 360) - 180

        phase_mapping_df = pd.DataFrame({
            "Step": steps,
            "Phase_Deg": rpa_norm
        })
        self.df = self.df.merge(phase_mapping_df, on="Step", how="left")

        self.df["Phase_Rad"] = np.deg2rad(self.df["Phase_Deg"])

        self.df["Phase_Vector"] = np.exp(1j * self.df["Phase_Rad"])

        rolling_mean_vector = self.df["Phase_Vector"].rolling(window=3).mean()

        self.df["R"] = np.abs(rolling_mean_vector)

        self.steps_taken = len(self.df)
        self.avg_cadence = int(self.df["Cadence"].mean())
        self.avg_hr = int(self.df["HR"].mean())
        self.avg_rpa = int(self.df["Phase_Deg"].mean())

        self.time_axis = np.arange(len(self.df))

        # Define graph configurations
        self.graphs = {
            "Beat-Step": {
                "title": "Viewing Beat-Step Differences",
                "ylabel": "Beat-Step Difference (s)",
                "y": self.df["Beat-Step"],
                "type": "scatter",
                "color": "purple"
            },
            "Cadence": {
                "title": "Viewing Cadence",
                "ylabel": "Cadence (spm)",
                "y": self.df["Cadence"],
                "type": "plot",
                "color": "teal"
            },
            "Phase": {
                "title": "Relative Phase Angle (0° = Perfect Synchronization)",
                "ylabel": "Phase Angle (Degrees)",
                "y": self.df["Phase_Deg"],
                "type": "scatter",
                "color": "crimson",
                "ylim": (-190, 190),
                "ref_line": 0
            },
            "R": {
                "title": "Phase Locking Value",
                "ylabel": "R",
                "y": self.df["R"],
                "type": "plot",
                "color": "darkgreen"
            }
        }

    def init_ui(self):
        # Main Central Widget is just the whole thing
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        #layout is "QHBox" whatever that means... Horizontal Boxes I guess
        main_layout = QHBoxLayout()
        self.main_widget.setLayout(main_layout)

        # 1. LEFT PANEL: On our left panel, we put in a vertical widget(this is kinda like divving in HTML), so we have lists of buttons
        left_layout = QVBoxLayout()
        
        btn_beat_step = QPushButton("View Beat-Step") #These are all of our button settings, we'll add more
        btn_cadence = QPushButton("View Cadence")
        btn_phase = QPushButton("View Phase")
        btn_R = QPushButton("View R")
        
        #When we click, we need to connect to the SLOT in PyQt,
        btn_beat_step.clicked.connect(lambda: self.set_plot("Beat-Step", )) #Using just self.set_plot(...) leads to python needing the function before it's created...?
                                                                          #So we use lambda as something so we can just do whatever we want
        btn_cadence.clicked.connect(lambda: self.set_plot("Cadence"))
        btn_phase.clicked.connect(lambda: self.set_plot("Phase"))
        btn_R.clicked.connect(lambda: self.set_plot("R"))
        
        left_layout.addWidget(btn_beat_step) #These create hte buttons
        left_layout.addWidget(btn_cadence)
        left_layout.addWidget(btn_phase)
        left_layout.addWidget(btn_R)
        left_layout.addStretch() #addStretch() makes it so everything is at the top, rather than spaced out and centered

        #We do the same thing for Right side, instead making it a big graph with an overview below
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
        
        self.graph_widget = MatplotlibWidget() #This creates our widget as self.graph_widget
        self.overview_widget = QTextBrowser()
        self.overview_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        right_layout.addWidget(self.graph_widget, stretch=6) #Occupies 60%
        right_layout.addLayout(slider_layout, stretch=1) #10%
        right_layout.addWidget(self.overview_widget, stretch=3) #30%


        main_layout.addLayout(left_layout, stretch=1) #Same deal here
        main_layout.addLayout(right_layout, stretch=9)

    def handle_slider_change(self):    
        min_val = self.sld_min.value()
        max_val = self.sld_max.value()
        
        # Guard rail: Stop the minimum slider from crossing past the maximum slider
        if min_val >= max_val:
            min_val = max_val - 1
            self.sld_min.setValue(min_val)
            
        # Dynamically change text readouts above sliders
        self.lbl_min.setText(f"Min: {min_val}s")
        self.lbl_max.setText(f"Max: {max_val}s")
        
        # Apply the new boundaries to the Matplotlib canvas
        self.graph_widget.set_x_limits(min_val, max_val)

    def set_plot(self, graph_key):
        """Your updated plotting method."""
        graph_cfg = self.graphs[graph_key]
        
        # Pass your new self.time_axis array into the update call
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
        
        # Enforce current slider settings onto the newly loaded graph
        self.handle_slider_change()


        #Because we're using textBrowser, we use html to set up everythnig for the overview
        self.overview_widget.setHtml(f"""
            <div style="font-family: sans-serif; font-size: 14px; color: #ffffff;">
                <h3>Run: DATE and TIME</h3>
                <hr>
                <p>Steps Taken: {self.steps_taken}</p>
                <p>Average Cadence: {self.avg_cadence}</p>
                <p>Average Heart Rate: {self.avg_hr}</p>
                <p>Average RPA: {self.avg_rpa}</p>
            </div>
        """)


if __name__ == "__main__": #Every time python runs a file, it makes __name__... sets it to __main__. So if it worked correctly, it runs this stuff
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
