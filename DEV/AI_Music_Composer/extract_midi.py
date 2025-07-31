import tarfile
import os

# Define the paths
archive_path = "C:\\Users\\KIIT\\Desktop\\music2\\Jazz-Midi.tar.xz"
destination_folder = "jazz_midi_files"

print(f"Checking for archive at: {archive_path}")

# Check if the archive file exists
if not os.path.exists(archive_path):
    print(f"Error: Archive not found at {archive_path}.")
    print("Please make sure you have uploaded the Jazz-Midi.tar.xz file.")
else:
    print(f"Extracting files from {archive_path} to {destination_folder}...")

    # Create the destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)
    
    # Open the archive and extract all files
    try:
        with tarfile.open(archive_path, "r:xz") as tar:
            tar.extractall(path=destination_folder)
        print("Extraction complete.")
    except tarfile.ReadError:
        print(f"Error: Unable to read {archive_path}. It might be corrupted or not a valid xz file.")
    except Exception as e:
        print(f"An unexpected error occurred during extraction: {e}")
