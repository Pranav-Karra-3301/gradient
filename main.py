import cv2
import mediapipe as mp
import numpy as np
import sounddevice as sd
import time

# Initialize Mediapipe Hand solution
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

#####################
# Audio Configuration
#####################

SAMPLE_RATE = 44100  # Standard audio sampling rate
current_freq = 440.0  # Default frequency (A4 note)
volume = 0.3         # Default volume

##############################
# Sounddevice Audio Callback
##############################
def audio_callback(outdata, frames, time_info, status):
    """
    This callback is called by sounddevice for each audio block.
    We'll generate a simple sine wave at the current frequency.
    """
    global current_freq, volume

    # Generate time values for this chunk
    t = (np.arange(frames) + audio_callback.t0) / SAMPLE_RATE
    # Generate a sine wave
    tone = volume * np.sin(2 * np.pi * current_freq * t).astype(np.float32)

    # Write into outdata
    outdata[:] = tone.reshape(-1, 1)  # mono sound

    # Update t0 so next block continues where we left off
    audio_callback.t0 += frames

# Initialize t0 for the callback (keeps track of phase)
audio_callback.t0 = 0

###################################
# Hand Tracking and Main Loop
###################################
def main():
    global current_freq, volume

    # Open webcam (0 is typical default on macOS)
    cap = cv2.VideoCapture(0)
    # Adjust capture properties if needed
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Start audio stream
    stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=audio_callback
    )
    stream.start()

    hand_detector = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame from webcam. Exiting...")
                break

            # Convert the frame to RGB (Mediapipe uses RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process with Mediapipe
            results = hand_detector.process(frame_rgb)

            # Draw hand annotations on the original (BGR) frame for visualization
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                    )

                # For simplicity, we’ll only use the first detected hand
                first_hand_landmarks = results.multi_hand_landmarks[0]

                # Extract the wrist (landmark 0) and index fingertip (landmark 8)
                wrist = first_hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                index_fingertip = first_hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

                # The landmarks have x, y, z in [0, 1] range (relative to the image).
                # We can use these to set frequency/volume or other parameters.

                # Example: Map the index fingertip y-position to frequency
                # We'll invert y since top of the frame is 0
                # We can transform range [0,1] -> [200 Hz, 800 Hz]
                tipY = 1.0 - index_fingertip.y  # invert so up is bigger
                freq_min, freq_max = 200.0, 800.0
                new_freq = freq_min + (freq_max - freq_min) * tipY

                # Example: Map the x-position of index fingertip to volume
                # Range [0,1] -> [0.0, 0.7]
                tipX = index_fingertip.x
                vol_min, vol_max = 0.0, 0.7
                new_vol = vol_min + (vol_max - vol_min) * (1.0 - tipX)  # or just tipX

                # Update the global frequency & volume
                current_freq = new_freq
                volume = new_vol

            # Show the webcam feed with drawings
            cv2.imshow("Theremin", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # Press ESC to exit
                break

    except KeyboardInterrupt:
        print("Exiting...")

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    stream.stop()
    stream.close()


if __name__ == "__main__":
    main()