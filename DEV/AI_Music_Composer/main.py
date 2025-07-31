from composer import MarkovComposer
import glob
import os

if __name__ == "__main__":
    # Correct path to the MIDI files, based on your folder structure
    midi_files_path = os.path.join("jazz_midi_files", "*.mid")

    # Get all MIDI files from the data directory
    midi_files = glob.glob(midi_files_path)

    if not midi_files:
        # This message will only show if the folder structure is still wrong
        print(f"No MIDI files found at '{midi_files_path}'. Please check your folder structure.")
    else:
        # Initialize and train the composer
        composer = MarkovComposer(order=2)
        print(f"Training on {len(midi_files)} MIDI files...")
        composer.train(midi_files)

        # Generate new music
        print("Generating new music...")
        composer.generate_music(length=200, output_path="generated_music.mid")