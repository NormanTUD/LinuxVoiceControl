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

def get_humidity_tomorrow (place):
    url = 'https://wttr.in/' + str(place) + '?format="%h"&lang=de'
    red_text(url)
    output = urlopen(url).read()
    this_str = output.decode('utf-8')
    this_str = this_str.replace('"', '')
    this_str = this_str.replace("\n", '')
    return this_str

def get_temperature_tomorrow (place):
    url = 'https://wttr.in/' + str(place) + '?format="%C"&lang=de'
    red_text(url)
    output = urlopen(url).read()
    this_str = output.decode('utf-8')
    this_str = this_str.replace('"', '')
    this_str = this_str.replace("\n", '')
    return this_str

def type_unicode(word):
    pyperclip.copy(word)
    pyautogui.hotkey("ctrl", "v")

def red_text(string):
    print("\u001b[41m\u001b[37;1m" + string + "\033[0m")

def talk(something):
    red_text(str(something))
    #os.system("espeak -a 1000 -v german '" + str(something) + "' 2> /dev/null")
    os.system('pico2wave --lang de-DE --wave /tmp/Test.wav "' + str(something) + '" ; play /tmp/Test.wav; rm /tmp/Test.wav')

def hole_aktuelles_fenster ():
    out = check_output(["xdotool", "getwindowfocus", "getwindowname"])
    this_str = out.decode("utf-8")
    return this_str

#sys.exit(1)

logging.basicConfig(level=20)

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
    print("Listening (ctrl-C to exit)...")

    print("Sage 'mitschreiben', damit mitgeschrieben wird")
    frames = vad_audio.vad_collector()

    # Stream from microphone to DeepSpeech using VAD
    spinner = None
    if not ARGS.nospinner:
        spinner = Halo(spinner='line')
    stream_context = model.createStream()
    wav_data = bytearray()
    starte_schreiben = False
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
            done_something = False
            if not text == "":
                red_text("Recognized: >>>%s<<<" % text)
                if text == 'welches fenster ist im vordergrund' or ("fenster" in text and "fokus" in text):
                    talk(hole_aktuelles_fenster())
                    done_something = True
                elif text == 'wechsel fenster' or text == 'fenster wechseln' or text == 'elster wechseln' or text == 'fenster wechsel' or text == 'ester wechseln':
                    pyautogui.hotkey('alt', 'tab')
                    time.sleep(1)
                    talk(hole_aktuelles_fenster())
                    done_something = True
                elif text == 'nächster tab' or text == 'nächster ta'  or text == 'nächster tap':
                    pyautogui.hotkey('ctrl', 'tab')
                    time.sleep(1)
                    talk(hole_aktuelles_fenster())
                    done_something = True
                elif text == 'letzter tab' or text == 'letzter ta'  or text == 'letzter tap':
                    pyautogui.hotkey('ctrl', 'shift', 'tab')
                    time.sleep(1)
                    talk(hole_aktuelles_fenster())
                    done_something = True
                elif text == 'schließe tab' or text == 'schließe tap':
                    pyautogui.hotkey('ctrl', 'w')
                    done_something = True
                elif text == 'neuer tab' or text == 'neuer tap':
                    pyautogui.hotkey('ctrl', 't')
                    done_something = True
                elif text == 'lautlos' or text == 'wieder laut':
                    os.system("amixer set Master toggle")
                    done_something = True
                elif text == 'lauter':
                    pyautogui.hotkey('volumeup')
                    done_something = True
                elif text == 'leiser':
                    pyautogui.hotkey('volumedown')
                    done_something = True
                elif text == 'abspielen' or text == 'spiel ab':
                    pyautogui.hotkey('space')
                    done_something = True
                elif text == 'wie wird das wetter morgen' or ("wetter" in text and "morgen" in text):
                    warmmorgen = get_temperature_tomorrow("Dresden")
                    luftfeuchtemorgen = get_humidity_tomorrow("Dresden")
                    talk("Morgen wird es " + str(warmmorgen) + " mit " + str(luftfeuchtemorgen) + " lufteuchtigkeit")
                    done_something = True
                elif text == 'starte internet' or text == 'state internet':
                    os.system("firefox")
                    done_something = True
                elif text == 'alles markieren':
                    pyautogui.hotkey('ctrl', 'a')
                    done_something = True
                elif text == 'eingabetaste' or text == 'eingabe taster' or text == 'ein abtaster' or text == 'eingabe taste':
                    pyautogui.hotkey('enter')
                    done_something = True
                elif text == 'alles löschen':
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.hotkey('del')
                    done_something = True
                elif text == 'löschen':
                    pyautogui.hotkey('del')
                    done_something = True
                elif 'rückgängig' in text and 'letzte' in text and 'aktion' in text:
                    pyautogui.hotkey('ctrl', 'z')
                    done_something = True
                elif text == 'wiederholen':
                    pyautogui.hotkey('ctrl', 'y')
                    done_something = True
                elif text == 'kopieren':
                    pyautogui.hotkey('ctrl', 'c')
                    done_something = True
                elif text == 'einfügen':
                    pyautogui.hotkey('ctrl', 'v')
                    done_something = True
                elif 'ein' in text and 'witz' in text:
                    array = [
                            "Was ist weiß und steht hinter einem Baum Eine scheue Milch",
                            "Gott sprach: Es werde Licht! Tschack Norris antwortete! Sag bitte!",
                            "Kommt ein Wektor zur Drogenberatung: Hilfe, ich bin line ar abhängig.",
                            "Was macht ein Mathematiker im Garten? Wurzeln ziehen.",
                            "Mathematiker sterben nie! sie verlieren nur einige ihrer Funktionen.",
                            "Wie viele Informatiker braucht man, um eine Glühbirne zu wechseln? Keinen, das ist ein Hardwärproblem!",
                            "Linux wird nie das meistinstallierte Betriebssystem sein, wenn man bedenkt, wie oft man Windows neu installieren muss!",
                            "Wie viele Glühbirnen braucht man, um eine Glühbirne zu wechseln? Genau zwei, die Alte und die Neue.",
                            "5 von 4 Leuten haben Probleme mit Mathematik!"
                    ]

                    talk(random.choice(array))
                elif text == 'alles vorlesen':
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.hotkey('ctrl', 'c')
                    os.system('xsel --clipboard | tr "\n" " " | espeak -a 1000 -v german')
                    done_something = True
                elif text == 'ausschneiden':
                    pyautogui.hotkey('ctrl', 'x')
                    done_something = True
                elif text == 'letztes wort löschen' or text == 'letztes wort laschen' or text == 'letztes wort lerchen':
                    pyautogui.hotkey('ctrl', 'backspace')
                    done_something = True
                elif starte_schreiben:
                    if text == 'nicht mehr mitschreiben' or text == 'nicht mehr mit schreiben' or text == 'nicht mit schreiben':
                        print("Es wird nicht mehr mitgeschrieben")
                        os.system("play line_end.wav")
                        starte_schreiben = False
                        done_something = True
                    elif text:
                        text = text + " "
                        done_something = True

                        text = text.replace("komma", ",")
                        text = text.replace("ausrufezeichen", "!")
                        text = text.replace("punkt", ".")
                        text = text.replace("neue zeile", "\n")
                        text = text.replace("neu zeile", "\n")
                        text = text.replace("leerzeichen", " ")
                        text = text.replace(" ,", ",")
                        text = text.replace(" !", "!")
                        text = text.replace(" .", ".")
                        text = text.replace("  ", " ")
                        text = text.replace("\n ", "\n")
                        text = text.replace(" \n", "\n")

                        #pyautogui.typewrite(text, interval=0.01)
                        type_unicode(text)
                else:
                    if text == "mitschreiben" or text == "mit schreiben":
                        starte_schreiben = True
                        print("Starte schreiben")
                        os.system("play bleep.wav")
                        done_something = True
                    else:
                        print("Sage 'mitschreiben', damit mitgeschrieben wird")

            if not done_something and not text == "":
                os.system("play stamp.wav")

            stream_context = model.createStream()

if __name__ == '__main__':
    DEFAULT_SAMPLE_RATE = 16000

    import argparse
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
