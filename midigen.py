try:
    import rtmidi
except ImportError:
    import rtmidi2 as rtmidi
except ImportError:
    pass

import sys
import platformdirs
import json
sys.modules['rtmidi'] = rtmidi

try:
    import fluidsynth
    FLUIDSYNTH_AVAILABLE = True
except ImportError:
    FLUIDSYNTH_AVAILABLE = False

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mido
import random
import os
import threading
import time
import shutil
import queue

# --- Force PyInstaller to bundle the actual driver ---
mido.set_backend('mido.backends.portmidi')

# ==========================================
# PHASE 1: CONSTANTS & DICTIONARIES
# ==========================================
BG_COLOR, FG_COLOR, MATRIX_COLOR, MUTE_BG = "#0C0C0C", "#39FF14", "#004400", "#222222"
SOLO_FLASH_ON, SOLO_FLASH_OFF = "#9C27B0", "#444444"
FONT_MAIN, FONT_TITLE, FONT_ASCII = ("Arial", 9, "bold"), ("Arial", 10, "underline"), ("Courier", 8)

SCALE_INTERVALS = {
    "Custom (Use Keyboard)": [], "Chromatic": [0,1,2,3,4,5,6,7,8,9,10,11], "Major (Ionian)": [0,2,4,5,7,9,11],
    "Minor (Aeolian)": [0,2,3,5,7,8,10], "Harmonic Minor": [0,2,3,5,7,8,11], "Melodic Minor": [0,2,3,5,7,9,11],
    "Dorian": [0,2,3,5,7,9,10], "Phrygian": [0,1,3,5,7,8,10], "Lydian": [0,2,4,6,7,9,11],
    "Mixolydian": [0,2,4,5,7,9,10], "Locrian": [0,1,3,5,6,8,10], "Pentatonic Maj": [0,2,4,7,9],
    "Pentatonic Min": [0,3,5,7,10], "Whole Tone": [0,2,4,6,8,10], "Diminished": [0,2,3,5,6,8,9,11]
}

NOTES_LIST = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ROOT_NOTES = {note: 60 + i for i, note in enumerate(NOTES_LIST)}

DIGITONE_SHAPES = {
    "Unison": [0], "Minor": [0,3,7], "Major": [0,4,7], "Sus2": [0,2,7], "Sus4": [0,5,7],
    "m7": [0,3,7,10], "M7": [0,4,7,10], "mMaj7": [0,3,7,11], "Maj7": [0,4,7,11], "m7b5": [0,3,6,10],
    "dim": [0,3,6], "dim7": [0,3,6,9], "aug": [0,4,8], "m9": [0,3,7,10,14], "M9": [0,4,7,10,14], "Maj9": [0,4,7,11,14]
}

COMPOSER_PROBABILITIES = {
    "J.S. Bach (Baroque)": {-2: 5, -1: 35, 0: 5, 1: 35, 2: 10, 3: 5, -3: 5},
    "W.A. Mozart (Classical)": {-2: 15, -1: 25, 0: 5, 1: 25, 2: 15, 3: 10, -3: 5},
    "Antonio Vivaldi (Baroque)": {-2: 20, -1: 15, 0: 10, 1: 15, 2: 20, 4: 10, -4: 10},
    "G.F. Handel (Baroque)": {-2: 10, -1: 30, 0: 10, 1: 30, 2: 10, 3: 5, -3: 5},
    "Ludwig van Beethoven": {-3: 15, -1: 20, 0: 10, 1: 20, 2: 15, 3: 20},
    "Joseph Haydn (Classical)": {-2: 10, -1: 30, 0: 5, 1: 30, 2: 10, 3: 10, -3: 5},
    "Franz Schubert (Romantic)": {-2: 10, -1: 35, 0: 10, 1: 35, 2: 10},
    "Frederic Chopin (Romantic)": {-4: 5, -2: 10, -1: 30, 0: 5, 1: 30, 2: 10, 4: 10},
    "Franz Liszt (Romantic)": {-5: 10, -1: 20, 0: 5, 1: 20, 2: 15, 5: 10, 7: 10, -7: 10},
    "Johannes Brahms (Romantic)": {-2: 15, -1: 25, 0: 10, 1: 25, 2: 15, 3: 5, -3: 5},
    "P.I. Tchaikovsky (Romantic)": {-2: 10, -1: 30, 0: 5, 1: 30, 2: 10, 4: 5, -4: 10},
    "Claude Debussy (Impressionist)":{-2: 15, -1: 25, 0: 15, 1: 25, 2: 15, 3: 5},
    "Erik Satie (Modern/Minimal)": {-2: 15, -1: 20, 0: 20, 1: 20, 2: 15, 4: 5, -4: 5},
    "Philip Glass (Minimalism)": {-2: 15, -1: 20, 0: 30, 1: 20, 2: 15},
    "Brian Eno (Ambient)": {-3: 5, -1: 15, 0: 40, 1: 15, 3: 5, 4: 10, -4: 10},
    "Aphex Twin (IDM)": {-7: 10, -4: 10, -2: 10, -1: 15, 0: 10, 1: 15, 2: 10, 4: 10, 7: 10}
}

ASCII_ART = {
    "J.S. Bach (Baroque)": "  [BACH]\n  _,-._\n / \\_/ \\\n >-(_)-<\n \\_/ \\_/\n   `-'",
    "W.A. Mozart (Classical)": " [MOZART]\n  .---.\n ( @ @ )\n  \\_^_/\n  /|||\\\n  `---'",
    "Philip Glass (Minimalism)": "  [GLASS]\n  .---.\n ( - - )\n  \\_=_/\n  /|||\\\n  `---'",
    "Aphex Twin (IDM)": " [APHEX]\n    _ \n   / \\\n  /_  \\\n /  \\_/\n \\___/ ",
    "Brian Eno (Ambient)": "  [ENO]\n  .---.\n /     \\\n(  - -  )\n \\  -  /\n  `---'",
    "default": " [CHOOSE]\n  .-.\n |? ?|\n | ^ |\n  '-'"
}

def get_resource_path(rel_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, rel_path)

CONFIG_DIR = platformdirs.user_config_dir("midigen", "the_passenger")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

def save_settings():
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        
        settings = {
            "style_var": style_var.get(),
            "root_var": root_var.get(),
            "scale_var": scale_var.get(),
            "length_var": length_var.get(),
            "algo_var": algo_var.get(),
            "melody_ch_var": melody_ch_var.get(),
            "harmony_ch_var": harmony_ch_var.get(),
            "chord_ch_var": chord_ch_var.get(),
            "bass_ch_var": bass_ch_var.get(),
            "harm_var": harm_var.get(),
            "chord_style_var": chord_style_var.get(),
            "digitone_shape_var": digitone_shape_var.get(),
            "chord_rhythm_var": chord_rhythm_var.get(),
            "chord_oct_var": chord_oct_var.get(),
            "bass_pat_var": bass_pat_var.get(),
            "bass_rhythm_var": bass_rhythm_var.get(),
            "midi_out_var": midi_out_var.get(),
            "midi_in_var": midi_in_var.get(),
            "sync_var": sync_var.get(),
            "workflow_var": workflow_var.get(),
            "lock_notes_var": lock_notes_var.get(),
            "fs_enabled_var": fs_enabled_var.get(),
            "sf_path_vars": [v.get() for v in sf_path_vars],
            "tempo_slider": tempo_slider.get(),
            "complexity_slider": complexity_slider.get(),
            "vel_slider": vel_slider.get(),
            "feel_slider": feel_slider.get(),
            "mel_gate_slider": mel_gate_slider.get(),
            "hrm_gate_slider": hrm_gate_slider.get(),
            "strum_slider": strum_slider.get(),
            "chord_gate_slider": chord_gate_slider.get(),
            "bass_comp_slider": bass_comp_slider.get(),
            "bas_gate_slider": bas_gate_slider.get(),
            "key_states": {str(k): v.get() for k, v in key_states.items()},
            "mute_mel_var": mute_mel_var.get(),
            "solo_mel_var": solo_mel_var.get(),
            "mute_hrm_var": mute_hrm_var.get(),
            "solo_hrm_var": solo_hrm_var.get(),
            "mute_chd_var": mute_chd_var.get(),
            "solo_chd_var": solo_chd_var.get(),
            "mute_bas_var": mute_bas_var.get(),
            "solo_bas_var": solo_bas_var.get()
        }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=4)

        print(f"Saved settings to {CONFIG_FILE}")
    except Exception as e:
        print(f"Failed to save settings: {e}")

def load_settings():
    try:
        if not os.path.exists(CONFIG_FILE):
            return
        
        with open(CONFIG_FILE, 'r') as f:
            settings = json.load(f)
            
        if "style_var" in settings: style_var.set(settings["style_var"])
        if "root_var" in settings: root_var.set(settings["root_var"])
        if "scale_var" in settings: scale_var.set(settings["scale_var"])
        if "length_var" in settings: length_var.set(settings["length_var"])
        if "algo_var" in settings: algo_var.set(settings["algo_var"])
        if "melody_ch_var" in settings: melody_ch_var.set(settings["melody_ch_var"])
        if "harmony_ch_var" in settings: harmony_ch_var.set(settings["harmony_ch_var"])
        if "chord_ch_var" in settings: chord_ch_var.set(settings["chord_ch_var"])
        if "bass_ch_var" in settings: bass_ch_var.set(settings["bass_ch_var"])
        if "harm_var" in settings: harm_var.set(settings["harm_var"])
        if "chord_style_var" in settings: chord_style_var.set(settings["chord_style_var"])
        if "digitone_shape_var" in settings: digitone_shape_var.set(settings["digitone_shape_var"])
        if "chord_rhythm_var" in settings: chord_rhythm_var.set(settings["chord_rhythm_var"])
        if "chord_oct_var" in settings: chord_oct_var.set(settings["chord_oct_var"])
        if "bass_pat_var" in settings: bass_pat_var.set(settings["bass_pat_var"])
        if "bass_rhythm_var" in settings: bass_rhythm_var.set(settings["bass_rhythm_var"])
        if "midi_out_var" in settings: midi_out_var.set(settings["midi_out_var"])
        if "midi_in_var" in settings: midi_in_var.set(settings["midi_in_var"])
        if "sync_var" in settings: sync_var.set(settings["sync_var"])
        if "workflow_var" in settings: workflow_var.set(settings["workflow_var"])
        if "lock_notes_var" in settings: lock_notes_var.set(settings["lock_notes_var"])
        if "fs_enabled_var" in settings: fs_enabled_var.set(settings["fs_enabled_var"])
        
        if "sf_path_vars" in settings:
            for i, val in enumerate(settings["sf_path_vars"]):
                if i < len(sf_path_vars): sf_path_vars[i].set(val)
        
        if "tempo_slider" in settings: tempo_slider.set(settings["tempo_slider"])
        if "complexity_slider" in settings: complexity_slider.set(settings["complexity_slider"])
        if "vel_slider" in settings: vel_slider.set(settings["vel_slider"])
        if "feel_slider" in settings: feel_slider.set(settings["feel_slider"])
        if "mel_gate_slider" in settings: mel_gate_slider.set(settings["mel_gate_slider"])
        if "hrm_gate_slider" in settings: hrm_gate_slider.set(settings["hrm_gate_slider"])
        if "strum_slider" in settings: strum_slider.set(settings["strum_slider"])
        if "chord_gate_slider" in settings: chord_gate_slider.set(settings["chord_gate_slider"])
        if "bass_comp_slider" in settings: bass_comp_slider.set(settings["bass_comp_slider"])
        if "bas_gate_slider" in settings: bas_gate_slider.set(settings["bas_gate_slider"])
        
        if "key_states" in settings:
            for k, v in settings["key_states"].items():
                if int(k) in key_states: key_states[int(k)].set(v)
                
        if "mute_mel_var" in settings: mute_mel_var.set(settings["mute_mel_var"])
        if "solo_mel_var" in settings: solo_mel_var.set(settings["solo_mel_var"])
        if "mute_hrm_var" in settings: mute_hrm_var.set(settings["mute_hrm_var"])
        if "solo_hrm_var" in settings: solo_hrm_var.set(settings["solo_hrm_var"])
        if "mute_chd_var" in settings: mute_chd_var.set(settings["mute_chd_var"])
        if "solo_chd_var" in settings: solo_chd_var.set(settings["solo_chd_var"])
        if "mute_bas_var" in settings: mute_bas_var.set(settings["mute_bas_var"])
        if "solo_bas_var" in settings: solo_bas_var.set(settings["solo_bas_var"])
        
        # Update M/S buttons based on loaded variables
        def update_ms_btn(var, btn, active_color):
             if var.get(): btn.config(bg=active_color)
             else: btn.config(bg="#555555")

        update_ms_btn(mute_mel_var, btn_mute_mel, "#FF0000")
        update_ms_btn(solo_mel_var, btn_solo_mel, "#9C27B0")
        update_ms_btn(mute_hrm_var, btn_mute_hrm, "#FF0000")
        update_ms_btn(solo_hrm_var, btn_solo_hrm, "#9C27B0")
        update_ms_btn(mute_chd_var, btn_mute_chd, "#FF0000")
        update_ms_btn(solo_chd_var, btn_solo_chd, "#9C27B0")
        update_ms_btn(mute_bas_var, btn_mute_bas, "#FF0000")
        update_ms_btn(solo_bas_var, btn_solo_bas, "#9C27B0")

        if fs_enabled_var.get():
            app.after(1000, toggle_fluidsynth)

    except Exception as e:
        print(f"Failed to load settings: {e}")

# ==========================================
# PHASE 2: ROOT APP & CANVAS SETUP
# ==========================================
app = tk.Tk()
app.title("the passenger's midi generator")
try: app.state('zoomed') 
except tk.TclError:
    try: app.attributes('-zoomed', True) 
    except tk.TclError: app.geometry("1400x900")
app.configure(bg=BG_COLOR)
app.update_idletasks()
target_width, target_height = app.winfo_screenwidth(), app.winfo_screenheight()

# Fast Canvas Background (No Scrollbar)
canvas = tk.Canvas(app, bg=BG_COLOR, highlightthickness=0)
canvas.pack(fill="both", expand=True)

# Main UI centered inside Canvas
main_frame = tk.Frame(canvas, bg=BG_COLOR, padx=20, pady=10)
canvas_window = canvas.create_window((target_width//2, target_height//2), window=main_frame, anchor="center")

def on_canvas_configure(event):
    if event.widget == canvas:
        canvas.coords(canvas_window, (event.width // 2, event.height // 2))
canvas.bind("<Configure>", on_canvas_configure)

# ==========================================
# PHASE 3: VARIABLES & STATE
# ==========================================
is_playing, current_playing_part, queued_part, blink_state = False, "A", None, False
next_events_A, next_events_B = [], []
live_events_update, reload_staged, gen_timer = False, False, None
seed_mel, seed_hrm, seed_chd, seed_bas, seed_prog = time.time(), time.time()+1, time.time()+2, time.time()+3, time.time()+4
latest_midi_hex, current_play_tick, target_ticks_global = "", 0, 1920
pr_events_A, pr_events_B, matrix_items, piano_roll_items = [], [], [], []
ui_msg_queue = queue.Queue()

mute_mel_var, solo_mel_var = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
mute_hrm_var, solo_hrm_var = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
mute_chd_var, solo_chd_var = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
mute_bas_var, solo_bas_var = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
key_states = {i: tk.BooleanVar(value=False) for i in range(12)}

style_var, root_var, scale_var = tk.StringVar(value="Aphex Twin (IDM)"), tk.StringVar(value="C"), tk.StringVar(value="Dorian")
length_var, algo_var = tk.StringVar(value="8 Bars"), tk.StringVar(value="Markov Chain")
melody_ch_var, harmony_ch_var = tk.StringVar(value="1"), tk.StringVar(value="2")
chord_ch_var, bass_ch_var = tk.StringVar(value="3"), tk.StringVar(value="4")
harm_var = tk.BooleanVar(value=True)

chord_style_var, digitone_shape_var = tk.StringVar(value="Diatonic Triads"), tk.StringVar(value="m7")
chord_rhythm_var, chord_oct_var = tk.StringVar(value="Whole Notes"), tk.StringVar(value="0")
bass_pat_var, bass_rhythm_var = tk.StringVar(value="Regular"), tk.StringVar(value="16th Notes")

midi_out_var, midi_in_var = tk.StringVar(), tk.StringVar()
sync_var, ext_bpm_var = tk.StringVar(value="Internal"), tk.StringVar(value="EXT BPM: ---")
workflow_var, lock_notes_var = tk.StringVar(value="Instant"), tk.BooleanVar(value=True)

# FluidSynth Variables
fs_enabled_var = tk.BooleanVar(value=False)
sf_path_vars = [tk.StringVar(value="Select SoundFont...") for _ in range(4)]
fs_instance = None
fs_sfids = [None] * 4

# ==========================================
# PHASE 4: LOGIC & GENERATOR FUNCTIONS
# ==========================================
def make_label(parent, text, **kwargs):
    return tk.Label(parent, text=text, bg=BG_COLOR, fg=FG_COLOR, font=FONT_MAIN, **kwargs)

def snap_to_scale(midi_val, scale_notes):
    if not scale_notes: return midi_val
    return min(scale_notes, key=lambda x: abs(x - midi_val))

def get_scale_notes(root_name, scale_type, octaves=8):
    if scale_type == "Custom (Use Keyboard)":
        intervals = [i for i in range(12) if key_states[i].get()]
        if not intervals: intervals = [0]
        base_note = 12 
        return sorted(list(set([base_note + iv + (oct * 12) for oct in range(octaves) for iv in intervals])))
    base_note = ROOT_NOTES[root_name] - 48 
    intervals = SCALE_INTERVALS[scale_type]
    return sorted([base_note + iv + (oct * 12) for oct in range(octaves) for iv in intervals])

def generate_chord_progression(target_ticks, note_duration, scale_length, rng):
    progressions = [[0,3,4,0], [0,5,3,4], [0,4,5,3], [5,3,0,4], [1,4,0,0], [0,3,0,4]]
    prog = rng.choice(progressions)
    chord_map, ticks, step = [], 0, 0
    while ticks < target_ticks:
        dur = note_duration if ticks + note_duration <= target_ticks else target_ticks - ticks
        chord_map.append((prog[step % len(prog)], dur))
        ticks += dur; step += 1
    return chord_map

def _generate_melody(notes, style, algo, complexity, vel_amt, start_index, target_ticks, rng, chord_map, gate_pct):
    raw_section, current_index, total_ticks, step = [], start_index, 0, 0
    probabilities = COMPOSER_PROBABILITIES.get(style, COMPOSER_PROBABILITIES["Brian Eno (Ambient)"])
    jumps, weights = list(probabilities.keys()), list(probabilities.values())
    motif = [(max(0, min(current_index + rng.randint(-3, 3), len(notes)-1)), rng.choice([240, 480])) for _ in range(rng.randint(4, 8))]
    arp_dir = 1
    while total_ticks < target_ticks:
        if algo == "Markov Chain":
            chosen_jump = rng.choices(jumps, weights=weights, k=1)[0]
            if complexity > 3 and chosen_jump != 0: chosen_jump = int(chosen_jump * (complexity / 2))
            current_index = max(0, min(current_index + chosen_jump, len(notes) - 1)) 
            duration = rng.choice([240, 480, 960])
        elif algo == "Brownian Motion":
            current_index = max(0, min(current_index + (rng.choice([-1, 0, 1]) * max(1, complexity // 2)), len(notes) - 1)) 
            duration = rng.choice([240, 480, 960])
        elif algo == "Ostinato Motif":
            current_index, duration = motif[step % len(motif)]
        elif algo == "Arpeggiator":
            current_index += arp_dir * max(1, complexity // 2)
            if current_index >= len(notes) - 5: arp_dir = -1
            elif current_index <= 5: arp_dir = 1
            duration = rng.choice([120, 240]) 
        
        if algo in ["Markov Chain", "Brownian Motion"] and rng.random() > 0.7:
            current_tick = total_ticks
            for c_idx, c_dur in chord_map:
                if current_tick < c_dur: current_index = c_idx + (len(notes)//2); break
                current_tick -= c_dur
        
        if "Eno" in style and algo != "Arpeggiator": duration = rng.choice([960, 1920])
        elif "Aphex" in style: duration = rng.choice([120, 120, 240, 480])
        elif "Glass" in style: duration = rng.choice([120, 240, 240])
        
        if total_ticks + duration > target_ticks: duration = target_ticks - total_ticks
        base_vel = 80 if step % 4 == 0 else 70 
        gate_dur = max(10, int(duration * (gate_pct / 100.0)))
        raw_section.append((current_index, duration, max(1, min(127, base_vel + rng.randint(-vel_amt, vel_amt))), 0, gate_dur))
        total_ticks += duration; step += 1
    return raw_section

def generate_single_section(notes, style, algo, complexity, vel_amt, target_ticks, is_b_section, rng, prog, gate_pct):
    start_index = len(notes) // 2 
    if is_b_section: start_index = min(start_index + 4, len(notes) - 1)
    return _generate_melody(notes, style, algo, complexity, vel_amt, start_index, target_ticks, rng, prog, gate_pct)

def generate_relational_harmony(melody_data, notes, vel_amt, feel_amt, rng, is_sparse, gate_pct):
    harmony_data = []
    for item in melody_data:
        idx, dur, vel, offset, _ = item
        if is_sparse:
            if dur >= 480 or (dur == 240 and rng.random() > 0.7):
                harm_idx = min(idx + rng.choice([2, 4]), len(notes) - 1) 
                offset_val = min(rng.randint(0, feel_amt) if feel_amt > 0 else 0, max(0, dur - 10))
                gate_dur = max(offset_val + 10, int(dur * (gate_pct / 100.0)))
                harmony_data.append((notes[harm_idx], dur, max(1, min(127, 50 + rng.randint(-vel_amt, vel_amt))), offset_val, gate_dur))
            else: harmony_data.append(("REST", dur, 0, 0, dur)) 
        else:
            if dur >= 480:
                accumulated = 0
                while accumulated < dur:
                    s_dur = min(dur - accumulated, rng.choice([120, 240, 480]))
                    harm_idx = max(0, min(idx + rng.choice([-4, -2, 2, 4, 5]), len(notes) - 1))
                    offset_val = rng.randint(0, feel_amt) if feel_amt > 0 else 0
                    gate_dur = max(offset_val + 10, int(s_dur * (gate_pct / 100.0)))
                    harmony_data.append((notes[harm_idx], s_dur, max(1, min(127, 60 + rng.randint(-vel_amt, vel_amt))), offset_val, gate_dur))
                    accumulated += s_dur
            else:
                harm_idx = max(0, min(idx + rng.choice([-2, 2, 3]), len(notes) - 1)) 
                offset_val = rng.randint(0, feel_amt) if feel_amt > 0 else 0
                gate_dur = max(offset_val + 10, int(dur * (gate_pct / 100.0)))
                harmony_data.append((notes[harm_idx], dur, max(1, min(127, 55 + rng.randint(-vel_amt, vel_amt))), offset_val, gate_dur))
    return harmony_data

def generate_chords_from_map(chord_map, notes, vel_amt, strum_max, style, digi_shape, oct_shift, rhythm, gate_pct, rng):
    chord_melody, c_vel_amt, scale_len = [], max(0, vel_amt // 2), len(notes) // 8
    for c_idx, map_dur in chord_map:
        ticks_accumulated = 0
        base_idx = min(c_idx + (scale_len * 3), len(notes) - 1)
        while ticks_accumulated < map_dur:
            play_note = True
            if rhythm == "Whole Notes": slice_dur = 1920
            elif rhythm == "Half Notes": slice_dur = 960
            elif rhythm == "Quarter Notes": slice_dur = 480
            elif rhythm == "Eighth Notes": slice_dur = 240
            elif rhythm == "Offbeats": slice_dur = 240; play_note = (ticks_accumulated // 240) % 2 != 0
            elif rhythm == "Syncopated": pos = ticks_accumulated % 1920; slice_dur = 720 if pos in [0, 720] else (480 if pos == 1440 else 240)
            else: slice_dur = map_dur
            slice_dur = min(slice_dur, map_dur - ticks_accumulated)
            
            if not play_note: chord_melody.append(("REST", slice_dur, 0, [0], slice_dur))
            else:
                velocity = max(1, min(127, 65 + rng.randint(-c_vel_amt, c_vel_amt)))
                if style == "Digitone Shapes":
                    raw_chord = [notes[min(base_idx, len(notes)-1)] + sm + (int(oct_shift) * 12) for sm in DIGITONE_SHAPES.get(digi_shape, [0,3,7])]
                    chord_notes = sorted(list(set([snap_to_scale(n, notes) for n in raw_chord])))
                else:
                    if scale_var.get() == "Chromatic": intervals = [0, 7] 
                    elif style == "Diatonic Triads": intervals = [0, 2, 4]
                    elif style == "Diatonic 7ths": intervals = [0, 2, 4, 6]
                    elif style == "Sus2 / Sus4": intervals = [0, 1, 4] if rng.random() > 0.5 else [0, 3, 4]
                    else: intervals = []
                    chord_notes = [notes[min(base_idx + i, len(notes) - 1)] + (int(oct_shift) * 12) for i in intervals]
                    
                strum_offsets = [0] + [rng.randint(0, strum_max) if strum_max > 0 else 0 for _ in range(1, len(chord_notes))]
                gate_dur = max(sum(strum_offsets) + 10, int(slice_dur * (gate_pct / 100.0)))
                chord_melody.append((chord_notes, slice_dur, velocity, strum_offsets, gate_dur))
            ticks_accumulated += slice_dur
    return chord_melody

def get_bass_pattern(name, comp, rng):
    if name == "Rock 1": return [(7 if (comp > 3 and i % 2 != 0) else 0, 240, 10 if i%2==0 else 0) for i in range(8)]
    elif name == "Rock 2": 
        pat = []
        for i in range(4): pat.extend([(0, 120, 10), (0, 120, 0), (12 if comp > 4 and i == 3 else 0, 240, 10)])
        return pat
    elif name == "Pop 1": 
        pat = []
        for i in range(4): pat.extend([(0, 120, 10), (12, 120, 5), ("REST", 120, 0), (12 if comp>2 else 0, 120, 5)])
        return pat
    elif name == "Pop 2": return [(0, 360, 10), (0, 120, 0), (12, 240, 10), (0, 240, 0), (0, 480, 10), (7 if comp>2 else 0, 480, 5)]
    elif name == "Dub 1": return [("REST", 480, 0), (0, 480, 10), (7 if comp>3 else 0, 480, 5), (12 if comp>2 else 0, 480, 5)]
    elif name == "Dub 2": return [(0, 480, 10), (12, 240, 5), (0, 240, 5), (7, 480, 10), (0 if comp>1 else "REST", 480, 0)]
    elif name == "Dub 3": return [(0, 720, 10), (12, 240, 5), ("REST", 480, 0), (7 if comp>3 else 0, 480, 10)]
    elif name == "Funk 1": return [(0,120,10), ("REST",120,0), (0,120,5), (12,120,10), ("REST",120,0), (0,120,5), (7 if comp>3 else 0,240,10), (0,240,10), ("REST",120,0), (0,120,5), (10 if comp>2 else 0,240,10), (0,240,10)]
    elif name == "Synthwave":
        pat = []
        for i in range(8): pat.extend([(0, 120, 10), (12 if comp > 2 else 0, 120, 5)])
        return pat
    elif name == "Disco":
        pat = []
        for i in range(4): pat.extend([(0, 240, 10), (12, 240, 10)])
        return pat
    elif name == "Latin": return [(0, 360, 10), (7 if comp>2 else 0, 360, 10), (0, 240, 10), (0, 360, 10), (5 if comp>3 else 0, 360, 10), (7 if comp>2 else 0, 240, 10)]
    return [(0, 480, 10)] * 4

def generate_bassline_from_map(chord_map, notes, target_ticks, vel_amt, rhythm_style, bass_pat, bass_comp, rng, gate_pct):
    bass_melody, b_vel_amt, ticks_accumulated, step = [], max(0, vel_amt // 4), 0, 0
    while ticks_accumulated < target_ticks:
        active_root, current_tick_map = 0, 0
        for c_idx, c_dur in chord_map:
            if current_tick_map <= ticks_accumulated < current_tick_map + c_dur:
                active_root = notes[min(c_idx, len(notes)-1)] % 12; break
            current_tick_map += c_dur
        bass_midi = active_root + 36 
        if bass_pat == "Regular":
            note_duration = 120 if rhythm_style == "16th Notes" else (240 if rhythm_style == "8th Notes" else 1920)
            if rhythm_style != "Whole Note" and bass_comp > 3 and step % 2 != 0: bass_midi += 12 
            if bass_comp < 3 and rng.random() > 0.8: vel, bass_midi = 0, "REST"
            else: vel = max(1, min(127, 60 + rng.randint(-b_vel_amt, b_vel_amt)))
            dur = note_duration if ticks_accumulated + note_duration <= target_ticks else target_ticks - ticks_accumulated
            gate_dur = dur if bass_midi == "REST" else max(10, int(dur * (gate_pct / 100.0)))
            bass_note = bass_midi if bass_midi == "REST" else snap_to_scale(bass_midi, notes)
            bass_melody.append((bass_note, dur, vel, 0, gate_dur))
            ticks_accumulated += dur; step += 1
        else:
            pattern_data = get_bass_pattern(bass_pat, bass_comp, rng)
            for note_offst, p_dur, acc in pattern_data:
                if ticks_accumulated >= target_ticks: break
                current_tick_map = 0
                for c_idx, c_dur in chord_map:
                    if current_tick_map <= ticks_accumulated < current_tick_map + c_dur:
                        bass_midi = (notes[min(c_idx, len(notes)-1)] % 12) + 36; break
                    current_tick_map += c_dur
                dur = p_dur if ticks_accumulated + p_dur <= target_ticks else target_ticks - ticks_accumulated
                gate_dur = max(10, int(dur * (gate_pct / 100.0)))
                if note_offst != "REST":
                    vel = max(1, min(127, 60 + acc + rng.randint(-b_vel_amt, b_vel_amt)))
                    bass_melody.append((snap_to_scale(bass_midi + note_offst, notes), dur, vel, 0, gate_dur))
                else: bass_melody.append(("REST", dur, 0, 0, dur))
                ticks_accumulated += dur
    return bass_melody

def create_midi(filename, notes, melody_data, harmony_data, chord_data, bassline, tempo_bpm):
    try:
        mid = mido.MidiFile()
        melody_track = mido.MidiTrack(); mid.tracks.append(melody_track)
        melody_track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo_bpm)))
        for item in melody_data:
            idx, dur, vel, offset, gate_dur = item
            n_val = notes[idx] if isinstance(idx, int) else idx
            melody_track.append(mido.Message('note_on', channel=0, note=n_val, velocity=vel, time=offset))
            melody_track.append(mido.Message('note_off', channel=0, note=n_val, velocity=64, time=max(0, gate_dur - offset)))
            rem_time = max(0, dur - max(gate_dur, offset))
            if rem_time > 0: melody_track.append(mido.Message('note_off', channel=0, note=0, velocity=0, time=rem_time))
            
        if harmony_data:
            harm_track = mido.MidiTrack(); mid.tracks.append(harm_track)
            for item in harmony_data:
                val, dur, vel, offset, gate_dur = item
                if val == "REST": harm_track.append(mido.Message('note_off', channel=1, note=0, velocity=0, time=dur))
                else:
                    harm_track.append(mido.Message('note_on', channel=1, note=val, velocity=vel, time=offset))
                    harm_track.append(mido.Message('note_off', channel=1, note=val, velocity=64, time=max(0, gate_dur - offset)))
                    rem_time = max(0, dur - max(gate_dur, offset))
                    if rem_time > 0: harm_track.append(mido.Message('note_off', channel=1, note=0, velocity=0, time=rem_time))

        if chord_data:
            chord_track = mido.MidiTrack(); mid.tracks.append(chord_track)
            for item in chord_data:
                c_notes, dur, vel, strum_offsets, gate_dur = item
                if c_notes == "REST": chord_track.append(mido.Message('note_off', channel=2, note=0, velocity=0, time=dur))
                elif isinstance(c_notes, list): 
                    total_on = sum(strum_offsets)
                    for i, n in enumerate(c_notes): chord_track.append(mido.Message('note_on', channel=2, note=n, velocity=vel, time=strum_offsets[i]))
                    for i, n in enumerate(c_notes):
                        chord_track.append(mido.Message('note_off', channel=2, note=n, velocity=64, time=max(0, gate_dur - total_on) if i == 0 else 0))
                    rem_time = max(0, dur - max(gate_dur, total_on))
                    if rem_time > 0: chord_track.append(mido.Message('note_off', channel=2, note=0, velocity=0, time=rem_time))
                else: 
                    n_val = notes[c_notes] if isinstance(c_notes, int) else c_notes
                    chord_track.append(mido.Message('note_on', channel=2, note=n_val, velocity=vel, time=0))
                    chord_track.append(mido.Message('note_off', channel=2, note=n_val, velocity=64, time=gate_dur))
                    rem_time = max(0, dur - gate_dur)
                    if rem_time > 0: chord_track.append(mido.Message('note_off', channel=2, note=0, velocity=0, time=rem_time))
            
        if bassline:
            bass_track = mido.MidiTrack(); mid.tracks.append(bass_track)
            for item in bassline:
                val, dur, vel, offset, gate_dur = item
                if val == "REST": bass_track.append(mido.Message('note_off', channel=3, note=0, velocity=0, time=dur))
                else:
                    bass_track.append(mido.Message('note_on', channel=3, note=val, velocity=vel, time=offset))
                    bass_track.append(mido.Message('note_off', channel=3, note=val, velocity=64, time=max(0, gate_dur - offset)))
                    rem_time = max(0, dur - max(gate_dur, offset))
                    if rem_time > 0: bass_track.append(mido.Message('note_off', channel=3, note=0, velocity=0, time=rem_time))
        mid.save(filename)
        return True
    except Exception: return False

def extract_events(filename):
    mid = mido.MidiFile(filename); events = []
    for track in mid.tracks:
        current_tick = 0
        for msg in track:
            current_tick += msg.time
            if not msg.is_meta: events.append((current_tick, msg))
    events.sort(key=lambda x: x[0])
    return events, mid.ticks_per_beat

def parse_for_piano_roll(events):
    active, parsed = {}, []
    for t, msg in events:
        if hasattr(msg, 'note'):
            if msg.type == 'note_on' and msg.velocity > 0: active[(msg.channel, msg.note)] = t
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                st = active.pop((msg.channel, msg.note), None)
                if st is not None: parsed.append({'ch': msg.channel, 'note': msg.note, 'start': st, 'end': t})
    return parsed

def render_piano_roll(part_events):
    try: piano_roll_canvas.delete("note")
    except: return
    min_note, max_note, pr_width, offset_x = 24, 96, 720, 30
    note_range = max_note - min_note
    colors = {3: "#FFC107", 2: "#9C27B0", 1: "#00FFFF", 0: "#39FF14"} 
    for draw_ch in [3, 2, 1, 0]:
        for ev in part_events:
            if ev['ch'] == draw_ch:
                x0 = offset_x + (ev['start'] / max(1, target_ticks_global)) * (pr_width - offset_x)
                x1 = offset_x + (ev['end'] / max(1, target_ticks_global)) * (pr_width - offset_x)
                y0 = 100 - ((ev['note'] - min_note) / note_range) * 100
                piano_roll_canvas.create_rectangle(x0, y0 - 3, max(x0+2, x1), y0+1, fill=colors[draw_ch], outline="", tags="note")
    piano_roll_canvas.tag_raise("playhead")

# --- UI & PLAYBACK CALLBACKS ---
def is_track_muted(channel, local_mute_active, local_solo_active):
    any_solos_active = solo_mel_var.get() or solo_hrm_var.get() or solo_chd_var.get() or solo_bas_var.get()
    if any_solos_active and not local_solo_active: return True
    if local_mute_active: return True
    return False

def update_status(text, color):
    try: status_label.config(text=f"> {text}", fg=color)
    except: pass

def panic_action():
    update_status("PANIC: KILLING ALL NOTES...", "#FF0000")
    if fs_enabled_var.get() and fs_instance:
        try:
            for ch in range(16):
                fs_instance.cc(ch, 123, 0)
                fs_instance.cc(ch, 120, 0)
        except: pass

    out_port_name = midi_out_var.get()
    if not out_port_name or out_port_name == "No Output Devices": return
    def kill_notes():
        try:
            with mido.open_output(out_port_name) as out_port:
                for ch in range(16):
                    out_port.send(mido.Message('control_change', channel=ch, control=123, value=0)) 
                    out_port.send(mido.Message('control_change', channel=ch, control=120, value=0)) 
                    for note in range(128): out_port.send(mido.Message('note_off', channel=ch, note=note, velocity=0))
        except: pass
        if not is_playing: app.after(0, lambda: update_status("STOPPED", "#FF0000"))
    threading.Thread(target=kill_notes, daemon=True).start()

def stop_playback():
    global is_playing, queued_part
    is_playing, queued_part = False, None
    panic_action()

def force_stop_state():
    global is_playing
    is_playing = False
    sync_var.set("Internal")
    update_status("READY", FG_COLOR)

def play_live_thread(file_a, file_b, out_port_name, in_port_name, sync_mode):
    global is_playing, current_playing_part, queued_part, live_events_update
    global next_events_A, next_events_B, reload_staged, latest_midi_hex, current_play_tick
    is_playing, queued_part, live_events_update, reload_staged, current_play_tick = True, None, False, False, 0
    update_status(f"PLAYING PART {current_playing_part}...", FG_COLOR)
    app.after(0, ui_blinker_loop)
    app.after(0, solo_flasher_loop)
    active_notes = set() 
    
    def process_message(msg):
        global latest_midi_hex
        if hasattr(msg, 'channel'):
            ch_tgt = None
            is_muted_flag = False
            try:
                if msg.channel == 0: 
                    ch_tgt = int(melody_ch_var.get())-1
                    is_muted_flag = is_track_muted(ch_tgt, mute_mel_var.get(), solo_mel_var.get())
                elif msg.channel == 1: 
                    ch_tgt = int(harmony_ch_var.get())-1
                    is_muted_flag = is_track_muted(ch_tgt, mute_hrm_var.get(), solo_hrm_var.get())
                elif msg.channel == 2: 
                    ch_tgt = int(chord_ch_var.get())-1
                    is_muted_flag = is_track_muted(ch_tgt, mute_chd_var.get(), solo_chd_var.get())
                elif msg.channel == 3: 
                    ch_tgt = int(bass_ch_var.get())-1
                    is_muted_flag = is_track_muted(ch_tgt, mute_bas_var.get(), solo_bas_var.get())
                if ch_tgt is not None: msg = msg.copy(channel=ch_tgt)
            except: pass
            if msg.type == 'note_on' and msg.velocity > 0:
                if is_muted_flag: return None
                active_notes.add((msg.channel, msg.note))
                ui_msg_queue.put(("note_on", msg.note, msg.channel))
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                active_notes.discard((msg.channel, msg.note))
        latest_midi_hex = msg.hex() 
        return msg

    try:
        events_A, ticks_per_beat = extract_events(file_a)
        events_B, _ = extract_events(file_b)
        ticks_per_pulse = ticks_per_beat // 24 
        app.after(0, lambda: render_piano_roll(pr_events_A if current_playing_part == "A" else pr_events_B))

        with mido.open_output(out_port_name) as out_port:
            event_index, play_tick = 0, 0
            active_events = events_A if current_playing_part == "A" else events_B
            
            if sync_mode == "Internal":
                out_port.send(mido.Message('start'))
                while is_playing:
                    pulse_duration = 60.0 / (int(tempo_slider.get()) * 24)
                    start_time = time.perf_counter()
                    out_port.send(mido.Message('clock')) 
                    
                    if live_events_update:
                        for ch, note in active_notes: out_port.send(mido.Message('note_off', channel=ch, note=note, velocity=0))
                        active_notes.clear()
                        events_A, events_B = next_events_A, next_events_B
                        active_events = events_A if current_playing_part == "A" else events_B
                        play_tick = play_tick % (int(length_var.get().split()[0]) * 1920)
                        event_index = 0
                        while event_index < len(active_events) and active_events[event_index][0] <= play_tick: event_index += 1
                        app.after(0, lambda: render_piano_roll(pr_events_A if current_playing_part == "A" else pr_events_B))
                        live_events_update = False
                    
                    target_ticks = int(length_var.get().split()[0]) * 1920
                    while event_index < len(active_events) and active_events[event_index][0] <= play_tick:
                        processed_msg = process_message(active_events[event_index][1])
                        if processed_msg:
                            out_port.send(processed_msg)
                            if fs_enabled_var.get() and fs_instance:
                                try:
                                    if processed_msg.type == 'note_on':
                                        fs_instance.noteon(processed_msg.channel, processed_msg.note, processed_msg.velocity)
                                    elif processed_msg.type == 'note_off':
                                        fs_instance.noteoff(processed_msg.channel, processed_msg.note)
                                    elif processed_msg.type == 'control_change':
                                        fs_instance.cc(processed_msg.channel, processed_msg.control, processed_msg.value)
                                    elif processed_msg.type == 'program_change':
                                        fs_instance.program_change(processed_msg.channel, processed_msg.program)
                                    elif processed_msg.type == 'pitchwheel':
                                        fs_instance.pitch_bend(processed_msg.channel, processed_msg.pitch)
                                except: pass
                        event_index += 1

                    play_tick += ticks_per_pulse
                    current_play_tick = play_tick 
                    
                    if play_tick >= target_ticks:
                        while event_index < len(active_events) and active_events[event_index][0] <= target_ticks:
                            processed_msg = process_message(active_events[event_index][1])
                            if processed_msg:
                                out_port.send(processed_msg)
                                if fs_enabled_var.get() and fs_instance:
                                    try:
                                        if processed_msg.type == 'note_on':
                                            fs_instance.noteon(processed_msg.channel, processed_msg.note, processed_msg.velocity)
                                        elif processed_msg.type == 'note_off':
                                            fs_instance.noteoff(processed_msg.channel, processed_msg.note)
                                        elif processed_msg.type == 'control_change':
                                            fs_instance.cc(processed_msg.channel, processed_msg.control, processed_msg.value)
                                        elif processed_msg.type == 'program_change':
                                            fs_instance.program_change(processed_msg.channel, processed_msg.program)
                                        elif processed_msg.type == 'pitchwheel':
                                            fs_instance.pitch_bend(processed_msg.channel, processed_msg.pitch)
                                    except: pass
                            event_index += 1
                        if reload_staged:
                            events_A, _ = extract_events(file_a)
                            events_B, _ = extract_events(file_b)
                            reload_staged = False
                        if queued_part:
                            current_playing_part = queued_part
                            queued_part = None
                            update_status(f"PLAYING PART {current_playing_part}...", FG_COLOR)
                        active_events = events_B if current_playing_part == "B" else events_A
                        app.after(0, lambda: render_piano_roll(pr_events_A if current_playing_part == "A" else pr_events_B))
                        play_tick, current_play_tick, event_index = 0, 0, 0

                    target_time = start_time + pulse_duration
                    sleep_time = target_time - time.perf_counter() - 0.002
                    if sleep_time > 0: time.sleep(sleep_time)
                    while time.perf_counter() < target_time: pass

            elif sync_mode == "External":
                update_status("WAITING FOR SYNC...", "#FFC107")
                transport_playing, clock_count, last_beat_time = False, 0, time.time()
                with mido.open_input(in_port_name) as in_port:
                    for ext_msg in in_port:
                        if not is_playing: break 
                        if ext_msg.type == 'start':
                            transport_playing, play_tick, current_play_tick, event_index, clock_count, last_beat_time = True, 0, 0, 0, 0, time.time()
                            for ch, note in active_notes: out_port.send(mido.Message('note_off', channel=ch, note=note, velocity=0))
                            active_notes.clear()
                            update_status(f"SYNCED! PART {current_playing_part}", FG_COLOR)
                        elif ext_msg.type == 'continue':
                            transport_playing = True
                            update_status(f"SYNCED! PART {current_playing_part}", FG_COLOR)
                        elif ext_msg.type == 'stop':
                            transport_playing = False
                            update_status("EXT STOPPED - WAITING...", "#FFC107")
                            for ch, note in active_notes: out_port.send(mido.Message('note_off', channel=ch, note=note, velocity=0))
                            active_notes.clear()
                            app.after(0, lambda: ext_bpm_var.set("EXT BPM: ---"))
                        elif ext_msg.type == 'clock' and transport_playing:
                            clock_count += 1
                            if clock_count >= 24:
                                now = time.time()
                                try: app.after(0, lambda b=60.0/(now-last_beat_time): ext_bpm_var.set(f"EXT BPM: {int(b)}"))
                                except ZeroDivisionError: pass
                                last_beat_time, clock_count = now, 0
                            
                            if live_events_update:
                                for ch, note in active_notes: out_port.send(mido.Message('note_off', channel=ch, note=note, velocity=0))
                                active_notes.clear()
                                events_A, events_B = next_events_A, next_events_B
                                active_events = events_A if current_playing_part == "A" else events_B
                                target_ticks = int(length_var.get().split()[0]) * 1920
                                play_tick = play_tick % target_ticks 
                                event_index = 0
                                while event_index < len(active_events) and active_events[event_index][0] <= play_tick: event_index += 1
                                app.after(0, lambda: render_piano_roll(pr_events_A if current_playing_part == "A" else pr_events_B))
                                live_events_update = False
                                
                            target_ticks = int(length_var.get().split()[0]) * 1920
                            while event_index < len(active_events) and active_events[event_index][0] <= play_tick:
                                processed_msg = process_message(active_events[event_index][1])
                                if processed_msg:
                                    out_port.send(processed_msg)
                                    if fs_enabled_var.get() and fs_instance:
                                        try:
                                            if processed_msg.type == 'note_on':
                                                fs_instance.noteon(processed_msg.channel, processed_msg.note, processed_msg.velocity)
                                            elif processed_msg.type == 'note_off':
                                                fs_instance.noteoff(processed_msg.channel, processed_msg.note)
                                            elif processed_msg.type == 'control_change':
                                                fs_instance.cc(processed_msg.channel, processed_msg.control, processed_msg.value)
                                            elif processed_msg.type == 'program_change':
                                                fs_instance.program_change(processed_msg.channel, processed_msg.program)
                                            elif processed_msg.type == 'pitchwheel':
                                                fs_instance.pitch_bend(processed_msg.channel, processed_msg.pitch)
                                        except: pass
                                event_index += 1
                                
                            play_tick += ticks_per_pulse
                            current_play_tick = play_tick
                            if play_tick >= target_ticks:
                                while event_index < len(active_events) and active_events[event_index][0] <= target_ticks:
                                    processed_msg = process_message(active_events[event_index][1])
                                    if processed_msg:
                                        out_port.send(processed_msg)
                                        if fs_enabled_var.get() and fs_instance:
                                            try:
                                                if processed_msg.type == 'note_on':
                                                    fs_instance.noteon(processed_msg.channel, processed_msg.note, processed_msg.velocity)
                                                elif processed_msg.type == 'note_off':
                                                    fs_instance.noteoff(processed_msg.channel, processed_msg.note)
                                                elif processed_msg.type == 'control_change':
                                                    fs_instance.cc(processed_msg.channel, processed_msg.control, processed_msg.value)
                                                elif processed_msg.type == 'program_change':
                                                    fs_instance.program_change(processed_msg.channel, processed_msg.program)
                                                elif processed_msg.type == 'pitchwheel':
                                                    fs_instance.pitch_bend(processed_msg.channel, processed_msg.pitch)
                                            except: pass
                                    event_index += 1
                                if reload_staged:
                                    events_A, _ = extract_events(file_a)
                                    events_B, _ = extract_events(file_b)
                                    reload_staged = False
                                if queued_part:
                                    current_playing_part = queued_part
                                    queued_part = None
                                    update_status(f"SYNCED! PART {current_playing_part}", FG_COLOR)
                                active_events = events_B if current_playing_part == "B" else events_A
                                app.after(0, lambda: render_piano_roll(pr_events_A if current_playing_part == "A" else pr_events_B))
                                play_tick, current_play_tick, event_index = 0, 0, 0
            out_port.send(mido.Message('stop'))
            for ch in range(16): out_port.send(mido.Message('control_change', channel=ch, control=123, value=0)) 
    except Exception as e:
        app.after(0, lambda e_msg=e: messagebox.showerror("Sync Error", f"Playback failed:\n{e_msg}"))
        app.after(0, force_stop_state)

def play_action():
    global is_playing
    if is_playing: return 
    file_a, file_b, _ = get_temp_filenames()
    if not os.path.exists(file_a) or not os.path.exists(file_b):
        if not generate_action(force_new=False): return
    out_port, in_port, sync = midi_out_var.get(), midi_in_var.get(), sync_var.get()
    if not out_port or out_port == "No Output Devices":
        messagebox.showwarning("Warning", "Please select a MIDI Output Device.")
        sync_var.set("Internal"); return
    if sync == "External" and (not in_port or in_port == "No Input Devices"):
        messagebox.showwarning("Warning", "Please select a MIDI Input Device for External Sync.")
        sync_var.set("Internal"); return
    threading.Thread(target=play_live_thread, args=(file_a, file_b, out_port, in_port, sync), daemon=True).start()

def handle_spacebar(event):
    if is_playing: stop_playback()
    else: play_action()
    return "break"

def handle_keypress(event):
    if event.keysym in ['a', 'A']: queue_part("A")
    elif event.keysym in ['b', 'B']: queue_part("B")
        
def queue_part(part):
    global queued_part, current_playing_part, reload_staged
    if not is_playing: 
        current_playing_part = part
        update_status(f"STARTING FROM: PART {part}", "#FFC107")
        try:
            btn_part_a.config(bg=FG_COLOR if part == "A" else "#333333", fg="black" if part == "A" else FG_COLOR)
            btn_part_b.config(bg=FG_COLOR if part == "B" else "#333333", fg="black" if part == "B" else FG_COLOR)
        except: pass
        return
    queued_part, reload_staged = part, True 

def ui_blinker_loop():
    global blink_state
    if not is_playing:
        try:
            btn_part_a.config(bg=FG_COLOR if current_playing_part == "A" else "#333333", fg="black" if current_playing_part == "A" else FG_COLOR)
            btn_part_b.config(bg=FG_COLOR if current_playing_part == "B" else "#333333", fg="black" if current_playing_part == "B" else FG_COLOR)
        except: pass
        return
    blink_state = not blink_state
    try:
        if current_playing_part == "A": btn_part_a.config(bg=FG_COLOR, fg="black")
        elif queued_part == "A": btn_part_a.config(bg="#FFC107" if blink_state else "#333333", fg="black")
        else: btn_part_a.config(bg="#333333", fg=FG_COLOR)
        if current_playing_part == "B": btn_part_b.config(bg=FG_COLOR, fg="black")
        elif queued_part == "B": btn_part_b.config(bg="#FFC107" if blink_state else "#333333", fg="black")
        else: btn_part_b.config(bg="#333333", fg=FG_COLOR)
    except: pass
    if is_playing: app.after(300, ui_blinker_loop) 

def solo_flasher_loop():
    global blink_state
    if not is_playing:
        try:
            for btn in [btn_solo_mel, btn_solo_hrm, btn_solo_chd, btn_solo_bas]: btn.config(bg=SOLO_FLASH_OFF, fg="#FF0000")
        except: pass
        return
    flash_on = blink_state
    any_solos = solo_mel_var.get() or solo_hrm_var.get() or solo_chd_var.get() or solo_bas_var.get()
    try:
        c = SOLO_FLASH_ON if flash_on else "#772088" 
        btn_solo_mel.config(bg=c if solo_mel_var.get() else SOLO_FLASH_OFF)
        btn_solo_hrm.config(bg=c if solo_hrm_var.get() else SOLO_FLASH_OFF)
        btn_solo_chd.config(bg=c if solo_chd_var.get() else SOLO_FLASH_OFF)
        btn_solo_bas.config(bg=c if solo_bas_var.get() else SOLO_FLASH_OFF)
    except: pass
    if is_playing: app.after(400, solo_flasher_loop) 

def spawn_note_visual(note, channel):
    try:
        x = (note / 127.0) * target_width
        colors = {0: "#39FF14", 1: "#00FFFF", 2: "#9C27B0", 3: "#FFC107"} 
        rect_id = canvas.create_rectangle(x, -20, x+10, 0, fill=colors.get(channel, "#FFFFFF"), outline="")
        piano_roll_items.append({"id": rect_id, "y": -20, "speed": 10})
    except: pass

def update_visualizer():
    global latest_midi_hex
    while not ui_msg_queue.empty():
        msg_type, note, channel = ui_msg_queue.get()
        if msg_type == "note_on": spawn_note_visual(note, channel)
        
    for item in matrix_items:
        item["y"] += item["speed"]
        if item["y"] > target_height:
            item["y"], item["x"] = random.randint(-200, -50), random.randint(0, target_width)
        if random.random() > 0.85:
            if latest_midi_hex and random.random() > 0.5:
                char_str, latest_midi_hex = "\n".join([latest_midi_hex[i:i+2].upper() for i in range(0, len(latest_midi_hex), 2)]), ""
            else: char_str = "\n".join([hex(random.randint(0, 255))[2:].zfill(2).upper() for _ in range(8)])
            try: canvas.itemconfig(item["id"], text="00\nFF" if not char_str.strip() else char_str)
            except: pass
        try: canvas.coords(item["id"], item["x"], item["y"])
        except: pass
        
    for item in piano_roll_items[:]:
        item["y"] += item["speed"]
        try:
            canvas.coords(item["id"], canvas.coords(item["id"])[0], item["y"], canvas.coords(item["id"])[2], item["y"]+20)
            if item["y"] > 100: # Matched to new piano roll height
                canvas.delete(item["id"])
                piano_roll_items.remove(item)
        except: pass
            
    px = 30 + (current_play_tick / max(1, target_ticks_global)) * 690
    try: piano_roll_canvas.coords("playhead", px, 0, px, 100)
    except: pass
    app.after(80, update_visualizer) # 80ms to free up CPU for MIDI Engine

def draw_piano_keyboard():
    keyboard_canvas.delete("all")
    scale_name, root_idx = scale_var.get(), NOTES_LIST.index(root_var.get())
    if scale_name == "Custom (Use Keyboard)": active_keys = [i for i in range(12) if key_states[i].get()]
    else:
        active_keys = [(root_idx + iv) % 12 for iv in SCALE_INTERVALS[scale_name]]
        for i in range(12): key_states[i].set(i in active_keys)
        
    wk_width, wk_height, bk_width, bk_height = 40, 100, 24, 60
    white_keys, black_keys = [0, 2, 4, 5, 7, 9, 11], [1, 3, None, 6, 8, 10] 
    
    for i, note in enumerate(white_keys):
        x0 = i * wk_width
        keyboard_canvas.create_rectangle(x0, 0, x0 + wk_width, wk_height, fill="#EEEEEE", outline="#333333")
        keyboard_canvas.create_text(x0 + wk_width/2, wk_height - 15, text=NOTES_LIST[note], font=("Arial", 8, "bold"), fill="#000000")
        if note in active_keys: keyboard_canvas.create_oval(x0 + wk_width/2 - 5, wk_height - 35, x0 + wk_width/2 + 5, wk_height - 25, fill="#FF0000", outline="#FF0000")
            
    for i, note in enumerate(black_keys):
        if note is None: continue
        x0 = (i * wk_width) + (wk_width - bk_width/2)
        keyboard_canvas.create_rectangle(x0, 0, x0 + bk_width, bk_height, fill="#222222", outline="#000000")
        if note in active_keys: keyboard_canvas.create_oval(x0 + bk_width/2 - 4, bk_height - 15, x0 + bk_width/2 + 4, bk_height - 7, fill="#FF0000", outline="#FF0000")

def toggle_key(event):
    if scale_var.get() != "Custom (Use Keyboard)": return
    x, y, wk_width, bk_width, bk_height, clicked_note = event.x, event.y, 40, 24, 60, -1
    if y <= bk_height:
        for note, pos in {1: 1, 3: 2, 6: 4, 8: 5, 10: 6}.items():
            cx = (pos-1)*wk_width + (wk_width - bk_width/2)
            if cx <= x <= cx + bk_width: clicked_note = note; break
    if clicked_note == -1: clicked_note = [0, 2, 4, 5, 7, 9, 11][min(x // wk_width, 6)]
    if clicked_note != -1:
        key_states[clicked_note].set(not key_states[clicked_note].get())
        draw_piano_keyboard(); trigger_auto_generate()

def toggle_solo(var, btn):
    var.set(not var.get())
    btn.config(relief="sunken" if var.get() else "raised")
    if solo_mel_var.get() and solo_hrm_var.get() and solo_chd_var.get() and solo_bas_var.get():
        for v in [solo_mel_var, solo_hrm_var, solo_chd_var, solo_bas_var]: v.set(False)
        for b in [btn_solo_mel, btn_solo_hrm, btn_solo_chd, btn_solo_bas]: b.config(relief="raised")

def toggle_mute(var, btn):
    var.set(not var.get())
    btn.config(bg="#F44336" if var.get() else "#555555", relief="sunken" if var.get() else "raised")

def on_bass_pat_change(*args):
    bass_rhythm_dropdown.config(state="readonly" if bass_pat_var.get() == "Regular" else "disabled")
    trigger_auto_generate()

def on_chord_style_change(*args):
    if chord_style_var.get() == "Digitone Shapes": digitone_shape_dropdown.pack(side="left", padx=5, after=chord_style_dropdown)
    else: digitone_shape_dropdown.pack_forget()
    trigger_auto_generate()

def on_composer_change(*args):
    try: ascii_label.config(text=ASCII_ART.get(style_var.get(), ASCII_ART["default"]))
    except NameError: pass
    trigger_auto_generate()

def trigger_auto_generate(part=None, *args):
    if workflow_var.get() == "Staged" and part is None: return 
    global gen_timer
    if gen_timer is not None: app.after_cancel(gen_timer)
    gen_timer = app.after(150, lambda: generate_action(force_new=False, part=part)) 

def randomize_params():
    style_var.set(random.choice(list(COMPOSER_PROBABILITIES.keys())))
    algo_var.set(random.choice(["Markov Chain", "Brownian Motion", "Ostinato Motif", "Arpeggiator"]))
    root_var.set(random.choice(NOTES_LIST))
    scale_var.set(random.choice(["Major (Ionian)", "Minor (Aeolian)", "Dorian", "Phrygian", "Mixolydian", "Harmonic Minor", "Pentatonic Min"]))
    complexity_slider.set(random.randint(1, 5))
    length_var.set(random.choice(["1 Bar", "2 Bars", "4 Bars"]))
    chord_style_var.set(random.choice(["Off", "Diatonic Triads", "Diatonic 7ths", "Sus2 / Sus4", "Digitone Shapes"]))
    if chord_style_var.get() == "Digitone Shapes": digitone_shape_var.set(random.choice(list(DIGITONE_SHAPES.keys())))
    chord_rhythm_var.set(random.choice(["Whole Notes", "Half Notes", "Quarter Notes", "Eighth Notes", "Offbeats", "Syncopated"]))
    chord_oct_var.set(random.choice(["+1", "0", "-1"]))
    chord_gate_slider.set(random.randint(20, 100)); mel_gate_slider.set(random.randint(20, 100)); hrm_gate_slider.set(random.randint(20, 100)); bas_gate_slider.set(random.randint(20, 100))
    bass_pat_var.set(random.choice(["Regular", "Dub 1", "Dub 2", "Dub 3", "Rock 1", "Rock 2", "Pop 1", "Pop 2", "Funk 1", "Synthwave", "Disco", "Latin"]))
    bass_comp_slider.set(random.randint(1, 5))
    bass_rhythm_var.set(random.choice(["Whole Note", "8th Notes", "16th Notes"]))
    harm_var.set(random.choice([True, False]))
    vel_slider.set(random.randint(5, 30)); feel_slider.set(random.randint(0, 60)); strum_slider.set(random.randint(0, 10))
    draw_piano_keyboard(); generate_action(force_new=True) 

def get_temp_filenames():
    base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "temp_A.mid"), os.path.join(base, "temp_B.mid"), os.path.join(base, "temp_full.mid")

def generate_action(force_new=True, part=None):
    global next_events_A, next_events_B, live_events_update, target_ticks_global, pr_events_A, pr_events_B
    global seed_mel, seed_hrm, seed_chd, seed_bas, seed_prog
    
    scale_type, root_name = scale_var.get(), root_var.get()
    if scale_type == "Custom (Use Keyboard)" and not any(var.get() for var in key_states.values()): return False

    if force_new or (not lock_notes_var.get() and part is None):
        t = time.time(); seed_mel, seed_hrm, seed_chd, seed_bas, seed_prog = t, t+1, t+2, t+3, t+4
    elif part == "mel": seed_mel = time.time()
    elif part == "hrm": seed_hrm = time.time()
    elif part == "chd": seed_chd = time.time()
    elif part == "bas": seed_bas = time.time()

    rng_mel_A, rng_mel_B = random.Random(seed_mel), random.Random(seed_mel + 100)
    rng_hrm_A, rng_hrm_B = random.Random(seed_hrm), random.Random(seed_hrm + 100)
    rng_chd_A, rng_chd_B = random.Random(seed_chd), random.Random(seed_chd + 100)
    rng_bas_A, rng_bas_B = random.Random(seed_bas), random.Random(seed_bas + 100)
    rng_prog_A, rng_prog_B = random.Random(seed_prog), random.Random(seed_prog + 100)

    notes = get_scale_notes(root_name, scale_type)
    bars = int(length_var.get().split()[0])
    target_ticks_global = bars * 1920
    
    file_a, file_b, file_full = get_temp_filenames()
    undo_a, undo_b, undo_full = file_a.replace(".mid", "_undo.mid"), file_b.replace(".mid", "_undo.mid"), file_full.replace(".mid", "_undo.mid")
    if os.path.exists(file_a): shutil.copy2(file_a, undo_a); shutil.copy2(file_b, undo_b); shutil.copy2(file_full, undo_full)

    vel_amt, feel_amt, strum_amt, oct_shift = int(vel_slider.get()), int(feel_slider.get()), int(strum_slider.get()), int(chord_oct_var.get())
    mel_gate_pct, hrm_gate_pct, chd_gate_pct, bas_gate_pct = int(mel_gate_slider.get()), int(hrm_gate_slider.get()), int(chord_gate_slider.get()), int(bas_gate_slider.get())
    
    prog_dur = 1920 
    prog_A = generate_chord_progression(target_ticks_global, prog_dur, len(notes), rng_prog_A)
    prog_B = generate_chord_progression(target_ticks_global, prog_dur, len(notes), rng_prog_B)

    melody_A = generate_single_section(notes, style_var.get(), algo_var.get(), complexity_slider.get(), vel_amt, target_ticks_global, False, rng_mel_A, prog_A, mel_gate_pct)
    melody_B = generate_single_section(notes, style_var.get(), algo_var.get(), complexity_slider.get(), vel_amt, target_ticks_global, True, rng_mel_B, prog_B, mel_gate_pct)
    
    harmony_A = generate_relational_harmony(melody_A, notes, vel_amt, feel_amt, rng_hrm_A, harm_var.get(), hrm_gate_pct)
    harmony_B = generate_relational_harmony(melody_B, notes, vel_amt, feel_amt, rng_hrm_B, harm_var.get(), hrm_gate_pct)
        
    if chord_style_var.get() != "Off":
        chord_A = generate_chords_from_map(prog_A, notes, vel_amt, strum_amt, chord_style_var.get(), digitone_shape_var.get(), oct_shift, chord_rhythm_var.get(), chd_gate_pct, rng_chd_A)
        chord_B = generate_chords_from_map(prog_B, notes, vel_amt, strum_amt, chord_style_var.get(), digitone_shape_var.get(), oct_shift, chord_rhythm_var.get(), chd_gate_pct, rng_chd_B)
    else: chord_A, chord_B = [], []

    if bass_pat_var.get() != "Off":
        bass_A = generate_bassline_from_map(prog_A, notes, target_ticks_global, vel_amt, bass_rhythm_var.get(), bass_pat_var.get(), bass_comp_slider.get(), rng_bas_A, bas_gate_pct)
        bass_B = generate_bassline_from_map(prog_B, notes, target_ticks_global, vel_amt, bass_rhythm_var.get(), bass_pat_var.get(), bass_comp_slider.get(), rng_bas_B, bas_gate_pct)
    else: bass_A, bass_B = [], []
    
    create_midi(file_a, notes, melody_A, harmony_A, chord_A, bass_A, int(tempo_slider.get()))
    create_midi(file_b, notes, melody_B, harmony_B, chord_B, bass_B, int(tempo_slider.get()))
    
    full_melody = melody_A + [(idx, dur, vel, off, g) for idx, dur, vel, off, g in melody_B]
    full_harmony = harmony_A + [(val, dur, vel, off, g) for val, dur, vel, off, g in harmony_B]
    full_chord = chord_A + [(c, dur, vel, off, g) for c, dur, vel, off, g in chord_B]
    full_bass = bass_A + [(idx, dur, vel, off, g) for idx, dur, vel, off, g in bass_B]
    create_midi(file_full, notes, full_melody, full_harmony, full_chord, full_bass, int(tempo_slider.get()))
    
    ev_a, _ = extract_events(file_a); ev_b, _ = extract_events(file_b)
    pr_events_A, pr_events_B = parse_for_piano_roll(ev_a), parse_for_piano_roll(ev_b)
    
    if is_playing: 
        if workflow_var.get() == "Instant":
            next_events_A, next_events_B, live_events_update = ev_a, ev_b, True
            update_status("HOT-SWAPPED!", FG_COLOR)
        else: update_status("NEW SEQ STAGED! LAUNCH TO PLAY", "#FFC107")
    else: 
        update_status(f"NEW {bars}-BAR SEQ READY", FG_COLOR)
        app.after(0, lambda: render_piano_roll(pr_events_A if current_playing_part == "A" else pr_events_B))
    return True

def undo_action():
    global next_events_A, next_events_B, live_events_update, pr_events_A, pr_events_B
    file_a, file_b, file_full = get_temp_filenames()
    undo_a, undo_b, undo_full = file_a.replace(".mid", "_undo.mid"), file_b.replace(".mid", "_undo.mid"), file_full.replace(".mid", "_undo.mid")
    if os.path.exists(undo_a):
        shutil.copy2(undo_a, file_a); shutil.copy2(undo_b, file_b); shutil.copy2(undo_full, file_full)
        ev_a, _ = extract_events(file_a); ev_b, _ = extract_events(file_b)
        pr_events_A, pr_events_B = parse_for_piano_roll(ev_a), parse_for_piano_roll(ev_b)
        if is_playing: 
            if workflow_var.get() == "Instant":
                next_events_A, next_events_B, live_events_update = ev_a, ev_b, True
                update_status("UNDO HOT-SWAPPED!", FG_COLOR)
            else: update_status("UNDO STAGED! LAUNCH TO PLAY", "#FFC107")
        else: 
            update_status("UNDO SUCCESSFUL", FG_COLOR)
            app.after(0, lambda: render_piano_roll(pr_events_A if current_playing_part == "A" else pr_events_B))
    else: update_status("NOTHING TO UNDO", "#FF0000")

def save_action():
    _, _, temp_full = get_temp_filenames()
    if not os.path.exists(temp_full):
        if not generate_action(): return
    filename = f"{style_var.get().split()[0].replace('.', '')}_{root_var.get()}_{scale_var.get()[:3]}_Full.mid"
    try:
        shutil.copy2(temp_full, os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), filename))
        messagebox.showinfo("Success", f"MIDI Masterpiece saved as:\n{filename}")
    except Exception as e: messagebox.showerror("Error", f"Failed to save file: {e}")

def refresh_midi_ports():
    try:
        outs, ins = mido.get_output_names() or ["No Output Devices"], mido.get_input_names() or ["No Input Devices"]
        midi_out_dropdown['values'], midi_in_dropdown['values'] = outs, ins
        midi_out_var.set(outs[0]); midi_in_var.set(ins[0])
    except Exception as e:
        midi_out_dropdown['values'] = midi_in_dropdown['values'] = ["Backend Error"]
        midi_out_var.set("Backend Error"); midi_in_var.set("Backend Error")
        messagebox.showerror("MIDI Error", f"Could not connect to MIDI drivers:\n{e}")

def on_sync_change(*args):
    was_playing = is_playing
    if was_playing:
        stop_playback()
        if sync_var.get() == "External": app.after(500, play_action) 
    else:
        if sync_var.get() == "External": play_action()

def on_closing():
    global is_playing, fs_instance
    is_playing = False

    save_settings()
    panic_action()
    if fs_instance:
        try:
            fs_instance.delete()
            fs_instance = None
        except: pass
    app.after(500, app.destroy)

def init_fluidsynth():
    global fs_instance, fs_sfids
    if not FLUIDSYNTH_AVAILABLE:
        messagebox.showerror("FluidSynth Error", "pyfluidsynth not installed")
        fs_enabled_var.set(False)
        return
    
    try:
        if fs_instance:
            fs_instance.delete()
        
        fs_instance = fluidsynth.Synth()
        driver = 'coreaudio' if sys.platform == 'darwin' else ('dsound' if sys.platform == 'win32' else 'alsa')
        fs_instance.start(driver=driver)
        
        fs_sfids = [None] * 4
        any_loaded = False
        for i in range(4):
            path = sf_path_vars[i].get()
            if os.path.exists(path):
                sfid = fs_instance.sfload(path)
                fs_sfids[i] = sfid
                # Map internal channel i to this soundfont
                # Note: internal channels 0, 1, 2, 3 correspond to Mel, Hrm, Chd, Bas
                fs_instance.program_select(i, sfid, 0, 0)
                any_loaded = True
        
        if any_loaded:
            update_status("FLUIDSYNTH READY", FG_COLOR)
        else:
            update_status("FLUIDSYNTH: NO SOUNDFONTS LOADED", "#FFC107")

    except Exception as e:
        messagebox.showerror("FluidSynth Error", f"Failed to initialize: {e}")
        fs_enabled_var.set(False)
        fs_instance = None

def select_soundfont(idx):
    path = filedialog.askopenfilename(filetypes=[("SoundFont files", "*.sf2")])
    if path:
        sf_path_vars[idx].set(path)
        if fs_enabled_var.get():
            init_fluidsynth()

def toggle_fluidsynth():
    if fs_enabled_var.get():
        init_fluidsynth()
    else:
        global fs_instance
        if fs_instance:
            fs_instance.delete()
            fs_instance = None
            update_status("FLUIDSYNTH DISABLED", "#FFC107")

# ==========================================
# PHASE 5: UI WIDGET ASSEMBLY (TWO COLUMN)
# ==========================================
top_frame = tk.Frame(main_frame, bg=BG_COLOR)
top_frame.pack(fill="x", pady=(0, 5))
ascii_label = tk.Label(top_frame, text="", bg=BG_COLOR, fg=FG_COLOR, font=FONT_ASCII, justify="left")
ascii_label.pack(side="right", padx=10)
tk.Label(top_frame, text="the passenger's midi generator", bg=BG_COLOR, fg="#FFC107", font=("Arial", 16, "bold")).pack(anchor="w", pady=(5,0))
tk.Label(top_frame, text="v4.0 algorithmic sequencer", bg=BG_COLOR, fg=FG_COLOR, font=("Arial", 10)).pack(anchor="w")

# Two Column Rack Layout
content_frame = tk.Frame(main_frame, bg=BG_COLOR)
content_frame.pack(fill="x", pady=5)

col_left = tk.Frame(content_frame, bg=BG_COLOR)
col_left.pack(side="left", fill="y", expand=True, padx=(0, 10))

col_right = tk.Frame(content_frame, bg=BG_COLOR)
col_right.pack(side="right", fill="y", expand=True, padx=(10, 0))

# --- LEFT COLUMN: GLOBAL & MELODY ---
global_frame = tk.LabelFrame(col_left, text=" GLOBAL SETTINGS ", bg=BG_COLOR, fg=FG_COLOR, font=FONT_TITLE, padx=10, pady=10)
global_frame.pack(fill="x", pady=5)
gf_r1 = tk.Frame(global_frame, bg=BG_COLOR); gf_r1.pack(fill="x", pady=2)
make_label(gf_r1, text="COMPOSER:").pack(side="left")
ttk.Combobox(gf_r1, textvariable=style_var, values=list(COMPOSER_PROBABILITIES.keys()), state="readonly", width=25, height=20, font=FONT_MAIN).pack(side="left", padx=5)
make_label(gf_r1, text="ROOT:").pack(side="left")
ttk.Combobox(gf_r1, textvariable=root_var, values=NOTES_LIST, width=4, height=20, state="readonly", font=FONT_MAIN).pack(side="left", padx=5)
make_label(gf_r1, text="SCALE:").pack(side="left")
ttk.Combobox(gf_r1, textvariable=scale_var, values=list(SCALE_INTERVALS.keys()), width=18, height=20, state="readonly", font=FONT_MAIN).pack(side="left", padx=5)

gf_r2 = tk.Frame(global_frame, bg=BG_COLOR); gf_r2.pack(fill="x", pady=2)
make_label(gf_r2, text="TEMPO:").pack(side="left")
tempo_slider = tk.Scale(gf_r2, from_=40, to=200, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=100)
tempo_slider.set(100); tempo_slider.pack(side="left", padx=5)
make_label(gf_r2, text="LENGTH:").pack(side="left")
ttk.Combobox(gf_r2, textvariable=length_var, values=["1 Bar", "2 Bars", "4 Bars", "8 Bars", "16 Bars"], state="readonly", width=6, height=20, font=FONT_MAIN).pack(side="left", padx=5)
make_label(gf_r2, text="ALG:").pack(side="left")
ttk.Combobox(gf_r2, textvariable=algo_var, values=["Markov Chain", "Brownian Motion", "Ostinato Motif", "Arpeggiator"], state="readonly", width=12, height=20, font=FONT_MAIN).pack(side="left", padx=5)
make_label(gf_r2, text="VOLATILITY:").pack(side="left")
complexity_slider = tk.Scale(gf_r2, from_=1, to=5, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=80)
complexity_slider.set(2); complexity_slider.pack(side="left", padx=5)

keyboard_container = tk.Frame(global_frame, bg=BG_COLOR)
keyboard_container.pack(pady=5)
keyboard_canvas = tk.Canvas(keyboard_container, width=280, height=100, bg=BG_COLOR, highlightthickness=0)
keyboard_canvas.pack(); keyboard_canvas.bind("<Button-1>", toggle_key)

mel_frame = tk.LabelFrame(col_left, text=" MELODY & HARMONY ", bg=BG_COLOR, fg=FG_COLOR, font=FONT_TITLE, padx=10, pady=10)
mel_frame.pack(fill="x", pady=5)
mf_r1 = tk.Frame(mel_frame, bg=BG_COLOR); mf_r1.pack(fill="x", pady=2)
frame_mel = tk.Frame(mf_r1, bg=MUTE_BG, padx=4, pady=4); frame_mel.pack(side="left", padx=5)
make_label(frame_mel, text="MEL CH:").pack(side="left")
ttk.Combobox(frame_mel, textvariable=melody_ch_var, values=[str(i) for i in range(1, 17)], width=2, state="readonly", height=20, font=FONT_MAIN).pack(side="left", padx=2)
btn_mute_mel = tk.Button(frame_mel, text="M", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_mute(mute_mel_var, btn_mute_mel))
btn_mute_mel.pack(side="left", padx=2)
btn_solo_mel = tk.Button(frame_mel, text="S", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_solo(solo_mel_var, btn_solo_mel))
btn_solo_mel.pack(side="left", padx=2)

frame_hrm = tk.Frame(mf_r1, bg=MUTE_BG, padx=4, pady=4); frame_hrm.pack(side="left", padx=5)
make_label(frame_hrm, text="HRM CH:").pack(side="left")
ttk.Combobox(frame_hrm, textvariable=harmony_ch_var, values=[str(i) for i in range(1, 17)], width=2, state="readonly", height=20, font=FONT_MAIN).pack(side="left", padx=2)
btn_mute_hrm = tk.Button(frame_hrm, text="M", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_mute(mute_hrm_var, btn_mute_hrm))
btn_mute_hrm.pack(side="left", padx=2)
btn_solo_hrm = tk.Button(frame_hrm, text="S", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_solo(solo_hrm_var, btn_solo_hrm))
btn_solo_hrm.pack(side="left", padx=2)

tk.Button(mf_r1, text="GEN MEL", bg="#2196F3", fg="white", font=FONT_ASCII, relief="flat", takefocus=0, command=lambda: trigger_auto_generate("mel")).pack(side="right", padx=2)
tk.Button(mf_r1, text="GEN HRM", bg="#2196F3", fg="white", font=FONT_ASCII, relief="flat", takefocus=0, command=lambda: trigger_auto_generate("hrm")).pack(side="right", padx=2)

mf_r2 = tk.Frame(mel_frame, bg=BG_COLOR); mf_r2.pack(fill="x", pady=2)
tk.Checkbutton(mf_r2, text="SPARSE HARMONY", variable=harm_var, bg=BG_COLOR, fg=FG_COLOR, selectcolor="black", font=FONT_MAIN, takefocus=0).pack(side="left", padx=5)
make_label(mf_r2, text="VEL VAR:").pack(side="left")
vel_slider = tk.Scale(mf_r2, from_=0, to=40, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=80)
vel_slider.set(15); vel_slider.pack(side="left", padx=5)
make_label(mf_r2, text="HRM LAG:").pack(side="left")
feel_slider = tk.Scale(mf_r2, from_=0, to=120, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=80)
feel_slider.set(5); feel_slider.pack(side="left", padx=5)

mf_r3 = tk.Frame(mel_frame, bg=BG_COLOR); mf_r3.pack(fill="x", pady=2)
make_label(mf_r3, text="MEL GATE %:").pack(side="left")
mel_gate_slider = tk.Scale(mf_r3, from_=10, to=100, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=100)
mel_gate_slider.set(100); mel_gate_slider.pack(side="left", padx=5)
make_label(mf_r3, text="HRM GATE %:").pack(side="left")
hrm_gate_slider = tk.Scale(mf_r3, from_=10, to=100, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=100)
hrm_gate_slider.set(100); hrm_gate_slider.pack(side="left", padx=5)

# --- RIGHT COLUMN: CHORDS & BASS ---
chd_frame = tk.LabelFrame(col_right, text=" CHORDS ", bg=BG_COLOR, fg=FG_COLOR, font=FONT_TITLE, padx=10, pady=10)
chd_frame.pack(fill="x", pady=5)
cf_r1 = tk.Frame(chd_frame, bg=BG_COLOR); cf_r1.pack(fill="x", pady=2)
frame_chd_mix = tk.Frame(cf_r1, bg=MUTE_BG, padx=4, pady=4); frame_chd_mix.pack(side="left", padx=5)
make_label(frame_chd_mix, text="CHORD CH:").pack(side="left")
ttk.Combobox(frame_chd_mix, textvariable=chord_ch_var, values=[str(i) for i in range(1, 17)], width=2, state="readonly", height=20, font=FONT_MAIN).pack(side="left", padx=2)
btn_mute_chd = tk.Button(frame_chd_mix, text="M", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_mute(mute_chd_var, btn_mute_chd))
btn_mute_chd.pack(side="left", padx=2)
btn_solo_chd = tk.Button(frame_chd_mix, text="S", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_solo(solo_chd_var, btn_solo_chd))
btn_solo_chd.pack(side="left", padx=2)

make_label(cf_r1, text="STYLE:").pack(side="left")
chord_style_dropdown = ttk.Combobox(cf_r1, textvariable=chord_style_var, values=["Off", "Diatonic Triads", "Diatonic 7ths", "Sus2 / Sus4", "Digitone Shapes"], state="readonly", width=14, height=20, font=FONT_MAIN)
chord_style_dropdown.pack(side="left", padx=5)
digitone_shape_dropdown = ttk.Combobox(cf_r1, textvariable=digitone_shape_var, values=list(DIGITONE_SHAPES.keys()), state="readonly", width=6, height=20, font=FONT_MAIN)
tk.Button(cf_r1, text="GEN CHD", bg="#2196F3", fg="white", font=FONT_ASCII, relief="flat", takefocus=0, command=lambda: trigger_auto_generate("chd")).pack(side="right", padx=2)

cf_r2 = tk.Frame(chd_frame, bg=BG_COLOR); cf_r2.pack(fill="x", pady=2)
make_label(cf_r2, text="RHYTHM:").pack(side="left")
chord_rhythm_dropdown = ttk.Combobox(cf_r2, textvariable=chord_rhythm_var, values=["Whole Notes", "Half Notes", "Quarter Notes", "Eighth Notes", "Offbeats", "Syncopated"], state="readonly", width=12, height=20, font=FONT_MAIN)
chord_rhythm_dropdown.pack(side="left", padx=5)
chord_oct_label = make_label(cf_r2, text="OCT:")
chord_oct_label.pack(side="left")
chord_oct_dropdown = ttk.Combobox(cf_r2, textvariable=chord_oct_var, values=["+1", "0", "-1"], state="readonly", width=3, height=20, font=FONT_MAIN)
chord_oct_dropdown.pack(side="left", padx=5)
make_label(cf_r2, text="STRUM:").pack(side="left")
strum_slider = tk.Scale(cf_r2, from_=0, to=20, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=80)
strum_slider.set(5); strum_slider.pack(side="left", padx=5)
make_label(cf_r2, text="GATE %:").pack(side="left")
chord_gate_slider = tk.Scale(cf_r2, from_=10, to=100, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=80)
chord_gate_slider.set(100); chord_gate_slider.pack(side="left", padx=5)

bas_frame = tk.LabelFrame(col_right, text=" BASS ", bg=BG_COLOR, fg=FG_COLOR, font=FONT_TITLE, padx=10, pady=10)
bas_frame.pack(fill="x", pady=5)
bf_r1 = tk.Frame(bas_frame, bg=BG_COLOR); bf_r1.pack(fill="x", pady=2)
frame_bas_mix = tk.Frame(bf_r1, bg=MUTE_BG, padx=4, pady=4); frame_bas_mix.pack(side="left", padx=5)
make_label(frame_bas_mix, text="BASS CH:").pack(side="left")
ttk.Combobox(frame_bas_mix, textvariable=bass_ch_var, values=[str(i) for i in range(1, 17)], width=2, state="readonly", height=20, font=FONT_MAIN).pack(side="left", padx=2)
btn_mute_bas = tk.Button(frame_bas_mix, text="M", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_mute(mute_bas_var, btn_mute_bas))
btn_mute_bas.pack(side="left", padx=2)
btn_solo_bas = tk.Button(frame_bas_mix, text="S", bg="#555555", fg="white", font=FONT_ASCII, width=2, relief="raised", takefocus=0, command=lambda: toggle_solo(solo_bas_var, btn_solo_bas))
btn_solo_bas.pack(side="left", padx=2)

make_label(bf_r1, text="PAT:").pack(side="left")
ttk.Combobox(bf_r1, textvariable=bass_pat_var, values=["Off", "Regular", "Dub 1", "Dub 2", "Dub 3", "Rock 1", "Rock 2", "Pop 1", "Pop 2", "Funk 1", "Synthwave", "Disco", "Latin"], state="readonly", width=10, height=20, font=FONT_MAIN).pack(side="left", padx=5)
make_label(bf_r1, text="RHYTHM:").pack(side="left")
bass_rhythm_dropdown = ttk.Combobox(bf_r1, textvariable=bass_rhythm_var, values=["Whole Note", "8th Notes", "16th Notes"], state="readonly", width=10, height=20, font=FONT_MAIN)
bass_rhythm_dropdown.pack(side="left", padx=5)
tk.Button(bf_r1, text="GEN BASS", bg="#2196F3", fg="white", font=FONT_ASCII, relief="flat", takefocus=0, command=lambda: trigger_auto_generate("bas")).pack(side="right", padx=2)

bf_r2 = tk.Frame(bas_frame, bg=BG_COLOR); bf_r2.pack(fill="x", pady=2)
make_label(bf_r2, text="COMPLEXITY:").pack(side="left")
bass_comp_slider = tk.Scale(bf_r2, from_=1, to=5, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=120)
bass_comp_slider.set(2); bass_comp_slider.pack(side="left", padx=5)
make_label(bf_r2, text="BSS GATE %:").pack(side="left")
bas_gate_slider = tk.Scale(bf_r2, from_=10, to=100, orient="horizontal", bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, font=FONT_MAIN, takefocus=0, length=120)
bas_gate_slider.set(100); bas_gate_slider.pack(side="left", padx=5)

sync_routing_frame = tk.Frame(col_right, bg=BG_COLOR)
sync_routing_frame.pack(fill="x", pady=5)
make_label(sync_routing_frame, text="MIDI OUT:").grid(row=0, column=0, sticky="w", pady=2)
midi_out_dropdown = ttk.Combobox(sync_routing_frame, textvariable=midi_out_var, state="readonly", width=18, height=20, font=FONT_MAIN)
midi_out_dropdown.grid(row=0, column=1, padx=5, pady=2)
make_label(sync_routing_frame, text="MIDI IN:").grid(row=1, column=0, sticky="w", pady=2)
midi_in_dropdown = ttk.Combobox(sync_routing_frame, textvariable=midi_in_var, state="readonly", width=18, height=20, font=FONT_MAIN)
midi_in_dropdown.grid(row=1, column=1, padx=5, pady=2)
tk.Button(sync_routing_frame, text="REFRESH", command=refresh_midi_ports, bg="#333333", fg=FG_COLOR, font=FONT_MAIN, relief="flat", takefocus=0).grid(row=0, column=2, rowspan=2, padx=10)

tk.Radiobutton(sync_routing_frame, text="INTERNAL CLOCK", variable=sync_var, value="Internal", bg=BG_COLOR, fg=FG_COLOR, selectcolor="black", font=FONT_MAIN, takefocus=0).grid(row=0, column=3, sticky="w", padx=10)
tk.Radiobutton(sync_routing_frame, text="EXTERNAL CLOCK", variable=sync_var, value="External", bg=BG_COLOR, fg=FG_COLOR, selectcolor="black", font=FONT_MAIN, takefocus=0).grid(row=1, column=3, sticky="w", padx=10)
tk.Label(sync_routing_frame, textvariable=ext_bpm_var, bg=BG_COLOR, fg="#FFC107", font=FONT_MAIN).grid(row=1, column=4, sticky="w")

fs_frame = tk.LabelFrame(main_frame, text=" FLUIDSYNTH MULTI-SOUNDFONT ", bg=BG_COLOR, fg="#00FFFF", font=FONT_TITLE, padx=10, pady=5)
fs_frame.pack(fill="x", pady=5)
fs_top = tk.Frame(fs_frame, bg=BG_COLOR); fs_top.pack(fill="x")
tk.Checkbutton(fs_top, text="ENABLE FLUIDSYNTH", variable=fs_enabled_var, command=toggle_fluidsynth, bg=BG_COLOR, fg="#00FFFF", selectcolor="black", font=FONT_MAIN, takefocus=0).pack(side="left")

fs_grid = tk.Frame(fs_frame, bg=BG_COLOR); fs_grid.pack(fill="x", pady=5)
labels = ["MEL SF2:", "HRM SF2:", "CHD SF2:", "BAS SF2:"]
for i in range(4):
    row = i // 2
    col = i % 2
    f = tk.Frame(fs_grid, bg=BG_COLOR); f.grid(row=row, column=col, sticky="w", padx=10, pady=2)
    make_label(f, text=labels[i], width=8, anchor="w").pack(side="left")
    tk.Entry(f, textvariable=sf_path_vars[i], font=FONT_MAIN, bg="#222222", fg="white", width=40).pack(side="left", padx=5)
    tk.Button(f, text="...", command=lambda idx=i: select_soundfont(idx), bg="#444444", fg="white", font=FONT_MAIN, relief="flat", takefocus=0).pack(side="left")

# --- FOOTER: PLAYBACK & PIANO ROLL ---
piano_roll_frame = tk.Frame(main_frame, bg="#111111", bd=2, relief="sunken", padx=2, pady=2)
piano_roll_frame.pack(pady=(10, 5))
piano_roll_canvas = tk.Canvas(piano_roll_frame, width=720, height=100, bg="#050505", highlightthickness=0)
piano_roll_canvas.pack()

button_frame = tk.Frame(main_frame, bg=BG_COLOR)
button_frame.pack(fill="x", pady=5)
wf_frame = tk.Frame(button_frame, bg=BG_COLOR); wf_frame.pack(fill="x", pady=2)
make_label(wf_frame, text="WORKFLOW MODE:").pack(side="left")
tk.Radiobutton(wf_frame, text="INSTANT HOT-SWAP", variable=workflow_var, value="Instant", bg=BG_COLOR, fg=FG_COLOR, selectcolor="black", font=FONT_ASCII, takefocus=0).pack(side="left", padx=5)
tk.Radiobutton(wf_frame, text="STAGED LAUNCH", variable=workflow_var, value="Staged", bg=BG_COLOR, fg=FG_COLOR, selectcolor="black", font=FONT_ASCII, takefocus=0).pack(side="left", padx=5)
tk.Checkbutton(wf_frame, text="LOCK NOTES (FX ONLY)", variable=lock_notes_var, bg=BG_COLOR, fg="#FFC107", selectcolor="black", font=FONT_MAIN, takefocus=0).pack(side="right")

row1 = tk.Frame(button_frame, bg=BG_COLOR); row1.pack(fill="x", pady=2)
tk.Button(row1, text="GEN NEW ALL", command=lambda: generate_action(force_new=True), bg="#2196F3", fg="white", font=FONT_MAIN, width=12, relief="flat", takefocus=0).pack(side="left", padx=(0, 10))
tk.Button(row1, text="UNDO", command=undo_action, bg="#FF9800", fg="black", font=FONT_MAIN, width=8, relief="flat", takefocus=0).pack(side="left", padx=10)
tk.Button(row1, text="RANDOMIZE", command=randomize_params, bg="#9C27B0", fg="white", font=FONT_MAIN, width=12, relief="flat", takefocus=0).pack(side="left", padx=10)
tk.Button(row1, text="SAVE", command=save_action, bg="#333333", fg=FG_COLOR, font=FONT_MAIN, width=8, relief="flat", takefocus=0).pack(side="right")

row2 = tk.Frame(button_frame, bg=BG_COLOR); row2.pack(fill="x", pady=5)
btn_part_a = tk.Button(row2, text="LAUNCH [A]", command=lambda: queue_part("A"), bg=FG_COLOR, fg="black", font=FONT_MAIN, width=40, relief="flat", takefocus=0)
btn_part_a.pack(side="left", padx=5, expand=True)
btn_part_b = tk.Button(row2, text="LAUNCH [B]", command=lambda: queue_part("B"), bg="#333333", fg=FG_COLOR, font=FONT_MAIN, width=40, relief="flat", takefocus=0)
btn_part_b.pack(side="right", expand=True)

row3 = tk.Frame(button_frame, bg=BG_COLOR); row3.pack(fill="x", pady=2)
tk.Button(row3, text="PLAY (SPACE)", command=play_action, bg="#4CAF50", fg="white", font=FONT_MAIN, width=22, relief="flat", takefocus=0).pack(side="left", padx=(0,10))
tk.Button(row3, text="STOP (SPACE)", command=stop_playback, bg="#F44336", fg="white", font=FONT_MAIN, width=22, relief="flat", takefocus=0).pack(side="left", padx=10)
tk.Button(row3, text="PANIC (KILL NOTES)", command=panic_action, bg="#E91E63", fg="white", font=FONT_MAIN, width=22, relief="flat", takefocus=0).pack(side="right")

status_label = tk.Label(main_frame, text="> READY", bg=BG_COLOR, fg=FG_COLOR, font=("Courier", 12, "bold"))
status_label.pack(anchor="w", pady=(5,0))

# ==========================================
# PHASE 6: BINDINGS & EVENT LISTENERS
# ==========================================
app.protocol("WM_DELETE_WINDOW", on_closing)
app.createcommand("tk::mac::Quit", on_closing)  # Handle Cmd+Q on macOS

app.bind_all("<space>", handle_spacebar)
app.bind_class("TCombobox", "<space>", handle_spacebar)
app.bind_class("Button", "<space>", handle_spacebar)
app.bind_class("Scale", "<space>", handle_spacebar)
app.bind_all("<KeyPress>", handle_keypress)

style_var.trace_add("write", lambda *args: [on_composer_change()])
algo_var.trace_add("write", lambda *args: [trigger_auto_generate()])
root_var.trace_add("write", lambda *args: [draw_piano_keyboard(), trigger_auto_generate()])
scale_var.trace_add("write", lambda *args: [draw_piano_keyboard(), trigger_auto_generate()])
length_var.trace_add("write", lambda *args: [trigger_auto_generate()])
chord_style_var.trace_add("write", lambda *args: [on_chord_style_change()])
digitone_shape_var.trace_add("write", lambda *args: [trigger_auto_generate()])
chord_rhythm_var.trace_add("write", lambda *args: [trigger_auto_generate()])
chord_oct_var.trace_add("write", lambda *args: [trigger_auto_generate()])
bass_pat_var.trace_add("write", lambda *args: [on_bass_pat_change()])
bass_rhythm_var.trace_add("write", lambda *args: [trigger_auto_generate()])
harm_var.trace_add("write", lambda *args: [trigger_auto_generate()])
sync_var.trace_add("write", on_sync_change)

complexity_slider.config(command=lambda val: trigger_auto_generate())
bass_comp_slider.config(command=lambda val: trigger_auto_generate())
vel_slider.config(command=lambda val: trigger_auto_generate())
feel_slider.config(command=lambda val: trigger_auto_generate())
strum_slider.config(command=lambda val: trigger_auto_generate())
chord_gate_slider.config(command=lambda val: trigger_auto_generate())
mel_gate_slider.config(command=lambda val: trigger_auto_generate())
hrm_gate_slider.config(command=lambda val: trigger_auto_generate())
bas_gate_slider.config(command=lambda val: trigger_auto_generate())

# ==========================================
# PHASE 7: MATRIX INIT & LAUNCH
# ==========================================
matrix_density_canvas = max(15, target_width // 60)
for i in range(matrix_density_canvas):
    x, y = random.randint(0, target_width), random.randint(-800, 0)
    tid = canvas.create_text(x, y, text="00\nFF", fill=MATRIX_COLOR, font=("Courier", 10, "bold"), anchor="n", justify="center")
    canvas.tag_lower(tid)
    matrix_items.append({"id": tid, "x": x, "y": y, "speed": random.randint(3, 8)})

draw_piano_keyboard()
on_composer_change()
refresh_midi_ports()
load_settings()
generate_action(force_new=True)

app.after(50, update_visualizer)
app.mainloop()
