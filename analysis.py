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

steps = df["Step"].dropna().sort_values().values
beats = df["Beat"].dropna().sort_values().values

idx = np.searchsorted(beats, steps)

idx_before = np.clip(idx - 1, 0, len(beats) - 1)
idx_after = np.clip(idx, 0, len(beats) - 1)

beats_before = beats[idx_before]
beats_after = beats[idx_after]

denom = beats_after - beats_before


rpa = 360 * (steps - beats_before) / denom

rpa_norm = ((rpa + 180) % 360) - 180

# --- 3. Merging Phase Angles back to Main Dataframe Structure ---
phase_mapping_df = pd.DataFrame({
    "Step": steps,
    "Phase_Deg": rpa_norm
})

# Combine back into the primary dataframe structure
df = df.merge(phase_mapping_df, on="Step", how="left")

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
    "Phase": {
        "title": "Relative Phase Angle (0° = Perfect Synchronization)",
        "ylabel": "Phase Angle (Degrees)",
        "y": df["Phase_Deg"],
        "type": "scatter",
        "color": "crimson"
    }
}

def set_plot(graph_name):
    ax.clear()
    graph = graphs[graph_name]
    ax.set_title(graph["title"])
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(graph["ylabel"])
    
    if graph_name == "Phase":
        ax.set_ylim(-190, 190)  # Standardizes visualization box around the phase span
        ax.axhline(0, color="gray", linestyle="--", alpha=0.5) # Zero reference line
    
    if graph["type"] == "plot":
        ax.plot(df["Step"], graph["y"], color=graph["color"], linewidth=2)
        
    elif graph["type"] == "scatter":
        ax.scatter(df["Step"], graph["y"], color=graph["color"], s=40, alpha=0.85)
        ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    plt.draw()

# Button action callbacks
def show_beat_step(event): set_plot("Beat-Step")
def show_cadence(event): set_plot("Cadence")
def show_phase(event): set_plot("Phase")

# Custom UI Button Placement Axes allocations
ax_beat_btn = plt.axes([0.12, 0.05, 0.23, 0.065])
ax_cadence_btn = plt.axes([0.38, 0.05, 0.23, 0.065])
ax_phase_btn = plt.axes([0.64, 0.05, 0.23, 0.065])

btn_beat = Button(ax_beat_btn, 'Show Beat-Step', color='mistyrose', hovercolor='lightcoral')
btn_cadence = Button(ax_cadence_btn, 'Show Cadence', color='lightcyan', hovercolor='powderblue')
btn_phase = Button(ax_phase_btn, 'Show Phase Angle', color='lavender', hovercolor='plum')

btn_beat.on_clicked(show_beat_step)
btn_cadence.on_clicked(show_cadence)
btn_phase.on_clicked(show_phase)

# Initial View Default Configuration
set_plot("Beat-Step")
plt.show()

steps_taken = len(df)
avg_cadence = df["Cadence"].mean()
avg_rpa = df["Phase_Deg"].mean()