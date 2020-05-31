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
from colored import fg, bg, attr
import secrets

def green_text(string):
    print(str(fg('white')) + str(bg('green')) + str(string) + str(attr('reset')))


def red_text(string):
    print(str(fg('white')) + str(bg('red')) + str(string) + str(attr('reset')))


def yellow_text(string):
    print(str(fg('white')) + str(bg('yellow')) + str(string) + str(attr('reset')))

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
        yellow_text(url)
        downloaded = urlopen(url)
        yellow_text("Status-Code: " + str(downloaded.getcode()))
        output = downloaded.read()
        this_str = output.decode('utf-8')
        return this_str

    def download_file_get_string_replace_quotes_and_newlines (self, url):
        this_str = self.download_file_get_string(url)
        this_str = this_str.replace('"', '')
        this_str = this_str.replace("\n", '')

    def random_element_from_array(self, array):
        return secrets.choice(array)

class Features():
    def __init__ (self, interact, controlkeyboard):
        self.interact = interact
        self.basefeatures = BaseFeatures()
        self.controlkeyboard = controlkeyboard
        self.radio_streams = {
            "radio eins": "https://www.radioeins.de/live.m3u",
            "eins": "https://www.radioeins.de/live.m3u",
            "sachsen radio": "http://avw.mdr.de/streams/284280-0_mp3_high.m3u"
        }

    def grenzwert(self):
        self.interact.talk("Seh ich aus wie WolframAlpha? Diese Aufgabe ist mir viel zu schwer")

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
        array = [
            "Ich kann mich aktuell nicht beklagen. Wahrscheinlich deshalb, weil ich nur eine Maschine bin und gar nichts fühle.",
            "Wenn ich ganz tief in mich schaue, sehe ich nur Nullen und Einsen",
            "Mein aktueller Status ist in Ordnung, danke der Nachfrage"
        ]

        self.interact.talk(self.basefeatures.random_element_from_array(array))

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

    def talk_weather_tomorrow (self, orig_place):
        place = orig_place[0].upper() + orig_place[1:]

        warmmorgen = self.get_temperature_tomorrow(place)
        luftfeuchtemorgen = self.get_humidity_tomorrow(place)
        if str(warmmorgen) == "None"  or str(luftfeuchtemorgen) == "None":
            self.interact.talk("Keine Ahnung, irgendwas ist schiefgelaufen beim Holen der Wetterdaten")
        else:
            self.interact.talk("Morgen wird es " + str(warmmorgen) + " mit " + str(luftfeuchtemorgen) + " lufteuchtigkeit")

    def solve_equation (self):
        self.controlkeyboard.hotkey('home')
        self.controlkeyboard.hotkey('shift', 'end')
        self.controlkeyboard.hotkey('ctrl', 'c')
        self.interact.vad_audio.stream.stop_stream()
        os.system('qalc -t $(xsel --clipboard) | sed -e "s/ or / oder /"')
        os.system('qalc -t $(xsel --clipboard) | sed -e "s/ or / oder /" | sed -e "s/-/ minus /" | pico2wave --lang de-DE --wave /tmp/Test.wav ; play /tmp/Test.wav; rm /tmp/Test.wav')
        self.interact.vad_audio.stream.start_stream()

    def read_aloud(self):
        self.controlkeyboard.hotkey('ctrl', 'a')
        self.controlkeyboard.hotkey('ctrl', 'c')

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
                "5 von 4 Leuten haben Probleme mit Mathematik!",
                "Sagt ein Mathestudent zum Kommilitonen: Ich habe gehört, die Ehe des Professors soll sehr unglücklich sein! Meint der andere: Das wundert mich nicht. Er ist Mathematiker, und sie unberechenbar.",
                "Was ist die Lieblingsbeschäftigung von Bits und Bytes? Busfahren.",
                "Der kürzeste Programmiererwitz: Gleich bin ich fertig!",
                "Ein Informatiker schiebt einen Kinderwagen durch den Park. Kommt ein älteres Ehepaar: Junge oder Mädchen? Da sagt der Informatiker: Richtig!"
        ]

        self.interact.talk(self.basefeatures.random_element_from_array(array))

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
    def __init__ (self, vad_audio, controlkeyboard):
        self.vad_audio = vad_audio
        self.controlkeyboard = controlkeyboard

    def talk(self, something):
        yellow_text(str(something))
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
        self.controlkeyboard.hotkey("ctrl", "v")

class ControlKeyboard():
    def hotkey(self, *argv):
        for arg in argv:
            yellow_text("Pressing `" + str(arg) + "`")
        pyautogui.hotkey(*argv)

class GUITools():
    def __init__ (self, interact, controlkeyboard):
        self.interact = interact
        self.controlkeyboard = controlkeyboard

    def start_browser(self):
        os.system("firefox")

    def toggle_volume(self):
        self.interact.talk("OK")
        os.system("amixer set Master toggle")

    def volume_up (self):
        self.controlkeyboard.hotkey('volumeup')

    def volume_down (self):
        self.controlkeyboard.hotkey('volumedown')

    def say_current_window(self):
        self.interact.talk(self.get_current_window())

    def switch_window (self):
        self.controlkeyboard.hotkey('alt', 'tab')
        time.sleep(1)
        self.say_current_window()

    def next_tab (self):
        self.controlkeyboard.hotkey('ctrl', 'tab')
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
        self.controlkeyboard.hotkey('ctrl', 'w')

    def previous_tab(self):
        self.controlkeyboard.hotkey('ctrl', 'shift', 'tab')
        time.sleep(1)
        self.interact.talk(self.get_current_window())

    def mark_and_delete_all(self):
        self.controlkeyboard.hotkey('ctrl', 'a')
        self.controlkeyboard.hotkey('del')

    def repeat (self):
        self.controlkeyboard.hotkey('ctrl', 'y')

    def new_tab(self):
        self.controlkeyboard.hotkey('ctrl', 't')

    def new_window(self):
        self.controlkeyboard.hotkey('ctrl', 'n')

    def copy (self):
        self.controlkeyboard.hotkey('ctrl', 'c')

    def select_all(self):
        self.controlkeyboard.hotkey('ctrl', 'a')

    def undo (self):
        self.controlkeyboard.hotkey('ctrl', 'z')

    def cut(self):
        self.controlkeyboard.hotkey('ctrl', 'x')

    def delete(self):
        self.controlkeyboard.hotkey('del')

    def select_current_line(self):
        self.controlkeyboard.hotkey('home')
        self.controlkeyboard.hotkey('shift', 'end')

    def delete_current_line (self):
        self.select_current_line()
        self.delete()

    def paste (self):
        self.controlkeyboard.hotkey('ctrl', 'v')

    def delete_last_word(self):
        self.controlkeyboard.hotkey('ctrl', 'backspace')

    def press_enter(self):
        self.controlkeyboard.hotkey('enter')

    def press_space(self):
        self.controlkeyboard.hotkey('space')

class AnalyzeAudio ():
    def __init__ (self, guitools, interact, features):
        self.guitools = guitools
        self.interact = interact
        self.features = features

        self.regexes = {
            "^leiser$": self.guitools.volume_down,
            "^lauter$": self.guitools.volume_up,
            "^(?:(?:kannst du mich hören)|(?:hörst du mich))$": self.interact.can_you_hear_me,
            "^star?te internet$": self.guitools.start_browser,
            "^alles vorlesen$": self.features.read_aloud,
            "^löschen$": self.guitools.delete,
            "^aktuelle zeile (?:auswählen|markieren)$": self.guitools.select_current_line,
            "^aktuelle zeile löschen$": self.guitools.delete_current_line,
            "^aus\s*rechnen$": self.features.solve_equation,
            "^wieder\s*holen$": self.guitools.repeat,
            "^kopieren$": self.guitools.copy,
            "^einfügen$": self.guitools.paste,
            "^aus\s*schneiden$": self.guitools.cut,
            "^alles (markieren|auswählen)$": self.guitools.select_all,
            "^alle fenster$": self.guitools.all_windows,
            "^eingabe\s*taster?$": self.guitools.press_enter,
            "^alles löschen$": self.guitools.mark_and_delete_all,
            ".{0,20}fenster.*(vordergrund|fokus)$": self.guitools.say_current_window,
            "^schließe ta[bp]$": self.guitools.close_tab,
            "^(?:wechsel (?:fenster|elster))|(?:(?:elster|fenster) wechseln)$": self.guitools.switch_window,
            "^wie geht es dir$": self.features.how_are_you,
            ".*ist.*grenzwert.*$": self.features.grenzwert,
            "^neu(?:er)? ta[bp]$": self.guitools.new_tab,
            "^nächster ta[bp]?$": self.guitools.next_tab,
            "^letzter ta[bp]$": self.guitools.previous_tab,
            "^neues (?:fenster|elster)$": self.guitools.new_window,
            ".*ende.*dich.*selbst.*": self.features.suicide,
            "^(?:ab\s*spielen|spiele ab|pausieren)$": self.guitools.press_space,
            "^(?:lautlos|wieder laut)$": self.guitools.toggle_volume,
            "^rückgängig$": self.guitools.undo,
            ".*ein(?:en)? witz": self.features.tell_joke,
            "^letztes wort löschen$": self.guitools.delete_last_word,
            "^spieler? radio (.*)$": {"fn": "self.features.play_radio", "param": "text"},
            "^.*wetter morgen(?: in (.*))?$": {"fn": "self.features.talk_weather_tomorrow", "param": "m.group(1) or 'Dresden'"}
        }

    def do_what_i_just_said(self, text):
        m = REMatcher(text)

        done_something = False

        for regex in self.regexes:
            if m.match(regex):
                if type(self.regexes[regex]) is dict:
                    fn_name = self.regexes[regex]["fn"]
                    param = self.regexes[regex]["param"]
                    eval(fn_name + "(" + param + ")")
                else:
                    self.regexes[regex]()
                done_something = True

        return done_something

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

    controlkeyboard = ControlKeyboard()
    interact = Interaction(vad_audio, controlkeyboard)
    textreplacements = TextReplacements()
    features = Features(interact, controlkeyboard)
    guitools = GUITools(interact, controlkeyboard)

    analyzeaudio = AnalyzeAudio(guitools, interact, features)

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
                green_text("Recognized: >>>%s<<<" % text)

                done_something = analyzeaudio.do_what_i_just_said(text)

                if not done_something:
                    if 'formel eingeben' in text or 'formel ein geben' in text or 'formell eingeben' in text or 'formell ein geben' in text:
                        interact.talk("Sprich zeichen für zeichen ein und sage wenn fertig 'wieder text eingeben'")
                        is_formel = True
                        interact.play_sound("bleep.wav")
                    elif is_formel and 'text eingeben' in text:
                        interact.talk("Ab jetzt wieder Text")
                        is_formel = False
                        interact.play_sound("bleep.wav")
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
