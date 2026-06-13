import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

df = pd.read_csv("Dummy_Sheet.csv")
df["Step_Difference"] = df["Step"].diff()


df["Step_Difference"] = df["Step_Difference"].fillna(df.iloc[0, 0])
df["Rolling_Avg"] = df["Step_Difference"].rolling(window=3).mean()

if pd.isna(df.loc[0, "Rolling_Avg"]):
    df.loc[0, "Rolling_Avg"] = (df.loc[0, "Step_Difference"] + df.loc[1, "Step_Difference"]) / 2
if pd.isna(df.loc[1, "Rolling_Avg"]):
    df.loc[1, "Rolling_Avg"] = (df.loc[0, "Step_Difference"] + df.loc[1, "Step_Difference"] + df.loc[2, "Step_Difference"]) / 3

df["Cadence"] = 60 / df["Rolling_Avg"]

df["Beat-Step"] = df["Beat"] - df["Step"]
print(df)

# Setup of Plot
fig, ax = plt.subplots(figsize=(10, 6))
plt.subplots_adjust(bottom=0.2)  #bottom=0.2 makes room for buttons

plot_is_on = True

graphs = {
    "Beat-Step": {
        "title": "Viewing Beat-Step Differences",
        "ylabel": "Beat-Step Difference (s)",
        "y": df["Beat-Step"],
        "type": "scatter"
    },

    "Cadence": {
        "title": "Viewing Cadence",
        "ylabel": "Cadence (spm)",
        "y": df["Cadence"],
        "type": "plot"
    },
}

def set_plot(graph_name):
    ax.clear()

    graph = graphs[graph_name]

    ax.set_title(graph["title"])
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(graph["ylabel"])

    if graph["type"] == "plot":
        ax.plot(df["Step"], graph["y"])

    elif graph["type"] == "scatter":
        ax.scatter(df["Step"], graph["y"])

    plt.draw()

def show_beat_step(event):
    set_plot("Beat-Step")

def show_cadence(event):
    set_plot("Cadence")

# This creates the button below the graph
ax_beat_btn = plt.axes([0.3, 0.05, 0.18, 0.065])
ax_cadence_btn = plt.axes([0.5, 0.05, 0.18, 0.065])

btn_beat = Button(ax_beat_btn, 'Show Beat-Step', color='lightcoral', hovercolor='red')
btn_cadence = Button(ax_cadence_btn, 'Show Cadence', color='lightgreen', hovercolor='green')



btn_beat.on_clicked(show_beat_step)
btn_cadence.on_clicked(show_cadence)

plt.show()
