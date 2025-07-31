from collections import defaultdict
import random
import os
import mido

class MarkovComposer:
    def __init__(self, order=2):
        self.order = order
        self.transitions = {
            'melody': defaultdict(lambda: defaultdict(int)),
            'bass': defaultdict(lambda: defaultdict(int))
        }
        # Common durations: quarter, eighth, sixteenth, dotted eighth, thirty-second note
        self.note_durations = [480, 240, 120, 360, 60] 
        self.duration_weights = [0.4, 0.3, 0.2, 0.05, 0.05] # Probability weights for durations

    def train(self, midi_files):
        melody_notes = []
        bass_notes = []
        
        for file_path in midi_files:
            try:
                midi_file = mido.MidiFile(file_path, clip=True)
                
                for i, track in enumerate(midi_file.tracks):
                    # Skip empty tracks or tracks that are just metadata
                    if not any(msg.type in ['note_on', 'note_off'] for msg in track):
                        continue

                    track_type = self._classify_track(track)
                    notes = self._extract_notes_from_track(track)
                    
                    if track_type == 'melody':
                        melody_notes.extend(notes)
                    elif track_type == 'bass':
                        bass_notes.extend(notes)
                    # else: print(f"Skipping track {i} in {os.path.basename(file_path)} as 'other'")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        if not melody_notes:
            print("No suitable melody tracks found across all MIDI files. Check your dataset or refine classification thresholds.")
        if not bass_notes:
            print("No suitable bass tracks found across all MIDI files. Check your dataset or refine classification thresholds.")
            
        if melody_notes:
            print(f"Training melody Markov chain with {len(melody_notes)} notes...")
            self._build_transitions(melody_notes, 'melody')
        else:
            print("Skipping melody Markov chain training due to lack of notes.")

        if bass_notes:
            print(f"Training bass Markov chain with {len(bass_notes)} notes...")
            self._build_transitions(bass_notes, 'bass')
        else:
            print("Skipping bass Markov chain training due to lack of notes.")


    def _classify_track(self, track):
        notes_in_track = []
        min_pitch = 128 # Max possible MIDI note + 1
        max_pitch = -1  # Min possible MIDI note - 1
        is_percussion_channel = False
        
        for msg in track:
            if msg.type == 'program_change':
                # General MIDI percussion instruments often start from program 112
                # Standard drum channel is 9 (MIDI channels are 0-15)
                if msg.channel == 9 or msg.program >= 112: 
                    is_percussion_channel = True
            elif msg.type == 'note_on' and msg.velocity > 0:
                notes_in_track.append(msg.note)
                if msg.note < min_pitch:
                    min_pitch = msg.note
                if msg.note > max_pitch:
                    max_pitch = msg.note
        
        # If no notes, it's not a melodic/bass track
        if not notes_in_track:
            return 'other'
            
        # If it's a percussion channel, classify as 'other' for melodic/bass purposes
        if is_percussion_channel:
            return 'other'

        average_pitch = sum(notes_in_track) / len(notes_in_track)
        pitch_range = max_pitch - min_pitch

        # Heuristics for classification (these are tunable!)
        # Standard MIDI note for Middle C is 60. C3 is 48. C2 is 36.
        
        # Bass Track Criteria:
        # - Predominantly low notes (average pitch below C3)
        # - Relatively narrow pitch range
        # - Fewer notes overall (compared to typical melodies)
        if average_pitch < 48 and pitch_range < 24 and len(notes_in_track) > 10: # Minimum notes to be considered a valid part
            return 'bass'
        
        # Melody Track Criteria:
        # - Higher average pitch (above Middle C)
        # - Wider pitch range
        # - More notes overall
        elif average_pitch >= 60 and pitch_range > 12 and len(notes_in_track) > 20: # Minimum notes
            return 'melody'
            
        # If it doesn't fit specific melody or bass criteria, classify as 'other'
        return 'other' 

    def _extract_notes_from_track(self, track):
        notes = []
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                notes.append(msg.note)
        return notes

    def _build_transitions(self, notes, track_type):
        transitions = self.transitions[track_type]
        # Ensure enough notes for the given order
        if len(notes) < self.order + 1:
            print(f"Not enough notes ({len(notes)}) to build a Markov chain of order {self.order} for {track_type}.")
            return

        for i in range(len(notes) - self.order):
            state = tuple(notes[i:i+self.order])
            next_note = notes[i+self.order] 
            transitions[state][next_note] += 1

        for state, next_notes in transitions.items():
            total = sum(next_notes.values())
            for next_note, count in next_notes.items():
                transitions[state][next_note] = count / total

    def generate_music(self, length=200, output_path="generated_music.mid", tempo=120):
        if not self.transitions['melody'] and not self.transitions['bass']:
            print("No models trained. Cannot generate music.")
            return

        output_midi = mido.MidiFile()
        
        melody_track = mido.MidiTrack()
        bass_track = mido.MidiTrack()
        
        # Append tracks to MIDI file (order matters for some players)
        output_midi.tracks.append(melody_track)
        output_midi.tracks.append(bass_track)

        # Set tempo for both tracks (usually only needed on one, but safe to add to both)
        melody_track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo)))
        bass_track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo)))

        # Melody instrument and channel
        melody_track.append(mido.Message('program_change', program=73, channel=0)) # Tenor Saxophone (You can change this!)
        # Bass instrument and channel
        bass_track.append(mido.Message('program_change', program=33, channel=1))  # Upright Bass (You can change this!)

        # Generate melody and bassline only if models exist
        if self.transitions['melody']:
            # Generate melody with a louder velocity range
            self._generate_track(melody_track, 'melody', length, min_velocity=30, max_velocity=60)
        else:
            print("Skipping melody generation, no melody model trained.")
        
        if self.transitions['bass']:
            # Generate bass with a softer velocity range
            self._generate_track(bass_track, 'bass', length, min_velocity=40, max_velocity=80)
        else:
            print("Skipping bass generation, no bass model trained.")
        
        output_midi.save(output_path)
        print(f"Music generated successfully and saved to {output_path}")

    def _generate_track(self, track, track_type, length, min_velocity, max_velocity):
        transitions = self.transitions[track_type]
        initial_states = list(transitions.keys())
        if not initial_states:
            return # Cannot generate if no states to start from
            
        current_state = random.choice(initial_states)
        
        generated_notes = list(current_state)
        for _ in range(length):
            next_note_options = transitions.get(current_state)
            
            # If current state doesn't have transitions, pick a new random starting state
            if not next_note_options:
                current_state = random.choice(initial_states)
                continue
            
            next_note = random.choices(
                list(next_note_options.keys()),
                weights=list(next_note_options.values()),
                k=1
            )[0]
            
            note_duration = random.choices(self.note_durations, weights=self.duration_weights, k=1)[0]
            velocity = random.randint(min_velocity, max_velocity)
            
            # Use appropriate MIDI channel for melody (0) or bass (1)
            channel = 0 if track_type == 'melody' else 1
            
            track.append(mido.Message('note_on', note=next_note, velocity=velocity, time=note_duration, channel=channel))
            # Note off for the *previous* note to ensure correct timing
            track.append(mido.Message('note_off', note=generated_notes[-1], velocity=velocity, time=0, channel=channel))
            
            generated_notes.append(next_note)
            current_state = tuple(generated_notes[-self.order:])
        
        # Ensure the last note is turned off
        track.append(mido.Message('note_off', note=generated_notes[-1], velocity=0, time=0, channel=channel))