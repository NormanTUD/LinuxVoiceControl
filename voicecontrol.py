# -- coding: utf8 --

import time, logging
from datetime import datetime
import threading, collections, queue, os, os.path
import deepspeech
import numpy as np
import pyaudio
import wave
import webrtcvad
from halo import Halo
from scipy import signal
import sys
import pyautogui 
import pyperclip
from subprocess import check_output
import time
from urllib.request import urlopen
import random
import wmctrl
import argparse
import os.path
import re

def red_text(string):
    print("\u001b[41m\u001b[37;1m" + string + "\033[0m")

logging.basicConfig(level=20)

class REMatcher(object):
    def __init__(self, matchstring):
        self.matchstring = matchstring

    def match(self,regexp):
        self.rematch = re.match(regexp, self.matchstring)
        return bool(self.rematch)

    def group(self,i):
        return self.rematch.group(i)

class BaseFeatures():
    def download_file_get_string (self, url):
        red_text(url)
        output = urlopen(url).read()
        this_str = output.decode('utf-8')
        return this_str

    def download_file_get_string_replace_quotes_and_newlines (self, url):
        this_str = self.download_file_get_string(url)
        this_str = this_str.replace('"', '')
        this_str = this_str.replace("\n", '')

class Features():
    def __init__ (self, interact):
        self.interact = interact
        self.basefeatures = BaseFeatures()
        self.radio_streams = {
            "radio eins": "https://www.radioeins.de/live.m3u",
            "sachsen radio": "http://avw.mdr.de/streams/284280-0_mp3_high.m3u"
        }

    def play_radio (self, text):
        radioname = '';

        m = REMatcher(text)

        if m.match(r"spieler? radio (.+)"):
            radioname = m.group(1)

        if radioname in self.radio_streams:
            radio_stream = self.radio_streams[radioname]
            self.interact.talk("Ich spiele " + str(radioname) + " ab, drücke S T R G C um abzubrechen")
            self.interact.vad_audio.stream.stop_stream()
            os.system("play " + str(radio_stream))
            self.interact.vad_audio.stream.start_stream()
        else:
            self.interact.talk("Das Radio mit dem Namen " + str(radioname) + " ist mir nicht bekannt")

    def how_are_you(self):
        self.interact.talk("Ich kann mich aktuell nicht beklagen. Wahrscheinlich deshalb, weil ich nur eine Maschine bin und gar nichts fühle.")

    def suicide (self):
        self.interact.talk("ok, ich beende mich selbst und höre nicht mehr weiter zu!")
        sys.exit(0)

    def get_temperature_tomorrow (self, place):
        url = 'https://wttr.in/' + str(place) + '?format="%C"&lang=de'
        this_str = self.basefeatures.download_file_get_string_replace_quotes_and_newlines(url)
        return this_str

    def get_humidity_tomorrow (self, place):
        url = 'https://wttr.in/' + str(place) + '?format="%h"&lang=de'
        this_str = self.basefeatures.download_file_get_string_replace_quotes_and_newlines(url)
        return this_str

    def talk_weather_tomorrow (self, place):
        warmmorgen = self.get_temperature_tomorrow(place)
        luftfeuchtemorgen = self.get_humidity_tomorrow(place)
        if str(warmmorgen) == "None"  or str(luftfeuchtemorgen) == "None":
            self.interact.talk("Keine Ahnung, irgendwas ist schiefgelaufen beim Holen der Wetterdaten")
        else:
            self.interact.talk("Morgen wird es " + str(warmmorgen) + " mit " + str(luftfeuchtemorgen) + " lufteuchtigkeit")

    def solve_equation (self):
        pyautogui.hotkey('home')
        pyautogui.hotkey('shift', 'end')
        pyautogui.hotkey('ctrl', 'c')
        self.interact.vad_audio.stream.stop_stream()
        os.system('qalc -t $(xsel --clipboard) | sed -e "s/ or / oder /"')
        os.system('qalc -t $(xsel --clipboard) | sed -e "s/ or / oder /" | sed -e "s/-/ minus /" | pico2wave --lang de-DE --wave /tmp/Test.wav ; play /tmp/Test.wav; rm /tmp/Test.wav')
        self.interact.vad_audio.stream.start_stream()

    def read_aloud(self):
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.hotkey('ctrl', 'c')

        self.interact.vad_audio.stream.stop_stream()
        os.system('xsel --clipboard | tr "\n" " " | pico2wave --lang de-DE --wave /tmp/Test.wav ; play /tmp/Test.wav; rm /tmp/Test.wav')
        self.interact.vad_audio.stream.start_stream()

    def tell_joke(self):
        array = [
                "Was ist weiß und steht hinter einem Baum? Eine scheue Milch",
                "Gott sprach: Es werde Licht! Tschack Norris antwortete! Sag bitte!",
                "Kommt ein Wektor zur Drogenberatung: Hilfe, ich bin line ar abhängig.",
                "Was macht ein Mathematiker im Garten? Wurzeln ziehen.",
                "Mathematiker sterben nie! sie verlieren nur einige ihrer Funktionen.",
                "Wie viele Informatiker braucht man, um eine Glühbirne zu wechseln? Keinen, das ist ein Hardwärproblem!",
                "Linux wird nie das meistinstallierte Betriebssystem sein, wenn man bedenkt, wie oft man Windows neu installieren muss!",
                "Wie viele Glühbirnen braucht man, um eine Glühbirne zu wechseln? Genau zwei, die Alte und die Neue.",
                "5 von 4 Leuten haben Probleme mit Mathematik!"
        ]

        self.interact.talk(random.choice(array))

class TextReplacements():
    def replace_in_text_mode (self, text):
        text = text.replace("komma", ",")
        text = text.replace("ausrufezeichen", "!")
        text = text.replace("punkt", ".")
        text = text.replace("neue zeile", "\n")
        text = text.replace("neuer zeile", "\n")
        text = text.replace("neu zeile", "\n")
        text = text.replace("leerzeichen", " ")
        text = text.replace("geschweifte klammer auf", "{")
        text = text.replace("geschweifte klammer zu", "}")
        text = text.replace("eckige klammer auf", "[")
        text = text.replace("eckige klammer zu", "]")
        text = text.replace("klammer auf", "(")
        text = text.replace("klammer zu", ")")
        text = text.replace(" ,", ",")
        text = text.replace(" !", "!")
        text = text.replace(" .", ".")
        text = text.replace("  ", " ")
        text = text.replace("\n ", "\n")
        text = text.replace(" \n", "\n")
        return text

    def replace_in_formula_mode(self, text):
        text = text.replace("null", "0")
        text = text.replace("eins", "1")
        text = text.replace("zwei", "2")
        text = text.replace("drei", "3")
        text = text.replace("vier", "4")
        text = text.replace("fünf", "5")
        text = text.replace("sechs", "6")
        text = text.replace("sieben", "7")
        text = text.replace("acht", "8")
        text = text.replace("neun", "9")
        text = text.replace("komma", ",")
        text = text.replace("plus", "+")
        text = text.replace("wurzel", "sqrt ")
        text = text.replace(" ex ", "x")
        text = text.replace("fluss", "+")
        text = text.replace("hoch", "^")
        text = text.replace("minus", "-")
        text = text.replace("gleich", "=")
        text = text.replace("mal", "*")
        text = text.replace("geteiltdurch", "/")
        text = text.replace("geteilt durch", "/")
        text = text.replace(" ", "")
        text = text.replace("geschweifte klammer auf", "{")
        text = text.replace("geschweifteklammerauf", "{")
        text = text.replace("geschweifte klammer zu", "}")
        text = text.replace("geschweifteklammerzu", "}")
        text = text.replace("eckige klammer auf", "[")
        text = text.replace("eckigeklammerauf", "[")
        text = text.replace("eckige klammer zu", "]")
        text = text.replace("eckigeklammerzu", "]")
        text = text.replace("klammer auf", "(")
        text = text.replace("klammerauf", "(")
        text = text.replace("klammer zu", ")")
        text = text.replace("klammerzu", ")")
        return text

class Interaction():
    def __init__ (self, vad_audio):
        self.vad_audio = vad_audio

    def talk(self, something):
        red_text(str(something))
        self.vad_audio.stream.stop_stream()
        os.system('pico2wave --lang de-DE --wave /tmp/Test.wav "' + str(something) + '" ; play /tmp/Test.wav; rm /tmp/Test.wav')
        self.vad_audio.stream.start_stream()

    def can_you_hear_me(self):
        self.talk("Ja, kann ich")

    def play_sound (self, path):
        self.vad_audio.stream.stop_stream()
        if os.path.isfile(path):
            os.system("play " + path)
        else:
            self.talk("Die Datei " + str(path) + " konnte nicht gefunden werden!")
        self.vad_audio.stream.start_stream()

    def type_unicode(self, word):
        pyperclip.copy(word)
        pyautogui.hotkey("ctrl", "v")

class GUITools():
    def __init__ (self, interact):
        self.interact = interact

    def start_browser(self):
        os.system("firefox")

    def toggle_volume(self):
        self.interact.talk("OK")
        os.system("amixer set Master toggle")

    def volume_up (self):
        pyautogui.hotkey('volumeup')

    def volume_down (self):
        pyautogui.hotkey('volumedown')

    def say_current_window(self):
        self.interact.talk(self.get_current_window())

    def switch_window (self):
        pyautogui.hotkey('alt', 'tab')
        time.sleep(1)
        self.say_current_window()

    def next_tab (self):
        pyautogui.hotkey('ctrl', 'tab')
        time.sleep(1)
        self.say_current_window()

    def get_current_window (self):
        out = check_output(["xdotool", "getwindowfocus", "getwindowname"])
        this_str = out.decode("utf-8")
        return this_str

    def all_windows(self):
        Window = wmctrl.Window
        x = Window.list()
        for wn in Window.list():
            self.interact.talk(wn.wm_name)

    def close_tab(self):
        pyautogui.hotkey('ctrl', 'w')

    def previous_tab(self):
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        time.sleep(1)
        self.interact.talk(self.get_current_window())

    def mark_and_delete_all(self):
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.hotkey('del')

    def repeat (self):
        pyautogui.hotkey('ctrl', 'y')

    def new_tab(self):
        pyautogui.hotkey('ctrl', 't')

    def new_window(self):
        pyautogui.hotkey('ctrl', 'n')

    def copy (self):
        pyautogui.hotkey('ctrl', 'c')

    def select_all(self):
        pyautogui.hotkey('ctrl', 'a')

    def undo (self):
        pyautogui.hotkey('ctrl', 'z')

    def cut(self):
        pyautogui.hotkey('ctrl', 'x')

    def delete(self):
        pyautogui.hotkey('del')

    def mark_current_line(self):
        pyautogui.hotkey('home')
        pyautogui.hotkey('shift', 'end')

    def paste (self):
        pyautogui.hotkey('ctrl', 'v')

    def delete_last_word(self):
        pyautogui.hotkey('ctrl', 'backspace')

    def press_enter(self):
        pyautogui.hotkey('enter')

    def press_space(self):
        pyautogui.hotkey('space')

class Audio(object):
    """Streams raw audio from microphone. Data is received in a separate thread, and stored in a buffer, to be read from."""

    FORMAT = pyaudio.paInt16
    # Network/VAD rate-space
    RATE_PROCESS = 16000
    CHANNELS = 1
    BLOCKS_PER_SECOND = 50

    def __init__(self, callback=None, device=None, input_rate=RATE_PROCESS, file=None):
        def proxy_callback(in_data, frame_count, time_info, status):
            #pylint: disable=unused-argument
            if self.chunk is not None:
                in_data = self.wf.readframes(self.chunk)
            callback(in_data)
            return (None, pyaudio.paContinue)
        if callback is None: callback = lambda in_data: self.buffer_queue.put(in_data)
        self.buffer_queue = queue.Queue()
        self.device = device
        self.input_rate = input_rate
        self.sample_rate = self.RATE_PROCESS
        self.block_size = int(self.RATE_PROCESS / float(self.BLOCKS_PER_SECOND))
        self.block_size_input = int(self.input_rate / float(self.BLOCKS_PER_SECOND))
        self.pa = pyaudio.PyAudio()

        kwargs = {
            'format': self.FORMAT,
            'channels': self.CHANNELS,
            'rate': self.input_rate,
            'input': True,
            'frames_per_buffer': self.block_size_input,
            'stream_callback': proxy_callback,
        }

        self.chunk = None
        # if not default device
        if self.device:
            kwargs['input_device_index'] = self.device
        elif file is not None:
            self.chunk = 320
            self.wf = wave.open(file, 'rb')

        self.stream = self.pa.open(**kwargs)
        self.stream.start_stream()

    def resample(self, data, input_rate):
        """
        Microphone may not support our native processing sampling rate, so
        resample from input_rate to RATE_PROCESS here for webrtcvad and
        deepspeech

        Args:
            data (binary): Input audio stream
            input_rate (int): Input audio rate to resample from
        """
        data16 = np.fromstring(string=data, dtype=np.int16)
        resample_size = int(len(data16) / self.input_rate * self.RATE_PROCESS)
        resample = signal.resample(data16, resample_size)
        resample16 = np.array(resample, dtype=np.int16)
        return resample16.tostring()

    def read_resampled(self):
        """Return a block of audio data resampled to 16000hz, blocking if necessary."""
        return self.resample(data=self.buffer_queue.get(),
                             input_rate=self.input_rate)

    def read(self):
        """Return a block of audio data, blocking if necessary."""
        return self.buffer_queue.get()

    def destroy(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()

    frame_duration_ms = property(lambda self: 1000 * self.block_size // self.sample_rate)

    def write_wav(self, filename, data):
        logging.info("write wav %s", filename)
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        # wf.setsampwidth(self.pa.get_sample_size(FORMAT))
        assert self.FORMAT == pyaudio.paInt16
        wf.setsampwidth(2)
        wf.setframerate(self.sample_rate)
        wf.writeframes(data)
        wf.close()


class VADAudio(Audio):
    """Filter & segment audio with voice activity detection."""

    def __init__(self, aggressiveness=3, device=None, input_rate=None, file=None):
        super().__init__(device=device, input_rate=input_rate, file=file)
        self.vad = webrtcvad.Vad(aggressiveness)

    def frame_generator(self):
        """Generator that yields all audio frames from microphone."""

        if self.input_rate == self.RATE_PROCESS:
            while True:
                yield self.read()
        else:
            while True:
                yield self.read_resampled()

    def vad_collector(self, padding_ms=300, ratio=0.75, frames=None):
        """Generator that yields series of consecutive audio frames comprising each utterence, separated by yielding a single None.
            Determines voice activity by ratio of frames in padding_ms. Uses a buffer to include padding_ms prior to being triggered.
            Example: (frame, ..., frame, None, frame, ..., frame, None, ...)
                      |---utterence---|        |---utterence---|
        """


        if frames is None: frames = self.frame_generator()
        num_padding_frames = padding_ms // self.frame_duration_ms
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False

        for frame in frames:
            if len(frame) < 640:
                return

            is_speech = self.vad.is_speech(frame, self.sample_rate)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > ratio * ring_buffer.maxlen:
                    triggered = True
                    for f, s in ring_buffer:
                        yield f
                    ring_buffer.clear()

            else:
                yield frame
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                if num_unvoiced > ratio * ring_buffer.maxlen:
                    triggered = False
                    yield None
                    ring_buffer.clear()


def main(ARGS):
    # Load DeepSpeech model
    if os.path.isdir(ARGS.model):
        model_dir = ARGS.model
        ARGS.model = os.path.join(model_dir, 'output_graph.pb')
        ARGS.scorer = os.path.join(model_dir, ARGS.scorer)

    print('Initializing model...')
    logging.info("ARGS.model: %s", ARGS.model)
    model = deepspeech.Model(ARGS.model)
    if ARGS.scorer:
        logging.info("ARGS.scorer: %s", ARGS.scorer)
        model.enableExternalScorer(ARGS.scorer)

    # Start audio with VAD
    vad_audio = VADAudio(aggressiveness=ARGS.vad_aggressiveness,
                         device=ARGS.device,
                         input_rate=ARGS.rate,
                         file=ARGS.file)

    interact = Interaction(vad_audio)
    textreplacements = TextReplacements()
    features = Features(interact)
    guitools = GUITools(interact)

    print("Sage 'mitschreiben', damit mitgeschrieben wird")
    frames = vad_audio.vad_collector()

    # Stream from microphone to DeepSpeech using VAD
    spinner = None
    if not ARGS.nospinner:
        spinner = Halo(spinner='line')
    stream_context = model.createStream()

    wav_data = bytearray()
    starte_schreiben = False
    is_formel = False

    for frame in frames:
        if frame is not None:
            if spinner:
                spinner.start()
            logging.debug("streaming frame")
            stream_context.feedAudioContent(np.frombuffer(frame, np.int16))
            if ARGS.savewav: wav_data.extend(frame)
        else:
            if spinner:
                spinner.stop()
            logging.debug("end utterence")
            if ARGS.savewav:
                vad_audio.write_wav(os.path.join(ARGS.savewav, datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")), wav_data)
                wav_data = bytearray()
            text = stream_context.finishStream()

            text = " ".join(text.split())
            if not text == "":
                red_text("Recognized: >>>%s<<<" % text)
                if text == 'welches fenster ist im vordergrund' or ("fenster" in text and "fokus" in text):
                    guitools.say_current_window()
                elif text == 'wechsel fenster' or text == 'fenster wechseln' or text == 'elster wechseln' or text == 'fenster wechsel' or text == 'ester wechseln':
                    guitools.switch_window()
                elif text == 'nächster tab' or text == 'nächster ta'  or text == 'nächster tap':
                    guitools.next_tab()
                elif 'was ist' in text and 'grenzwert' in text:
                    interact.talk("Seh ich aus wie WolframAlpha? Diese Aufgabe ist mir viel zu schwer")
                elif 'formel eingeben' in text or 'formel ein geben' in text or 'formell eingeben' in text or 'formell ein geben' in text:
                    interact.talk("Sprich zeichen für zeichen ein und sage wenn fertig 'wieder text eingeben'")
                    is_formel = True
                    interact.play_sound("bleep.wav")
                elif is_formel and 'text eingeben' in text:
                    interact.talk("Ab jetzt wieder Text")
                    is_formel = False
                    interact.play_sound("bleep.wav")
                elif text == 'letzter tab' or text == 'letzter ta'  or text == 'letzter tap':
                    guitools.previous_tab()
                elif "alle fenster" in text:
                    guitools.all_windows()
                elif text == 'schließe tab' or text == 'schließe tap':
                    guitools.close_tab()
                elif text == 'neuer tab' or text == 'neuer tap':
                    guitools.new_tab()
                elif text == 'neues fenster':
                    guitools.new_window()
                elif "ende" in text and "selbst" in text:
                    features.suicide()
                elif text == 'lautlos' or text == 'wieder laut':
                    guitools.toggle_volume()
                elif text == 'lauter':
                    guitools.volume_up()
                elif text == 'leiser':
                    guitools.volume_down()
                elif text == 'kannst du mich hören':
                    interact.can_you_hear_me()
                elif text == 'abspielen' or text == 'spiel ab':
                    guitools.press_space()
                elif text == 'wie wird das wetter morgen' or ("wetter" in text and "morgen" in text):
                    features.talk_weather_tomorrow("Dresden")
                elif text == 'starte internet' or text == 'state internet':
                    guitools.start_browser()
                elif text == 'alles markieren':
                    guitools.select_all()
                elif text == 'eingabetaste' or text == 'eingabe taster' or text == 'ein abtaster' or text == 'eingabe taste':
                    guitools.press_enter()
                elif text == 'alles löschen':
                    guitools.mark_and_delete_all()
                elif 'wie geht es dir' == text:
                    features.how_are_you()
                elif 'spiele radio' in text or 'spieler radio' in text:
                    features.play_radio(text)
                elif text == 'löschen':
                    guitools.delete()
                elif 'rückgängig' in text and 'letzte' in text and 'aktion' in text:
                    guitools.undo()
                elif text == 'aktuelle zeile markieren':
                    guitools.mark_current_line()
                elif text == 'aktuelle zeile als gleichung sehen und lösen' or "ausrechnen" in text:
                    features.solve_equation()
                elif text == 'wiederholen':
                    guitools.repeat()
                elif text == 'kopieren':
                    guitools.copy()
                elif text == 'einfügen':
                    guitools.paste()
                elif 'ein' in text and 'witz' in text:
                    features.tell_joke()
                elif text == 'alles vorlesen':
                    features.read_aloud()
                elif text == 'ausschneiden':
                    guitools.cut()
                elif text == 'letztes wort löschen' or text == 'letztes wort laschen' or text == 'letztes wort lerchen':
                    guitools.delete_last_word()
                elif starte_schreiben:
                    if text == 'nicht mehr mitschreiben' or text == 'nicht mehr mit schreiben' or text == 'nicht mit schreiben':
                        print("Es wird nicht mehr mitgeschrieben")
                        interact.play_sound("line_end.wav")
                        starte_schreiben = False
                    elif is_formel:
                        text = textreplacements.replace_in_formula_mode(text)
                        interact.type_unicode(text)
                    elif text:
                        text = text + " "
                        text = textreplacements.replace_in_text_mode(text)
                        interact.type_unicode(text)
                else:
                    if text == "mitschreiben" or text == "mit schreiben":
                        starte_schreiben = True
                        print("Starte schreiben")
                        interact.play_sound("bleep.wav")
                    else:
                        print("Sage 'mitschreiben', damit mitgeschrieben wird")

            stream_context = model.createStream()

if __name__ == '__main__':
    DEFAULT_SAMPLE_RATE = 16000

    parser = argparse.ArgumentParser(description="Stream from microphone to DeepSpeech using VAD")

    parser.add_argument('-v', '--vad_aggressiveness', type=int, default=3,
                        help="Set aggressiveness of VAD: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive. Default: 3")
    parser.add_argument('--nospinner', action='store_true',
                        help="Disable spinner")
    parser.add_argument('-w', '--savewav',
                        help="Save .wav files of utterences to given directory")
    parser.add_argument('-f', '--file',
                        help="Read from .wav file instead of microphone")

    parser.add_argument('-m', '--model', required=True,
                        help="Path to the model (protocol buffer binary file, or entire directory containing all standard-named files for model)")
    parser.add_argument('-s', '--scorer',
                        help="Path to the external scorer file.")
    parser.add_argument('-d', '--device', type=int, default=None,
                        help="Device input index (Int) as listed by pyaudio.PyAudio.get_device_info_by_index(). If not provided, falls back to PyAudio.get_default_device().")
    parser.add_argument('-r', '--rate', type=int, default=DEFAULT_SAMPLE_RATE,
                        help=f"Input device sample rate. Default: {DEFAULT_SAMPLE_RATE}. Your device may require 44100.")

    ARGS = parser.parse_args()
    if ARGS.savewav: os.makedirs(ARGS.savewav, exist_ok=True)
    main(ARGS)
