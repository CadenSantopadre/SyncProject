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

def set_plot(title_text,y_label,y,type):
    ax.clear()
    ax.axhline(0)
    ax.set_title(title_text)
    ax.set_xlabel("Time (S)")
    ax.set_ylabel(y_label)
    if(type=="plot"):
        ax.plot(df["Step"],y)
    if(type=="scatter"):
        ax.scatter(df["Step"],y)
    plt.draw()

def show_beat_step(event): #matplotlib forces an event when we do button stuff
    global plot_is_on #MUST do this to change it. Like doing boolean& in cpp

    if plot_is_on:
        ax.clear()
        ax.set_title("Plot Turned Off")
        plt.draw()
        plot_is_on = False
    else:
        set_plot("Viewing Beat-Step Differences", "Beat-Step Difference (s)", df["Beat-Step"], "scatter")
        plot_is_on = True 


# This creates the button below the graph
ax_beat_btn = plt.axes([0.3, 0.05, 0.18, 0.065])

btn_beat = Button(ax_beat_btn, 'Show Beat-Step', color='lightcoral', hovercolor='red')

btn_beat.on_clicked(show_beat_step)

set_plot("Viewing Beat-Step Differences", "Beat-Step Difference (s)", df["Beat-Step"], "scatter")

plt.show()
