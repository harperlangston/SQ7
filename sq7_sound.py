#!/usr/bin/env python3
"""
sq7_sound.py -- Chiptune sound engine for Space Quest 7.

Synthesizes all audio programmatically (no external files required).
Uses pygame.mixer for playback. Gracefully degrades if pygame is
unavailable or audio initialization fails.
"""

import math
import array
import random

try:
    import pygame
    import pygame.mixer
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_RATE = 22050  # Hz, mono 16-bit signed

# Equal-temperament note frequency table (C1-B7)
NOTE_FREQS = {}
_NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
for _octave in range(1, 8):
    for _i, _name in enumerate(_NOTE_NAMES):
        _midi = (_octave + 1) * 12 + _i
        NOTE_FREQS[f"{_name}{_octave}"] = 440.0 * (2.0 ** ((_midi - 69) / 12.0))
# Aliases for flat notes
NOTE_FREQS['Bb1'] = NOTE_FREQS['A#1']
NOTE_FREQS['Bb2'] = NOTE_FREQS['A#2']
NOTE_FREQS['Bb3'] = NOTE_FREQS['A#3']
NOTE_FREQS['Bb4'] = NOTE_FREQS['A#4']
NOTE_FREQS['Bb5'] = NOTE_FREQS['A#5']
NOTE_FREQS['Eb3'] = NOTE_FREQS['D#3']
NOTE_FREQS['Eb4'] = NOTE_FREQS['D#4']
NOTE_FREQS['Eb5'] = NOTE_FREQS['D#5']
NOTE_FREQS['Ab3'] = NOTE_FREQS['G#3']
NOTE_FREQS['Ab4'] = NOTE_FREQS['G#4']
NOTE_FREQS['Db4'] = NOTE_FREQS['C#4']
NOTE_FREQS['Db5'] = NOTE_FREQS['C#5']
NOTE_FREQS['Gb4'] = NOTE_FREQS['F#4']

# ---------------------------------------------------------------------------
# Waveform generators
# ---------------------------------------------------------------------------

def generate_sine(freq, duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Smooth sine wave — good for drones and pads."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = int(32767 * volume)
    for i in range(n):
        val = int(amp * math.sin(2.0 * math.pi * freq * i / sample_rate))
        buf.append(val)
    return buf.tobytes()


def generate_square(freq, duration, volume=0.2, duty=0.5, sample_rate=SAMPLE_RATE):
    """Square wave — classic chiptune lead sound."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = int(32767 * volume)
    period = sample_rate / freq
    for i in range(n):
        phase = (i % period) / period
        val = amp if phase < duty else -amp
        buf.append(val)
    return buf.tobytes()


def generate_sawtooth(freq, duration, volume=0.18, sample_rate=SAMPLE_RATE):
    """Sawtooth wave — buzzy bass lines."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = int(32767 * volume)
    period = sample_rate / freq
    for i in range(n):
        phase = (i % period) / period
        val = int(amp * (2.0 * phase - 1.0))
        buf.append(val)
    return buf.tobytes()


def generate_noise(duration, volume=0.08, sample_rate=SAMPLE_RATE):
    """White noise — hiss, explosions, static."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = int(32767 * volume)
    for _ in range(n):
        buf.append(random.randint(-amp, amp))
    return buf.tobytes()


def generate_silence(duration, sample_rate=SAMPLE_RATE):
    """Silent padding for rests."""
    n = int(sample_rate * duration)
    return b'\x00\x00' * n


# ---------------------------------------------------------------------------
# Audio utilities
# ---------------------------------------------------------------------------

def apply_envelope(raw_bytes, attack=0.01, decay=0.03, sustain_level=0.65,
                   release=0.03, sample_rate=SAMPLE_RATE):
    """Apply ADSR envelope to avoid clicks and give notes musical shape."""
    buf = array.array('h')
    buf.frombytes(raw_bytes)
    n = len(buf)
    a_end = int(attack * sample_rate)
    d_end = a_end + int(decay * sample_rate)
    r_start = max(d_end, n - int(release * sample_rate))
    for i in range(n):
        if i < a_end:
            env = i / max(a_end, 1)
        elif i < d_end:
            t = (i - a_end) / max(d_end - a_end, 1)
            env = 1.0 - (1.0 - sustain_level) * t
        elif i < r_start:
            env = sustain_level
        else:
            t = (i - r_start) / max(n - r_start, 1)
            env = sustain_level * (1.0 - t)
        buf[i] = int(buf[i] * env)
    return buf.tobytes()


def mix_samples(*byte_arrays):
    """Mix multiple equal-length sample byte arrays, clipping to 16-bit range."""
    arrays = []
    for b in byte_arrays:
        a = array.array('h')
        a.frombytes(b)
        arrays.append(a)
    length = min(len(a) for a in arrays)
    result = array.array('h', [0] * length)
    for a in arrays:
        for i in range(length):
            val = result[i] + a[i]
            result[i] = max(-32768, min(32767, val))
    return result.tobytes()


def note_freq(note_str):
    """Return frequency in Hz for a note string like 'C4', 'F#3', 'Bb2'."""
    return NOTE_FREQS.get(note_str, 440.0)


# ---------------------------------------------------------------------------
# MelodySequencer
# ---------------------------------------------------------------------------

class MelodySequencer:
    """
    Renders a list of (note_str_or_None, beats) tuples into a pygame.mixer.Sound.

    note_str: e.g. 'C4', 'F#3', 'Bb2', or None/'R' for a rest.
    beats: duration in beats (float).
    """

    def __init__(self, notes, bpm=120, wave_fn=None, volume=0.18,
                 envelope=True, bass_notes=None, bass_wave_fn=None,
                 bass_volume=0.15):
        self.notes = notes
        self.bpm = bpm
        self.wave_fn = wave_fn or generate_square
        self.volume = volume
        self.envelope = envelope
        self.bass_notes = bass_notes  # optional bass line: [(note, beats), ...]
        self.bass_wave_fn = bass_wave_fn or generate_sawtooth
        self.bass_volume = bass_volume

    def render(self, sample_rate=SAMPLE_RATE):
        beat_dur = 60.0 / self.bpm
        melody_bytes = b''
        for note_str, beats in self.notes:
            dur = beat_dur * beats
            if not note_str or note_str == 'R':
                melody_bytes += generate_silence(dur, sample_rate)
            else:
                freq = note_freq(note_str)
                raw = self.wave_fn(freq, dur, self.volume, sample_rate)
                if self.envelope:
                    raw = apply_envelope(raw, sample_rate=sample_rate)
                melody_bytes += raw

        if not self.bass_notes:
            return pygame.mixer.Sound(buffer=melody_bytes)

        # Render bass line and mix
        bass_bytes = b''
        for note_str, beats in self.bass_notes:
            dur = beat_dur * beats
            if not note_str or note_str == 'R':
                bass_bytes += generate_silence(dur, sample_rate)
            else:
                freq = note_freq(note_str)
                raw = self.bass_wave_fn(freq, dur, self.bass_volume, sample_rate)
                if self.envelope:
                    raw = apply_envelope(raw, attack=0.005, decay=0.05,
                                         sustain_level=0.5, release=0.05,
                                         sample_rate=sample_rate)
                bass_bytes += raw

        # Pad shorter track with silence
        if len(melody_bytes) > len(bass_bytes):
            bass_bytes += generate_silence(
                (len(melody_bytes) - len(bass_bytes)) / (sample_rate * 2),
                sample_rate)
        elif len(bass_bytes) > len(melody_bytes):
            melody_bytes += generate_silence(
                (len(bass_bytes) - len(melody_bytes)) / (sample_rate * 2),
                sample_rate)

        mixed = mix_samples(melody_bytes, bass_bytes)
        return pygame.mixer.Sound(buffer=mixed)


# ---------------------------------------------------------------------------
# SoundEngine
# ---------------------------------------------------------------------------

class SoundEngine:
    """
    Chiptune sound engine for Space Quest 7.

    Synthesizes all audio at init time and caches as pygame.mixer.Sound objects.
    Channel 0: looping room music.
    Channels 1-3: one-shot SFX (round-robin).
    """

    MUSIC_CHANNEL = 0
    SFX_CHANNELS = [1, 2, 3]

    def __init__(self):
        self._disabled = False
        self._current_room = None
        self._sfx_index = 0
        self._room_music = {}
        self._sfx = {}

        if not _PYGAME_AVAILABLE:
            self._disabled = True
            return

        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1,
                              buffer=512)
            pygame.mixer.set_num_channels(4)
            self._music_ch = pygame.mixer.Channel(self.MUSIC_CHANNEL)
            self._sfx_chs = [pygame.mixer.Channel(i) for i in self.SFX_CHANNELS]
        except Exception:
            self._disabled = True
            return

        try:
            self._build_room_music()
        except Exception:
            pass  # music unavailable but SFX may still work

        try:
            self._build_sfx()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play_room_music(self, room_key):
        if self._disabled or room_key == self._current_room:
            return
        try:
            self._current_room = room_key
            sound = self._room_music.get(room_key)
            if sound:
                self._music_ch.fadeout(80)
                self._music_ch.play(sound, loops=-1, fade_ms=200)
            else:
                self._music_ch.stop()
        except Exception:
            pass

    def play_sfx(self, event_name):
        if self._disabled:
            return
        try:
            sound = self._sfx.get(event_name)
            if not sound:
                return
            ch = self._sfx_chs[self._sfx_index % len(self._sfx_chs)]
            self._sfx_index += 1
            ch.play(sound)
        except Exception:
            pass

    def stop_music(self):
        if self._disabled:
            return
        try:
            self._music_ch.fadeout(300)
            self._current_room = None
        except Exception:
            pass

    def stop_all(self):
        if self._disabled:
            return
        try:
            pygame.mixer.stop()
            self._current_room = None
        except Exception:
            pass

    def set_music_volume(self, vol):
        if self._disabled:
            return
        try:
            self._music_ch.set_volume(max(0.0, min(1.0, vol)))
        except Exception:
            pass

    def set_sfx_volume(self, vol):
        if self._disabled:
            return
        try:
            for ch in self._sfx_chs:
                ch.set_volume(max(0.0, min(1.0, vol)))
        except Exception:
            pass

    def shutdown(self):
        if self._disabled:
            return
        try:
            pygame.mixer.quit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Room music construction
    # ------------------------------------------------------------------

    def _build_room_music(self):
        """Synthesize looping background music for each room."""

        # --- Junk Pile: C minor, 80 BPM, dismal/comedic ---
        self._room_music['junk_pile'] = MelodySequencer(
            notes=[
                ('C4', 1), ('Eb4', 1), ('G4', 0.5), ('F4', 0.5),
                ('Eb4', 1), ('D4', 1), ('C4', 2),
                ('R', 1), ('G3', 1), ('Ab3', 0.5), ('G3', 0.5),
                ('F3', 1), ('Eb3', 1), ('D3', 1), ('C3', 2),
            ],
            bpm=80, wave_fn=generate_square, volume=0.16,
            bass_notes=[
                ('C2', 2), ('G2', 2), ('Eb2', 2), ('G2', 2),
                ('C2', 2), ('G2', 2), ('Eb2', 2), ('C2', 2),
            ],
            bass_wave_fn=generate_sawtooth, bass_volume=0.12,
        ).render()

        # --- Engine Room: E minor, 100 BPM, industrial/mechanical ---
        self._room_music['engine_room'] = MelodySequencer(
            notes=[
                ('E3', 0.5), ('R', 0.5), ('B3', 0.5), ('R', 0.5),
                ('E3', 0.5), ('R', 0.5), ('B3', 0.5), ('R', 0.5),
                ('E3', 0.5), ('F#3', 0.5), ('G3', 0.5), ('R', 0.5),
                ('E3', 0.5), ('R', 0.5), ('B2', 0.5), ('R', 0.5),
            ],
            bpm=100, wave_fn=generate_square, volume=0.18,
            bass_notes=[
                ('E2', 1), ('E2', 1), ('B1', 1), ('E2', 1),
                ('E2', 1), ('E2', 1), ('B1', 1), ('E2', 1),
            ],
            bass_wave_fn=generate_sawtooth, bass_volume=0.14,
        ).render()

        # --- Engine Room Catwalk: E minor, 90 BPM, tense/heights ---
        self._room_music['engine_room_catwalk'] = MelodySequencer(
            notes=[
                ('E4', 1), ('F#4', 0.5), ('G4', 1), ('A4', 0.5),
                ('G4', 1), ('F#4', 0.5), ('E4', 1), ('R', 1),
                ('B3', 1), ('E4', 1), ('D4', 0.5), ('C#4', 0.5),
                ('B3', 2),
            ],
            bpm=90, wave_fn=generate_square, volume=0.15,
            bass_notes=[
                ('E2', 2), ('B2', 2), ('E2', 2), ('B2', 2),
                ('E2', 2), ('B2', 2), ('E2', 2), ('B2', 2),
            ],
            bass_wave_fn=generate_sine, bass_volume=0.10,
        ).render()

        # --- Airlock Corridor: A minor, 70 BPM, eerie/empty ---
        self._room_music['airlock_corridor'] = MelodySequencer(
            notes=[
                ('A4', 2), ('R', 2), ('E4', 1), ('R', 1),
                ('A4', 1), ('R', 1), ('C5', 2), ('R', 2),
                ('R', 2), ('A5', 0.5), ('R', 3.5),
            ],
            bpm=70, wave_fn=generate_sine, volume=0.14,
            bass_notes=[
                ('A2', 4), ('E2', 4), ('A2', 4), ('E2', 4),
            ],
            bass_wave_fn=generate_sine, bass_volume=0.08,
        ).render()

        # --- Escape Pod Bay: C major, 110 BPM, anticipation ---
        self._room_music['escape_pod_bay'] = MelodySequencer(
            notes=[
                ('C4', 0.5), ('E4', 0.5), ('G4', 0.5), ('C5', 1),
                ('G4', 0.5), ('E4', 0.5), ('C4', 0.5), ('R', 0.5),
                ('D4', 0.5), ('F4', 0.5), ('A4', 0.5), ('D5', 1),
                ('A4', 0.5), ('F4', 0.5), ('D4', 0.5), ('R', 0.5),
            ],
            bpm=110, wave_fn=generate_square, volume=0.17,
            bass_notes=[
                ('C2', 2), ('G2', 2), ('D2', 2), ('A2', 2),
            ],
            bass_wave_fn=generate_sawtooth, bass_volume=0.12,
        ).render()

        # --- Escape Pod (Landed): G major, 100 BPM, new world/hopeful ---
        self._room_music['escape_pod_(landed)'] = MelodySequencer(
            notes=[
                ('G4', 1), ('B4', 0.5), ('D5', 1), ('C5', 0.5),
                ('B4', 1), ('A4', 0.5), ('G4', 1), ('R', 1),
                ('D4', 0.5), ('G4', 1), ('A4', 0.5), ('B4', 1),
                ('G4', 2),
            ],
            bpm=100, wave_fn=generate_square, volume=0.17,
            bass_notes=[
                ('G2', 2), ('D2', 2), ('G2', 2), ('D2', 2),
                ('G2', 2), ('D2', 2), ('G2', 2), ('D2', 2),
            ],
            bass_wave_fn=generate_sine, bass_volume=0.10,
        ).render()

        # --- Monolith Burger Exterior: F major, 130 BPM, cheesy jingle ---
        self._room_music['monolith_burger_exterior'] = MelodySequencer(
            notes=[
                ('F4', 0.5), ('A4', 0.5), ('C5', 0.5), ('A4', 0.5),
                ('F4', 0.5), ('C4', 0.5), ('F4', 1),
                ('R', 0.5), ('C5', 0.5), ('Bb4', 0.5), ('A4', 0.5),
                ('G4', 0.5), ('F4', 0.5), ('C4', 0.5), ('F4', 1),
            ],
            bpm=130, wave_fn=generate_square, volume=0.18,
            bass_notes=[
                ('F2', 1), ('F2', 1), ('C2', 1), ('F2', 1),
                ('F2', 1), ('Bb2', 1), ('C2', 1), ('F2', 1),
            ],
            bass_wave_fn=generate_sawtooth, bass_volume=0.13,
        ).render()

        # --- Monolith Burger Counter: F major, 120 BPM, bustling ---
        self._room_music['monolith_burger_counter'] = MelodySequencer(
            notes=[
                ('F4', 0.5), ('R', 0.25), ('A4', 0.5), ('R', 0.25),
                ('C5', 0.5), ('Bb4', 0.5), ('A4', 0.5), ('G4', 0.5),
                ('F4', 1), ('R', 0.5),
                ('C4', 0.5), ('F4', 0.5), ('A4', 0.5), ('C5', 1),
            ],
            bpm=120, wave_fn=generate_square, volume=0.17,
            bass_notes=[
                ('F2', 1), ('F2', 1), ('Bb2', 1), ('C3', 1),
                ('F2', 1), ('F2', 1), ('Bb2', 1), ('C3', 1),
            ],
            bass_wave_fn=generate_sawtooth, bass_volume=0.13,
        ).render()

        # --- Monolith Burger Kitchen: D minor, 110 BPM, hot/dangerous ---
        self._room_music['monolith_burger_kitchen'] = MelodySequencer(
            notes=[
                ('D4', 1), ('F4', 0.5), ('A4', 1), ('G4', 0.5),
                ('F4', 0.5), ('E4', 0.5), ('D4', 1),
                ('R', 0.5), ('A3', 0.5), ('D4', 0.5), ('F4', 0.5),
                ('E4', 0.5), ('D4', 0.5), ('A3', 1),
            ],
            bpm=110, wave_fn=generate_square, volume=0.17,
            bass_notes=[
                ('D2', 1), ('F2', 1), ('A2', 1), ('D3', 1),
                ('D2', 1), ('F2', 1), ('A2', 1), ('D3', 1),
            ],
            bass_wave_fn=generate_sawtooth, bass_volume=0.13,
        ).render()

        # --- Incinerator Chamber: chromatic descent, 160 BPM, urgent/deadly ---
        self._room_music['incinerator_chamber'] = MelodySequencer(
            notes=[
                ('E5', 0.5), ('Eb5', 0.5), ('D5', 0.5), ('C#5', 0.5),
                ('C5', 0.5), ('B4', 0.5), ('Bb4', 0.5), ('A4', 0.5),
                ('R', 0.5), ('A4', 0.5), ('Bb4', 0.5), ('A4', 0.5),
            ],
            bpm=160, wave_fn=generate_square, volume=0.20,
            bass_notes=[
                ('A2', 0.5), ('R', 0.5), ('A2', 0.5), ('R', 0.5),
                ('A2', 0.5), ('R', 0.5), ('A2', 0.5), ('R', 0.5),
                ('A2', 0.5), ('R', 0.5), ('A2', 0.5), ('R', 0.5),
            ],
            bass_wave_fn=generate_sine, bass_volume=0.14,
        ).render()

        # --- CEO Hallway: Bb minor, 85 BPM, corporate menace ---
        self._room_music['ceo_hallway'] = MelodySequencer(
            notes=[
                ('Bb3', 1), ('Db4', 1), ('F4', 0.5), ('Eb4', 0.5),
                ('Db4', 1), ('C4', 0.5), ('Bb3', 1.5),
                ('R', 1), ('F3', 1), ('Bb3', 1),
            ],
            bpm=85, wave_fn=generate_square, volume=0.16,
            bass_notes=[
                ('Bb2', 2), ('F2', 2), ('Bb2', 2), ('F2', 2),
                ('Bb2', 2), ('F2', 2),
            ],
            bass_wave_fn=generate_sine, bass_volume=0.11,
        ).render()

        # --- CEO Office: Bb minor, 95 BPM, confrontation/power ---
        self._room_music['ceo_office'] = MelodySequencer(
            notes=[
                ('Bb4', 0.5), ('Db5', 0.5), ('F5', 1), ('Db5', 0.5),
                ('Bb4', 1), ('R', 0.5),
                ('Ab4', 0.5), ('Gb4', 0.5), ('F4', 1), ('Eb4', 0.5),
                ('Db4', 0.5), ('Bb3', 1.5),
            ],
            bpm=95, wave_fn=generate_square, volume=0.19,
            bass_notes=[
                ('Bb2', 1), ('Bb2', 1), ('F2', 1), ('Bb2', 1),
                ('Bb2', 1), ('Bb2', 1), ('F2', 1), ('Bb2', 1),
            ],
            bass_wave_fn=generate_sawtooth, bass_volume=0.14,
        ).render()

        # --- Holding Cell: C minor, 75 BPM, desperate hope ---
        self._room_music['holding_cell'] = MelodySequencer(
            notes=[
                ('C4', 1), ('Eb4', 0.5), ('G4', 1), ('Ab4', 0.5),
                ('G4', 1), ('F4', 0.5), ('Eb4', 0.5), ('D4', 0.5),
                ('C4', 2), ('R', 1),
                ('G3', 0.5), ('C4', 1), ('Eb4', 0.5),
            ],
            bpm=75, wave_fn=generate_sine, volume=0.15,
            bass_notes=[
                ('C2', 2), ('G2', 2), ('Eb2', 2), ('G2', 2),
                ('C2', 2), ('G2', 2), ('Eb2', 2), ('G2', 2),
            ],
            bass_wave_fn=generate_sine, bass_volume=0.09,
        ).render()

    # ------------------------------------------------------------------
    # SFX construction
    # ------------------------------------------------------------------

    def _build_sfx(self):
        """Synthesize one-shot sound effects for game events."""

        # --- death: descending chromatic run + noise burst ---
        death_bytes = b''
        notes_d = ['C5', 'B4', 'Bb4', 'A4', 'Ab4', 'G4', 'F#4', 'F4',
                   'E4', 'Eb4', 'D4', 'C4', 'B3', 'Bb3', 'A3', 'G3']
        for n in notes_d:
            raw = generate_square(note_freq(n), 0.07, 0.22)
            death_bytes += apply_envelope(raw, attack=0.005, decay=0.02,
                                          sustain_level=0.5, release=0.02)
        death_bytes += generate_noise(0.4, 0.15)
        death_bytes += generate_silence(0.1)
        self._sfx['death'] = pygame.mixer.Sound(buffer=death_bytes)

        # --- victory: ascending major fanfare ---
        victory_bytes = b''
        for n, dur in [('C4', 0.2), ('E4', 0.2), ('G4', 0.2), ('C5', 0.4)]:
            raw = generate_square(note_freq(n), dur, 0.22)
            victory_bytes += apply_envelope(raw, attack=0.01, decay=0.04,
                                             sustain_level=0.7, release=0.04)
        # Final chord: C5+E5+G5 mixed
        chord_dur = 0.8
        c5 = generate_square(note_freq('C5'), chord_dur, 0.14)
        e5 = generate_square(note_freq('E5'), chord_dur, 0.14)
        g5 = generate_square(note_freq('G5'), chord_dur, 0.14)
        chord = mix_samples(c5, e5, g5)
        chord = apply_envelope(chord, attack=0.02, decay=0.1,
                                sustain_level=0.8, release=0.15)
        victory_bytes += chord
        self._sfx['victory'] = pygame.mixer.Sound(buffer=victory_bytes)

        # --- item_pickup: quick ascending ping ---
        pickup_bytes = b''
        for n, dur in [('C5', 0.07), ('G5', 0.10)]:
            raw = generate_square(note_freq(n), dur, 0.20)
            pickup_bytes += apply_envelope(raw, attack=0.005, decay=0.02,
                                            sustain_level=0.5, release=0.03)
        self._sfx['item_pickup'] = pygame.mixer.Sound(buffer=pickup_bytes)

        # --- score_up: three ascending notes ---
        score_bytes = b''
        for n, dur in [('C5', 0.09), ('E5', 0.09), ('G5', 0.14)]:
            raw = generate_square(note_freq(n), dur, 0.20)
            score_bytes += apply_envelope(raw, attack=0.005, decay=0.02,
                                           sustain_level=0.6, release=0.03)
        self._sfx['score_up'] = pygame.mixer.Sound(buffer=score_bytes)

        # --- pod_launch: rising sine sweep + noise ---
        n_samples = int(SAMPLE_RATE * 1.5)
        buf = array.array('h')
        phase_acc = 0.0
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = 80.0 + (800.0 - 80.0) * (t / 1.5)
            attack_env = min(1.0, t / 0.2)
            release_env = max(0.0, 1.0 - max(0.0, t - 1.2) / 0.3)
            env = attack_env * release_env
            phase_acc += 2.0 * math.pi * freq / SAMPLE_RATE
            val = max(-32768, min(32767, int(32767 * 0.25 * env * math.sin(phase_acc))))
            buf.append(val)
        launch_bytes = buf.tobytes()
        launch_bytes += generate_noise(0.4, 0.18)
        self._sfx['pod_launch'] = pygame.mixer.Sound(buffer=launch_bytes)

        # --- incinerator_warning: two short beeps ---
        warn_bytes = b''
        for _ in range(2):
            raw = generate_square(note_freq('A5'), 0.10, 0.22)
            warn_bytes += apply_envelope(raw, attack=0.005, decay=0.01,
                                          sustain_level=0.8, release=0.02)
            warn_bytes += generate_silence(0.08)
        self._sfx['incinerator_warning'] = pygame.mixer.Sound(buffer=warn_bytes)

        # --- incinerator_critical: rapid beeping ---
        crit_bytes = b''
        for _ in range(6):
            raw = generate_square(note_freq('A5'), 0.05, 0.24)
            crit_bytes += apply_envelope(raw, attack=0.003, decay=0.01,
                                          sustain_level=0.8, release=0.01)
            crit_bytes += generate_silence(0.04)
        self._sfx['incinerator_critical'] = pygame.mixer.Sound(buffer=crit_bytes)

        # --- ceo_ejection: descending whoosh ---
        eject_n = int(SAMPLE_RATE * 0.8)
        eject_buf = array.array('h')
        eject_phase = 0.0
        for i in range(eject_n):
            t = i / SAMPLE_RATE
            freq = 1000.0 - (1000.0 - 100.0) * (t / 0.8)
            env = max(0.0, 1.0 - t / 0.8)
            eject_phase += freq / SAMPLE_RATE
            saw = 2.0 * (eject_phase % 1.0) - 1.0
            val = max(-32768, min(32767, int(32767 * 0.22 * env * saw)))
            eject_buf.append(val)
        eject_bytes = eject_buf.tobytes()
        eject_bytes += generate_noise(0.15, 0.12)
        self._sfx['ceo_ejection'] = pygame.mixer.Sound(buffer=eject_bytes)

        # --- door_slam: noise burst with sharp attack ---
        slam_bytes = generate_noise(0.15, 0.30)
        slam_bytes = apply_envelope(slam_bytes, attack=0.002, decay=0.05,
                                     sustain_level=0.1, release=0.08)
        self._sfx['door_slam'] = pygame.mixer.Sound(buffer=slam_bytes)

        # --- intercom: ascending two-note chime ---
        intercom_bytes = b''
        for n, dur in [('E5', 0.10), ('A5', 0.14)]:
            raw = generate_sine(note_freq(n), dur, 0.22)
            intercom_bytes += apply_envelope(raw, attack=0.01, decay=0.03,
                                              sustain_level=0.6, release=0.05)
        self._sfx['intercom'] = pygame.mixer.Sound(buffer=intercom_bytes)

        # --- button_press: square blip ---
        btn_raw = generate_square(note_freq('B5'), 0.05, 0.18)
        btn_bytes = apply_envelope(btn_raw, attack=0.003, decay=0.01,
                                    sustain_level=0.5, release=0.02)
        self._sfx['button_press'] = pygame.mixer.Sound(buffer=btn_bytes)

        # --- electric_shock: tremolo noise burst ---
        shock_n = int(SAMPLE_RATE * 0.3)
        shock_buf = array.array('h')
        for i in range(shock_n):
            t = i / SAMPLE_RATE
            tremolo = 0.5 + 0.5 * math.sin(2.0 * math.pi * 40.0 * t)
            val = int(32767 * 0.25 * tremolo * random.uniform(-1.0, 1.0))
            shock_buf.append(val)
        self._sfx['electric_shock'] = pygame.mixer.Sound(buffer=shock_buf.tobytes())

        # --- unlock: two metallic clicks ---
        unlock_bytes = b''
        for _ in range(2):
            raw = generate_square(note_freq('C6'), 0.03, 0.20)
            unlock_bytes += apply_envelope(raw, attack=0.002, decay=0.01,
                                            sustain_level=0.3, release=0.01)
            unlock_bytes += generate_silence(0.05)
        self._sfx['unlock'] = pygame.mixer.Sound(buffer=unlock_bytes)
