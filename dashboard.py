import sys
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel)
from PyQt6.QtCore import Qt

# Matplotlib PyQt backend imports
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MatplotlibWidget(FigureCanvas): #This is how we set up the graph so it can be used as a widget
    def __init__(self):
        fig = Figure(figsize=(6, 4), dpi=100) #dpi is % of how much it takes up the space
        self.axes = fig.add_subplot(111) #111 means 1 row, 1 column, 1st subplot
        super().__init__(fig) #No clue what this does
        
    def update_graph(self, x, y, title, ylabel, plot_type="plot"):
        #when updating we clear the graph first
        self.axes.clear()
        
        #We select if it's scatter or plot based on what it's in the array... dictionary?
        if plot_type == "scatter":
            self.axes.scatter(x, y, color='purple', alpha=0.7, edgecolors='none')
        else:
            self.axes.plot(x, y, color='blue', linestyle='-', linewidth=2)
            
        self.axes.set_title(title)
        self.axes.set_xlabel("Time (s)")
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True)
        self.draw() #Actually draws the thing

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() #Also no clue
        self.setWindowTitle("Data Visualization Dashboard")
        self.setGeometry(0, 0, 1000, 700) #0,0 on the monitor; then it's x,y is 1000,700
        
        #intake the data and then process it
        self.process_data()
        
        # initilize the ui, so this will set up the widget format, 
        self.init_ui()
        
        # 3. Load the initial default plot
        self.set_plot("Beat-Step")
        
    def process_data(self):
        
        self.df = pd.read_csv("Dummy_Sheet.csv")
        
        self.df["Step_Difference"] = self.df["Step"].diff()
        self.df["Step_Difference"] = self.df["Step_Difference"].fillna(self.df.iloc[0, 0])
        self.df["Rolling_Avg"] = self.df["Step_Difference"].rolling(window=3).mean()
        
        if pd.isna(self.df.loc[0, "Rolling_Avg"]):
            self.df.loc[0, "Rolling_Avg"] = (self.df.loc[0, "Step_Difference"] + self.df.loc[1, "Step_Difference"]) / 2
        if pd.isna(self.df.loc[1, "Rolling_Avg"]):
            self.df.loc[1, "Rolling_Avg"] = (self.df.loc[0, "Step_Difference"] + self.df.loc[1, "Step_Difference"] + self.df.loc[2, "Step_Difference"]) / 3
            
        self.df["Cadence"] = 60 / self.df["Rolling_Avg"]
        self.df["Beat-Step"] = self.df["Beat"] - self.df["Step"]
        
        # Define graph configurations
        self.graphs = {
            "Beat-Step": {
                "title": "Viewing Beat-Step Differences",
                "ylabel": "Beat-Step Difference (s)",
                "y": self.df["Beat-Step"],
                "type": "scatter"
            },
            "Cadence": {
                "title": "Viewing Cadence",
                "ylabel": "Cadence (spm)",
                "y": self.df["Cadence"],
                "type": "plot"
            },
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
        #TODO: add these buttons, also you need a type configuration in teh dictionary to switch from 3d and stuff
        #btn_RPA3 = QPushButton("View RPA (3D)")
        #btn_RPAm = QPushButton("View RPA (Mod)")
        
        #When we click, we need to connect to the SLOT in PyQt,
        btn_beat_step.clicked.connect(lambda: self.set_plot("Beat-Step")) #Using just self.set_plot(...) leads to python needing the function before it's created...?
                                                                          #So we use lambda as something so we can just do whatever we want
        btn_cadence.clicked.connect(lambda: self.set_plot("Cadence"))
        
        left_layout.addWidget(btn_beat_step) #These create hte buttons
        left_layout.addWidget(btn_cadence)
        left_layout.addStretch() #addStretch() makes it so everything is at the top, rather than spaced out and centered

        #We do the same thing for Right side, instead making it a big graph with an overview below
        right_layout = QVBoxLayout()
        
        self.graph_widget = MatplotlibWidget() #This creates our widget as self.graph_widget
        self.overview_widget = QLabel() #This is empty right now, we need to put something in it... we use label to use markdown
        
        right_layout.addWidget(self.graph_widget, stretch=7) #Occupies 70%
        right_layout.addWidget(self.overview_widget, stretch=3) #30%


        main_layout.addLayout(left_layout, stretch=1) #Same deal here
        main_layout.addLayout(right_layout, stretch=9)

    def set_plot(self, graph_key):
        #We need a key(like an address in Cpp?) because this is object-oriented
        #we need the graph_key because we are looking in our dictionary of graphs(scatter, plot, etc)

        self.graph_widget.update_graph(
            x=self.df.index,
            y=self.graphs[graph_key]["y"],
            title=self.graphs[graph_key]["title"],
            ylabel=self.graphs[graph_key]["ylabel"],
            plot_type=self.graphs[graph_key]["type"]
        )


if __name__ == "__main__": #Every time python runs a file, it makes __name__... sets it to __main__. So if it worked correctly, it runs this stuff
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
