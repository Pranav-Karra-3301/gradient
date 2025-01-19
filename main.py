import cv2
import mediapipe as mp
import numpy as np
import sounddevice as sd

#####################
# Audio Configuration
#####################

SAMPLE_RATE = 96000 # Standard audio sampling rate
volume = 0.3         # Default volume

# We'll keep a list of active frequencies instead of a single freq
active_frequencies = []

##############################
# Sounddevice Audio Callback
##############################
def audio_callback(outdata, frames, time_info, status):
    """
    This callback is called by sounddevice for each audio block.
    We'll sum up sine waves for all active frequencies.
    """
    global active_frequencies, volume

    # Generate time values for this chunk
    t = (np.arange(frames) + audio_callback.t0) / SAMPLE_RATE

    # Start with silence
    mix = np.zeros(frames, dtype=np.float32)

    # Sum a sine wave for each active frequency
    for freq in active_frequencies:
        mix += volume * np.sin(2 * np.pi * freq * t).astype(np.float32)

    outdata[:] = mix.reshape(-1, 1)  # mono sound

    # Update t0 so next block continues where we left off
    audio_callback.t0 += frames

audio_callback.t0 = 0  # phase accumulator

###########################
# Mediapipe Setup
###########################
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def count_extended_fingers(hand_landmarks):
    """
    A simple heuristic to count how many fingers are extended.
    We'll check for each finger if the fingertip is
    above (i.e. y is smaller) than the PIP joint.
    (Note: Mediapipe's coordinate system has y increasing DOWNWARD.)
    """
    # Landmark indices for each finger tip and PIP
    # Thumb (tip=4, pip=2), Index (tip=8, pip=6), Middle (tip=12, pip=10),
    # Ring (tip=16, pip=14), Pinky (tip=20, pip=18).
    finger_tips = [4, 8, 12, 16, 20]
    finger_pips = [2, 6, 10, 14, 18]

    extended_count = 0
    for tip_idx, pip_idx in zip(finger_tips, finger_pips):
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]

        # If fingertip is above the PIP joint, consider it extended
        if tip.y < pip.y:
            extended_count += 1

    return extended_count


def main():
    global active_frequencies, volume

    # Open webcam
    cap = cv2.VideoCapture(0)

    # Start audio stream
    stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=audio_callback
    )
    stream.start()

    # Hand detector
    hand_detector = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,  # for simplicity, track only one hand at a time
        min_detection_confidence=0.5,
        min_tracking_confidence=0.3
    )

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame from webcam. Exiting...")
                break

            # Draw an XY grid on the frame
            frame_height, frame_width, _ = frame.shape

            # For example, draw a 4x4 grid
            grid_rows = 10
            grid_cols = 10
            row_step = frame_height // grid_rows
            col_step = frame_width // grid_cols

            for r in range(1, grid_rows):
                y = r * row_step
                cv2.line(frame, (0, y), (frame_width, y), (0, 255, 0), 1)
            for c in range(1, grid_cols):
                x = c * col_step
                cv2.line(frame, (x, 0), (x, frame_height), (0, 255, 0), 1)

            # Convert the frame to RGB (Mediapipe uses RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hand_detector.process(frame_rgb)

            if results.multi_hand_landmarks:
                # We only look at the first detected hand for simplicity
                hand_landmarks = results.multi_hand_landmarks[0]

                # Draw the hand annotations
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                )

                # Count extended fingers
                extended = count_extended_fingers(hand_landmarks)

                # We can get index fingertip as a reference for XY
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

                # x,y in [0,1], with y going DOWN.
                x = index_tip.x
                y = index_tip.y

                # Map X to volume (0.0 - 0.7)
                vol_min, vol_max = 0.0, 0.7
                volume = vol_min + (vol_max - vol_min) * (1.0 - x)

                # We'll map Y to a base frequency (200-800 Hz)
                # Invert Y so that moving the hand up (y=0) is higher pitch
                freq_min, freq_max = 200.0, 800.0
                base_freq = freq_min + (freq_max - freq_min) * (1.0 - y)

                # Now decide frequencies based on how many fingers are extended
                if extended == 1:
                    # One note
                    active_frequencies = [base_freq]

                elif extended == 2:
                    # Two notes: base_freq and an interval above it (e.g. perfect 5th)
                    interval_ratio = 1.5  # perfect 5th
                    active_frequencies = [base_freq, base_freq * interval_ratio]

                elif extended == 0:
                    # Fist → an ensemble (e.g. a major chord)
                    # We'll center the chord around base_freq
                    # Frequencies: base_freq, major third, perfect fifth, octave
                    # That is roughly (1, 1.26, 1.50, 2.0)
                    major_third = 1.26
                    perfect_fifth = 1.50
                    octave = 2.00
                    active_frequencies = [
                        base_freq,
                        base_freq * major_third,
                        base_freq * perfect_fifth,
                        base_freq * octave,
                    ]
                else:
                    # Any other case (3,4,5 fingers?), just default to a single note
                    active_frequencies = [base_freq]

            else:
                # No hand detected → no active frequencies (silence)
                active_frequencies = []

            # Show the webcam feed
            cv2.imshow("Theremin with XY Grid", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC key
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