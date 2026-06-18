import csv
import random
from bluetooth import *

songs = []

with open("songs.csv") as file:
    reader = csv.DictReader(file)

    for row in reader:
        songs.append({"name": row["song"],"bpm": float(row["bpm"])})

current_song = random.choice(songs)

song_name = current_song["name"]

song_bpm = current_song["bpm"]