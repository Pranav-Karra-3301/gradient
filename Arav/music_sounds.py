import mido
import time
import keyboard
import tkinter as tk
from typing import Dict, List

# Define instrument mappings (General MIDI program numbers)
INSTRUMENTS = {
    1: "Acoustic Grand Piano",
    5: "Electric Piano",
    25: "Acoustic Guitar",
    41: "Violin",
    57: "Trumpet",
    74: "Flute"
}

# Define note mappings for different instruments
NOTE_RANGES: Dict[int, List[int]] = {
    1: list(range(21, 109)),  # Piano (full range)
    5: list(range(28, 103)),  # Electric Piano
    25: list(range(40, 84)),  # Acoustic Guitar
    41: list(range(55, 100)), # Violin
    57: list(range(55, 82)),  # Trumpet
    74: list(range(60, 96))   # Flute
}

# Define notes for the visual interface
VISUAL_NOTES = [
    {'note': 60, 'name': 'C4', 'color': 'white'},
    {'note': 61, 'name': 'C#4', 'color': 'black'},
    {'note': 62, 'name': 'D4', 'color': 'white'},
    {'note': 63, 'name': 'D#4', 'color': 'black'},
    {'note': 64, 'name': 'E4', 'color': 'white'},
    {'note': 65, 'name': 'F4', 'color': 'white'},
    {'note': 66, 'name': 'F#4', 'color': 'black'},
    {'note': 67, 'name': 'G4', 'color': 'white'},
    {'note': 68, 'name': 'G#4', 'color': 'black'},
    {'note': 69, 'name': 'A4', 'color': 'white'},
    {'note': 70, 'name': 'A#4', 'color': 'black'},
    {'note': 71, 'name': 'B4', 'color': 'white'},
    {'note': 72, 'name': 'C5', 'color': 'white'}
]

class MusicInstrument:
    def __init__(self):
        self.port = mido.open_output()
        self.current_instrument = 1  # Default to piano
        self.active_notes = {}  # Dictionary to store active notes and their start times
        self.current_note = None
        self.start_time = None
        
    def select_instrument(self):
        """Display and select an instrument"""
        print("\nAvailable Instruments:")
        for number, name in INSTRUMENTS.items():
            print(f"{number}: {name}")
        
        try:
            num = int(input("\nSelect instrument number: "))
            if num in INSTRUMENTS:
                self.current_instrument = num
                # Send program change message to change instrument
                program_change = mido.Message('program_change', program=num-1)
                self.port.send(program_change)
                print(f"\nSelected instrument: {INSTRUMENTS[num]}")
                return True
            else:
                print("Invalid instrument number")
                return False
        except ValueError:
            print("Please enter a valid number")
            return False
    
    def start_note(self, note: int):
        """Start playing a note"""
        if note in NOTE_RANGES[self.current_instrument]:
            if self.current_note != note:
                if self.current_note is not None:
                    self.stop_note()
                
                self.current_note = note
                self.start_time = time.time()
                # Start with medium velocity
                note_on = mido.Message('note_on', note=note, velocity=64)
                self.port.send(note_on)
        else:
            print(f"Note {note} is out of range for {INSTRUMENTS[self.current_instrument]}")
    
    def stop_note(self):
        """Stop playing the current note"""
        if self.current_note is not None:
            duration = time.time() - self.start_time
            # Calculate velocity based on duration (longer press = stronger velocity)
            velocity = min(127, int(64 + (duration * 30)))
            
            # Send note off
            note_off = mido.Message('note_off', note=self.current_note, velocity=velocity)
            self.port.send(note_off)
            
            self.current_note = None
            self.start_time = None
    
    def play_scale(self, start_note: int, scale_type: str = "major"):
        """Play a scale starting from the given note"""
        major_scale = [0, 2, 4, 5, 7, 9, 11, 12]
        minor_scale = [0, 2, 3, 5, 7, 8, 10, 12]
        
        scale = major_scale if scale_type.lower() == "major" else minor_scale
        print(f"\nPlaying {scale_type} scale from note {start_note}")
        for interval in scale:
            note = start_note + interval
            self.start_note(note)
            time.sleep(0.5)
            self.stop_note()
    
    def visual_play_mode(self):
        """Create a visual interface for playing notes"""
        root = tk.Tk()
        root.title(f"Musical Interface - {INSTRUMENTS[self.current_instrument]}")
        
        # Set window size and position
        window_width = 800
        window_height = 400
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create canvas for drawing
        canvas = tk.Canvas(root, width=window_width, height=window_height, bg='lightgray')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Calculate key dimensions
        white_key_width = window_width // 8  # 8 white keys
        white_key_height = window_height * 0.8
        black_key_width = white_key_width * 0.6
        black_key_height = white_key_height * 0.6
        
        def draw_piano():
            """Draw the piano keys"""
            # Draw white keys
            white_x = 0
            white_index = 0
            for note in VISUAL_NOTES:
                if note['color'] == 'white':
                    canvas.create_rectangle(
                        white_x, window_height - white_key_height,
                        white_x + white_key_width, window_height,
                        fill='white', outline='black', tags=f"key_{note['note']}"
                    )
                    # Add note name
                    canvas.create_text(
                        white_x + white_key_width/2,
                        window_height - 20,
                        text=note['name'],
                        font=('Arial', 10)
                    )
                    white_x += white_key_width
                    white_index += 1
            
            # Draw black keys
            white_x = 0
            for i, note in enumerate(VISUAL_NOTES[:-1]):  # Exclude last note
                if note['color'] == 'white' and VISUAL_NOTES[i+1]['color'] == 'black':
                    canvas.create_rectangle(
                        white_x + white_key_width - black_key_width/2,
                        window_height - white_key_height,
                        white_x + white_key_width + black_key_width/2,
                        window_height - white_key_height + black_key_height,
                        fill='black', tags=f"key_{VISUAL_NOTES[i+1]['note']}"
                    )
                    # Add note name in white
                    canvas.create_text(
                        white_x + white_key_width,
                        window_height - white_key_height + black_key_height/2,
                        text=VISUAL_NOTES[i+1]['name'],
                        fill='white',
                        font=('Arial', 8)
                    )
                    white_x += white_key_width
                elif note['color'] == 'white':
                    white_x += white_key_width
        
        def get_note_from_position(event):
            """Determine which note to play based on mouse position"""
            x, y = event.x, event.y
            
            # Check if clicking black keys first (they're on top)
            white_x = 0
            for i, note in enumerate(VISUAL_NOTES[:-1]):
                if note['color'] == 'white' and VISUAL_NOTES[i+1]['color'] == 'black':
                    black_key_x1 = white_x + white_key_width - black_key_width/2
                    black_key_x2 = white_x + white_key_width + black_key_width/2
                    black_key_y = window_height - white_key_height + black_key_height
                    
                    if (black_key_x1 <= x <= black_key_x2 and 
                        window_height - white_key_height <= y <= black_key_y):
                        return VISUAL_NOTES[i+1]['note']
                    white_x += white_key_width
                elif note['color'] == 'white':
                    white_x += white_key_width
            
            # Check white keys
            white_x = 0
            for note in VISUAL_NOTES:
                if note['color'] == 'white':
                    if (white_x <= x <= white_x + white_key_width and 
                        window_height - white_key_height <= y <= window_height):
                        return note['note']
                    white_x += white_key_width
            
            return None
        
        def on_mouse_press(event):
            note = get_note_from_position(event)
            if note is not None:
                self.start_note(note)
                # Highlight the key
                canvas.itemconfig(f"key_{note}", fill='lightblue' if note in [n['note'] for n in VISUAL_NOTES if n['color'] == 'white'] else 'gray')
        
        def on_mouse_motion(event):
            note = get_note_from_position(event)
            if note is not None:
                self.start_note(note)
                # Highlight the key
                canvas.itemconfig(f"key_{note}", fill='lightblue' if note in [n['note'] for n in VISUAL_NOTES if n['color'] == 'white'] else 'gray')
        
        def on_mouse_release(event):
            self.stop_note()
            # Reset all key colors
            for note in VISUAL_NOTES:
                canvas.itemconfig(f"key_{note['note']}", fill=note['color'])
        
        # Draw the piano
        draw_piano()
        
        # Bind mouse events
        canvas.bind('<Button-1>', on_mouse_press)
        canvas.bind('<B1-Motion>', on_mouse_motion)
        canvas.bind('<ButtonRelease-1>', on_mouse_release)
        
        # Add quit button
        quit_button = tk.Button(root, text="Back to Menu", command=root.destroy)
        quit_button.pack(pady=10)
        
        root.mainloop()
    
    def close(self):
        """Close the MIDI port"""
        self.stop_note()
        self.port.close()

def main():
    instrument = MusicInstrument()
    print("\nWelcome to the Musical Instrument Interface!")
    
    # Initial instrument selection
    if not instrument.select_instrument():
        print("Failed to select instrument. Using default Piano.")
    
    while True:
        print("\n=== Musical Instrument Interface ===")
        print(f"Current Instrument: {INSTRUMENTS[instrument.current_instrument]}")
        print("\nOptions:")
        print("1. Change Instrument")
        print("2. Visual Play Mode")
        print("3. Scale Practice Mode")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            instrument.select_instrument()
        
        elif choice == "2":
            instrument.visual_play_mode()
        
        elif choice == "3":
            print("\nScale Practice Mode")
            print("This mode will play a complete musical scale")
            try:
                print("\nStarting notes reference:")
                for note in VISUAL_NOTES:
                    if note['color'] == 'white':
                        print(f"{note['name']}: {note['note']}")
                
                start_note = int(input("\nEnter starting note number: "))
                scale_type = input("Enter scale type (major/minor): ")
                instrument.play_scale(start_note, scale_type)
            except ValueError:
                print("Please enter a valid note number")
        
        elif choice == "4":
            instrument.close()
            print("Thank you for making music! Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
