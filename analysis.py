import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

# 1. Load and Process Data First
df = pd.read_csv("Dummy_Sheet.csv")
df["Step_Difference"] = df["Step"].diff()

# Fill in the NaN with the first step time
df["Step_Difference"] = df["Step_Difference"].fillna(df.iloc[0, 0])
df["Rolling_Avg"] = df["Step_Difference"].rolling(window=3).mean()

# Safely handle the initial rolling average NaN values using column names
if pd.isna(df.loc[0, "Rolling_Avg"]):
    df.loc[0, "Rolling_Avg"] = (df.loc[0, "Step_Difference"] + df.loc[1, "Step_Difference"]) / 2
if pd.isna(df.loc[1, "Rolling_Avg"]):
    df.loc[1, "Rolling_Avg"] = (df.loc[0, "Step_Difference"] + df.loc[1, "Step_Difference"] + df.loc[2, "Step_Difference"]) / 3

df["Cadence"] = 60 / df["Rolling_Avg"]
print(df)

# 2. Setup Canvas and Window Spacing
fig, ax = plt.subplots(figsize=(10, 6))
plt.subplots_adjust(bottom=0.2)  # Make room for buttons at the bottom

# 3. Helper Function to Redraw the Core Graph
def reset_plot(title_text):
    ax.clear()
    # Re-draw your base cadence curve on every click
    ax.plot(df["Step"], df["Cadence"], label="Cadence vs. Time", color="blue", zorder=3)
    ax.set_title(title_text)
    ax.set_xlabel("Time / Steps")
    ax.set_ylabel("Cadence (BPM)")
    ax.grid(axis='y', alpha=0.3)

# 4. Button Click Actions (Using 'ax.' instead of 'plt.')
def show_beat(event):
    reset_plot("Viewing Beat Intervals")
    for b_time in df["Beat"].dropna(): # .dropna() handles mismatched list lengths safely
        ax.axvline(x=b_time, color="red", linestyle="-", linewidth=1.5)
    plt.draw()

def show_step(event):
    reset_plot("Viewing Step Intervals")
    for s_time in df["Step"].dropna():
        ax.axvline(x=s_time, color="purple", linestyle=":", linewidth=1)
    plt.draw()

# 5. Create Buttons (Kept outside of functions so they stay alive)
ax_beat_btn = plt.axes([0.3, 0.05, 0.18, 0.065])
ax_step_btn = plt.axes([0.5, 0.05, 0.18, 0.065])

btn_beat = Button(ax_beat_btn, 'Show Beats', color='lightcoral', hovercolor='red')
btn_step = Button(ax_step_btn, 'Show Steps', color='lightblue', hovercolor='blue')

# Link buttons to their respective actions
btn_beat.on_clicked(show_beat)
btn_step.on_clicked(show_step)

# Initialize the window with the default "Beat" view on startup
show_beat(None)

plt.show()
