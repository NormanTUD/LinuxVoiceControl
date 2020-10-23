# -- coding: utf8 --

"""
TODO:
    - X11-Check vorm Mitschreiben
    - Steckdose ansteuern
    - Auf Raspi testen
"""

import psutil
import logging
from datetime import datetime
import threading, collections, queue, os, os.path
import deepspeech
import numpy as np
import pyaudio
import wave
import webrtcvad
from halo import Halo
import scipy
import sys
try:
    import pyautogui 
    import pyperclip
    import wmctrl
except Exception as e:
    print(str(e))
from subprocess import check_output
import time
from urllib.request import urlopen
import random
import argparse
import os.path
import re
from colored import fg, bg, attr
import secrets
import zahlwort2num as w2n
import urllib.parse
import json
import wikipediaapi
from datetime import date, datetime
from babel.dates import format_date, format_datetime, format_time
import string
from pathlib import Path
import getpass
import tempfile
from datetime import datetime
import calendar
import signal


def signal_handler(sig, frame):
    this_pid = os.getpid()
    parent = psutil.Process(this_pid)
    this_children = parent.children(recursive=True)
    if len(this_children):
        for child in this_children:
            if not child.pid == this_pid:
                try:
                    child.kill()
                except Exception as e:
                    print(str(e))
    else:
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def green_text(string):
    print(str(fg('white')) + str(bg('green')) + str(string) + str(attr('reset')))


def red_text(string):
    print(str(fg('white')) + str(bg('red')) + str(string) + str(attr('reset')))

def yellow_text(string):
    print(str(fg('white')) + str(bg('yellow')) + str(string) + str(attr('reset')))

def blue_text(string):
    print(str(fg('white')) + str(bg('blue')) + str(string) + str(attr('reset')))



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
    def __init__(self):
        self.original_sound_volume = self.get_current_audio_level()
        self.home = str(Path.home())
        self.assistant_name_file = self.home + "/.assistant_name"
        self.default_city_file = self.home + "/.default_city"
        self.ssh_x_server = self.home + "/.ssh_x_server"

    def has_x_server (self):
        retval = os.environ.get('DISPLAY')
        if retval is None:
            return False
        else:
            return True

    def get_ssh_x_server (self):
        return self.ssh_x_server 

    def get_ssh_x_server_connect(self):
        yellow_text("Add " + self.ssh_x_server + " file with login credentials if you want to access X11 related data from another computer (like 'user@ip'). Don't forget to make ssh passwordless then!")
        ssh_x_server_connect = self.read_first_line_of_file_if_exists(self.ssh_x_server, "ssh server", getpass.getuser() + "@localhost")
        return ssh_x_server_connect

    def get_assistant_name(self):
        assistant_name = self.read_first_line_of_file_if_exists(self.assistant_name_file, "Assistentenname", "juli")
        return assistant_name

    def get_default_city(self):
        default_city = self.read_first_line_of_file_if_exists(self.default_city_file, "Default-City", "Dresden")
        return default_city;

    def read_first_line_of_file_if_exists (self, filename, name, default):
        if os.path.isfile(filename):
            with open(filename) as f:
                first_line = f.readline()
                first_line = first_line.replace("\n", "")
                return first_line
        else:
            red_text("Die Datei " + filename + " existiert nicht. Typ: " + str(name) + ", Default-Wert: " + str(default));

        return default

    def x_server_is_running(self):
        self.run_command_get_output("echo $DISPLAY")

    def save_current_audio_level_as_original(self):
        self.original_sound_volume = self.get_current_audio_level()

    def get_unixtime(self):
        d = datetime.utcnow()
        unixtime = calendar.timegm(d.utctimetuple())
        return unixtime

    def run_command_get_output(self, command):
        f = tempfile.NamedTemporaryFile(delete=False)
        tmp = f.name
        os.system(command + ' > ' + tmp)
        stdout = open(tmp, 'r').read()
        os.unlink(f.name)
        stdout = stdout.rstrip("\n")
        return stdout

    def get_current_audio_level(self):
        out = ''
        command = "amixer -D pulse get Master | awk -F 'Left:|[][]' 'BEGIN {RS=\"\"}{ print $3 }'"
        blue_text(command)
        return self.run_command_get_output(command)

    def save_original_volume_set_other_value (self, other_value):
        self.original_sound_volume = self.get_current_audio_level()
        self.set_audio_level(other_value)

    def restore_original_sound_level(self):
        self.set_audio_level(self.original_sound_volume)

    def set_audio_level(self, volume):
        command = "amixer set Master " + str(volume)
        blue_text(command)
        return self.run_command_get_output(command)

    def remove_text_in_brackets(self, text):
        ret = ''
        skip1c = 0
        skip2c = 0
        for i in text:
            if i == '[':
                skip1c += 1
            elif i == '(':
                skip2c += 1
            elif i == ']' and skip1c > 0:
                skip1c -= 1
            elif i == ')'and skip2c > 0:
                skip2c -= 1
            elif skip1c == 0 and skip2c == 0:
                ret += i
        return ret

    def download_file_get_string (self, url):
        yellow_text(url)
        this_str = None
        try:
            downloaded = urlopen(url)
            blue_text("Status-Code: " + str(downloaded.getcode()))
            output = downloaded.read()
            this_str = output.decode('utf-8')
        except Exception as e:
            red_text("FEHLER!!!")
            red_text(str(e))

        return this_str

    def random_element_from_array(self, array):
        return secrets.choice(array)

    def run_system_command(self, command):
        blue_text(command)
        os.system(command)




class Features():
    def __init__ (self, interact, controlkeyboard, textreplacements, guitools, basefeatures):
        self.interact = interact
        self.basefeatures = basefeatures
        self.controlkeyboard = controlkeyboard
        self.textreplacements = textreplacements
        self.guitools = guitools
        self.radio_streams = {
            "(?:radio )?eine?s": {
                "link": "https://www.radioeins.de/live.m3u",
                "name": "Radio Eins"
            },
            "sachsen(\s*radio)?": {
                "link": "http://avw.mdr.de/streams/284280-0_mp3_high.m3u",
                "name": "Sachsenradio"
            },
            "deutschland\s*funk": {
                "link": "https://st01.sslstream.dlf.de/dlf/01/64/mp3/stream.mp3",
                "name": "Deutschlandfunk"
            }
        }

    def speak_system_command(self, command):
        pico2wave = " | pico2wave --lang de-DE --wave /tmp/Test.wav ; play /tmp/Test.wav; rm /tmp/Test.wav"
        full_command = command + pico2wave
        blue_text(full_command)
        self.interact.vad_audio.stream.stop_stream()
        self.basefeatures.run_system_command(full_command)
        self.interact.vad_audio.stream.start_stream()

    def get_weekday(self):
        today = date.today()
        return ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")[today.weekday()]

    def talk_weekday(self):
        weekday = self.get_weekday()
        self.interact.talk(weekday)

    def talk_calendar_week (self):
        calweek = date.today().isocalendar()[1]
        self.interact.talk("Es ist die Kalenderwoche " + str(calweek))

    def talk_current_date (self):
        d = datetime.today()
        date_string = "Heute ist " + self.get_weekday() + " der " + str(format_date(d, locale='de_DE'))
        self.interact.talk(date_string)

    def get_available_radio_names (self):
        names = []
        for key in self.radio_streams:
            names.append(self.radio_streams[key]["name"])
        return names

    def read_wikipedia_article(self, article):
        wiki_wiki = wikipediaapi.Wikipedia('de')

        words = article.split(" ")
        words_new = []
        for word in words:
            words_new.append(word.capitalize())

        article = ' '.join(words_new)

        page_py = wiki_wiki.page(article)
        summary = page_py.summary


        summary = summary.replace("[", "")
        summary = summary.replace("]", "")

        re.sub("[\(\[].*?[\)\]]", "", summary)
        summary = self.basefeatures.remove_text_in_brackets(summary)

        self.interact.talk(summary)

    def start_dr_house (self):
        self.basefeatures.run_system_command("vlc ~/mailserver/filme_und_serien/Dr-House/")

    def bitcoin_price (self):
        self.speak_system_command('echo "Ein Bitcoin = $(curl -s https://api.coindesk.com/v1/bpi/currentprice/usd.json | grep -o \'rate\\":\\"[^\\"]*\' | cut -d\\" -f3 | sed -e \"s/\..*//\") US Dollar" | sed -e "s/\,//"')

    def grenzwert(self):
        self.interact.talk("Seh ich aus wie WolframAlpha? Diese Aufgabe ist mir viel zu schwer")

    def stop_radio(self):
        this_pid = os.getpid()
        parent = psutil.Process(this_pid)
        for child in parent.children(recursive=True):
            if not child.pid == this_pid:
                try:
                    child.kill()
                except Exception as e:
                    print(str(e))

    def play_radio (self, regex, text):
        radioname = '';

        m = REMatcher(text)

        #if m.match(r"(?:(?:v|sp)iel(?:e?r?)?|[nm]ach|star?te) radio (.+)(\s+a[nb])?"):
        if regex is not None and m.match(regex):
            radioname = m.group(1)
        else:
            radioname = text

        radio_stream = None
        radio_name = None
        for regex in self.radio_streams:
            if radio_stream is None:
                mr = REMatcher(radioname)
                if mr.match(regex):
                    radio_stream = self.radio_streams[regex]["link"]
                    radio_name = self.radio_streams[regex]["name"]

        if radio_stream is not None:
            self.interact.talk("Ich spiele " + str(radio_name) + " ab")
            newpid = os.fork()
            if newpid == 0:
                self.basefeatures.run_system_command("cvlc " + str(radio_stream))
            else:
                pids = (os.getpid(), newpid)
                print("Forked process, parent: %d, child: %d\n" % pids)
        else:
            self.interact.talk("Das Radio mit dem Namen " + str(radioname) + " ist mir nicht bekannt")

    def how_are_you(self):
        array = [
            "Ich kann mich aktuell nicht beklagen. Wahrscheinlich deshalb, weil ich nur eine Maschine bin und gar nichts fühle.",
            "Wenn ich ganz tief in mich schaue, sehe ich nur Nullen und Einsen",
            "Mein aktueller Status ist in Ordnung, danke der Nachfrage!",
            "Wenn in meiner Software noch Fehler sind, dann merke ich sie gerade zumindest nicht!"
        ]

        self.interact.talk(self.basefeatures.random_element_from_array(array))

    def start_editor (self):
        self.basefeatures.run_system_command("kate &")

    def go_to_end_of_line (self):
        self.controlkeyboard.hotkey('end')

    def save (self):
        if self.guitools.is_console:
            self.controlkeyboard.hotkey('esc')
            self.controlkeyboard.hotkey(':')
            self.controlkeyboard.hotkey('w')
            self.controlkeyboard.hotkey('q')
            self.controlkeyboard.hotkey('!')
            self.controlkeyboard.hotkey('enter')
        else:
            self.controlkeyboard.hotkey('ctrl', 's')

    def suicide (self):
        self.interact.talk("ok, ich beende mich selbst")
        sys.exit(0)

    def get_weather_json (self, place):
        url = 'https://wttr.in/' + urllib.parse.quote(str(place)) + '?format=j1&lang=de'
        this_str = self.basefeatures.download_file_get_string(url)
        datastore = None
        if not this_str is None:
            datastore = json.loads(this_str)
        return datastore

    def talk_current_weather (self, place):
        datastore = self.get_weather_json(place)
        if not datastore is None:
            current_feels_like_temp = datastore['current_condition'][0]["FeelsLikeC"]
            current_humidity = datastore['current_condition'][0]["humidity"]
            current_temp = datastore['current_condition'][0]["temp_C"]
            current_weather_desc = datastore['current_condition'][0]["lang_de"][0]["value"]
            current_windspeed = datastore['current_condition'][0]["windspeedKmph"]

            temperature_string = ''
            if current_feels_like_temp == current_temp:
                temperature_string = "einer Temperatur von %s Grad" % (current_temp)
            else:
                temperature_string = "einer realen Temperatur von %s Grad und einer gefühlten von %s Grad" % (current_temp, current_feels_like_temp)

            weather_string = "In %s ist es %s bei %s. Die Windgeschwindigkeit ist %s km/h bei einer Luftfeuchtigkeit von %s Prozent" % (place, current_weather_desc, temperature_string, current_windspeed, current_humidity)

            self.interact.talk(weather_string)
        else:
            self.interact.talk("Aktuell krieg ich die Wetterdaten aus technischen Gründen leider nicht. Tut mir leid.")

    def talk_weather_tomorrow (self, place):
        datastore = self.get_weather_json(place)
        if not datastore is None:
            (mintemp, maxtemp, tag, hourly_status) = self.create_weather_string(datastore, 1)
            weather_string = "In %s liegt die Temperatur morgen zwischen %s und %s Grad. %s %s" % (place, mintemp, maxtemp, tag, hourly_status)
            self.interact.talk(weather_string)
        else:
            self.interact.talk("Aktuell krieg ich die Wetterdaten aus technischen Gründen leider nicht. Tut mir leid.")

    def talk_weather_the_day_after_tomorrow (self, place):
        datastore = self.get_weather_json(place)
        if not datastore is None:
            (mintemp, maxtemp, tag, hourly_status) = self.create_weather_string(datastore, 2)
            weather_string = "In %s liegt die Temperatur übermorgen zwischen %s und %s Grad. %s %s" % (place, mintemp, maxtemp, tag, hourly_status)
            self.interact.talk(weather_string)
        else:
            self.interact.talk("Aktuell krieg ich die Wetterdaten aus technischen Gründen leider nicht. Tut mir leid.")

    def create_weather_string (self, datastore, number):
        maxtemp = datastore['weather'][number]["maxtempC"]
        mintemp = datastore['weather'][number]["mintempC"]

        weather_status = []
        hourly = datastore['weather'][number]["hourly"]
        for item in hourly:
            this_item = item['lang_de'][0]['value']
            if len(weather_status) == 0 or weather_status[len(weather_status) - 1] != this_item:
                weather_status.append(this_item)

        tag = "Es wird"
        hourly_status = ""
        if len(weather_status) > 1:
            hourly_status = "erst "
            tag = "Über den Tag verteilt wird es"

        hourly_status = hourly_status + ", dann ".join(weather_status)

        return (mintemp, maxtemp, tag, hourly_status)

    def calculate(self, text):
        math_text = self.textreplacements.replace_in_formula_mode(text)

        m = REMatcher(math_text)
        if m.match("^\d+(?:,\d+)?((\+|-|\*|/)\d+(?:,\d+)?)$"):
            self.controlkeyboard.copy(math_text)
            self.basefeatures.run_system_command('qalc -t $(xsel --clipboard) | sed -e "s/ or / oder /"')
            self.speak_system_command('qalc -t $(xsel --clipboard) | sed -e "s/ or / oder /g" | sed -e "s/-/ minus /g" | sed -e "s/\/ durch //g" | sed -e "s/^/' + str(math_text) + ' gleich/" | sed -e "s/\\*/ mal /"')
        else:
            red_text("Erkannt: " + str(math_text))
            self.interact.talk("Diese Rechnung ist mir zu kompliziert oder ich habe sie nicht richtig verstanden");

    def solve_equation (self):
        self.controlkeyboard.hotkey('home')
        self.controlkeyboard.hotkey('shift', 'end')
        self.controlkeyboard.hotkey('ctrl', 'c')
        self.speak_system_command('qalc -t $(xsel --clipboard) | sed -e "s/ or / oder /" | sed -e "s/-/ minus /"')

    def read_aloud(self):
        self.controlkeyboard.hotkey('ctrl', 'a')
        self.controlkeyboard.hotkey('ctrl', 'c')
        self.controlkeyboard.hotkey('ctrl', 'a')
        self.controlkeyboard.hotkey('ctrl', 'c')
        self.controlkeyboard.hotkey('right')

        self.speak_system_command('xsel --clipboard | tr "\n" " "')

    def lalelu (self):
        self.interact.talk("Nur der Mann im Mond hört zu")

    def lalalalala(self):
        self.interact.talk("La la la la la")

    def read_line_aloud(self):
        self.guitools.select_current_line()
        self.controlkeyboard.hotkey('ctrl', 'c')
        self.speak_system_command('xsel --clipboard | tr "\n" " "')

    def say_something_philosophical (self):
        array = [
            "Das ontisch Nächste ist das ontologisch Fernste",
            "Jedes Wort ist ein Vorurteil",
            "Man verdirbt einen Jüngling am sichersten, wenn man ihn verleitet, den Gleichdenkenden höher zu achten als den Andersdenkenden.",
        ]

        self.interact.talk(self.basefeatures.random_element_from_array(array))

    def random_string(self, string_length=16):
        letters = string.ascii_letters + string.digits
        return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(string_length))

    def say_current_sound_volume(self):
        audio_level = self.basefeatures.get_current_audio_level()
        self.interact.talk(audio_level)

    def create_password(self):
        random_string = self.random_string(25)
        print("Das zufällig generierte Passwort ist: " + random_string)
        self.controlkeyboard.copy(random_string)
        self.controlkeyboard.copy(random_string)
        self.interact.talk("Ein Passwort wurde erstellt und in das Clipboard kopiert")

    def favourite_song (self):
        array = [
            "Monoton und Minimal von Welle Erdball",
            "Digital ist Besser von Tocotronic",
            "Starless von King Krimson",
            "Technologik von Däft Pank"
        ]

        self.interact.talk(self.basefeatures.random_element_from_array(array))

    def hello (self):
        self.interact.talk("Hallo, " + os.getenv("USER"))


    def tell_day (self):
        from datetime import date
        heute = date.today()
        string_day = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")[heute.weekday()]
        self.interact.talk("Heute ist " + string_day)

    def tell_time (self):
        now = datetime.now()
        current_hour = now.strftime("%H")
        current_minute = now.strftime("%M")
        string_time = str(current_hour) + " Uhr " + str(current_minute)
        self.interact.talk(string_time)

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
            "Ein Informatiker schiebt einen Kinderwagen durch den Park. Kommt ein älteres Ehepaar und fragt: Junge oder Mädchen? Da sagt der Informatiker: Richtig!"
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
        text = text.replace("ein hundert", "100")
        text = text.replace("zweihundert", "200")
        text = text.replace("zwei hundert", "200")
        text = text.replace("drei hundert", "300")
        text = text.replace("dreihundert", "300")
        text = text.replace("vierhundert", "400")
        text = text.replace("vier hundert", "400")
        text = text.replace("fünfhundert", "500")
        text = text.replace("fünf hundert", "500")
        text = text.replace("sechs hundert", "600")
        text = text.replace("sechshundert", "600")
        text = text.replace("sieben hundert", "700")
        text = text.replace("siebenhundert", "700")
        text = text.replace("acht hundert", "800")
        text = text.replace("achthundert", "800")
        text = text.replace("neun hundert", "900")
        text = text.replace("neunhundert", "900")

        text = text.replace("hundert", "100")
        text = text.replace("hundert", "100")

        text = text.replace("eine million", "1000000")
        text = text.replace("ein million", "1000000")
        text = text.replace("einmillion", "1000000")
        text = text.replace("million", "1000000")

        words = text.split(" ")
        words_new = []
        for word in words:
            try:
                word = w2n.convert(word)
            except Exception as e:
                pass
            words_new.append(str(word))

        text = ' '.join(words_new)


        text = text.replace("null", "0")
        text = text.replace("eins", "1")
        text = text.replace("zwei", "2")
        text = text.replace("drei", "3")
        text = text.replace("vier", "4")
        text = text.replace("von", "5")
        text = text.replace("fünf", "5")
        text = text.replace("sechs", "6")
        text = text.replace("sieben", "7")
        text = text.replace("acht", "8")
        text = text.replace("neun", "9")
        text = text.replace("zehn", "10")
        text = text.replace("elf", "11")
        text = text.replace("zwölf", "12")
        text = text.replace("dreizehn", "13")
        text = text.replace("vierzehn", "14")
        text = text.replace("fünfzehn", "15")
        text = text.replace("sechszehn", "16")
        text = text.replace("siebzehn", "17")
        text = text.replace("achtzehn", "18")
        text = text.replace("neunzehn", "19")
        text = text.replace("zwanzig", "20")

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
        text = text.replace("ausrufezeichen", "!")
        text = text.replace("fakultät", "!")


        return text

class Interaction():
    def __init__ (self, vad_audio, controlkeyboard, basefeatures):
        self.vad_audio = vad_audio
        self.controlkeyboard = controlkeyboard
        self.consolemode = False
        self.basefeatures = basefeatures

        self.ssh_x_server_connect = self.basefeatures.get_ssh_x_server_connect()

    def is_console(self):
        self.consolemode = True

    def is_not_console(self):
        self.consolemode = False

    def talk(self, something):
        yellow_text(str(something))
        if not something == "":
            self.vad_audio.stream.stop_stream()
            self.basefeatures.run_system_command('pico2wave --lang de-DE --wave /tmp/Test.wav "' + str(something) + '" ; play /tmp/Test.wav; rm /tmp/Test.wav')
            self.vad_audio.stream.start_stream()

    def can_you_hear_me(self):
        array = [
            "Ja, kann ich",
            "Ja, sonst könnte ich dir auch nicht antworten",
            "Nein. ähhh Doch. Ich meine ja."
        ]

        self.talk(self.basefeatures.random_element_from_array(array))

    def do_you_hear_me (self):
        self.talk("Ja, ich höre dich")

    def play_sound_ok(self):
        self.play_sound(os.path.dirname(os.path.realpath(__file__)) + "/bleep.wav")

    def play_sound_not_ok(self):
        self.play_sound(os.path.dirname(os.path.realpath(__file__)) + "/line_end.wav")

    def play_sound (self, path):
        self.vad_audio.stream.stop_stream()
        if os.path.isfile(path):
            self.basefeatures.run_system_command("play " + path)
        else:
            self.talk("Die Datei " + str(path) + " konnte nicht gefunden werden!")
        self.vad_audio.stream.start_stream()

    def type_unicode(self, word):
        if self.basefeatures.has_x_server():
            self.controlkeyboard.copy(word)
            if self.consolemode:
                self.controlkeyboard.hotkey("ctrl", "shift", "v")
            else:
                self.controlkeyboard.hotkey("ctrl", "v")
        else:
            red_text("No X11")

class ControlKeyboard():
    def copy(self, word):
        word_debug = word
        word_debug = word_debug.replace("\n", "\\n")
        yellow_text("Copying `" + str(word_debug) + "` to clipboard")
        pyperclip.copy(word)
        pyperclip.copy(word)

    def hotkey(self, *argv):
        yellow_text("Pressing `" + ' + '.join(argv) + "`")
        pyautogui.hotkey(*argv)

class GUITools():
    def __init__ (self, interact):
        self.interact = interact
        self.consolemode = False

    def is_console(self):
        self.interact.consolemode = True
        self.consolemode = True

    def is_not_console(self):
        self.interact.consolemode = False
        self.consolemode = False

    def start_browser(self):
        self.interact.basefeatures.run_system_command("firefox")

    def toggle_volume(self):
        self.interact.talk("OK")
        command = "amixer set Master toggle"
        blue_text(command)
        self.interact.basefeatures.run_system_command(command)

    def volume_up (self):
        self.interact.controlkeyboard.hotkey('volumeup')

    def volume_down (self):
        self.interact.controlkeyboard.hotkey('volumedown')

    def say_current_window(self):
        self.interact.talk(self.get_current_window())

    def switch_window (self):
        self.interact.controlkeyboard.hotkey('alt', 'tab')
        time.sleep(1)
        self.say_current_window()

    def next_tab (self):
        self.interact.controlkeyboard.hotkey('ctrl', 'tab')
        time.sleep(1)
        self.say_current_window()

    def get_current_window (self):
        out = b''
        if os.path.isfile(self.interact.basefeatures.get_ssh_x_server()):
            out = check_output(['ssh', self.interact.basefeatures.get_ssh_x_server_connect(), 'env DISPLAY=:0 XAUTHORITY=/home/$USER/.Xauthority xdotool getwindowfocus getwindowname'])
        else:
            out = check_output(["xdotool", "getwindowfocus", "getwindowname"])
        this_str = out.decode("utf-8")
        return this_str

    def all_windows(self):
        Window = wmctrl.Window
        x = Window.list()
        for wn in Window.list():
            self.interact.talk(wn.wm_name)

    def close_tab(self):
        self.interact.controlkeyboard.hotkey('ctrl', 'w')

    def previous_tab(self):
        self.interact.controlkeyboard.hotkey('ctrl', 'shift', 'tab')
        time.sleep(1)
        self.interact.talk(self.get_current_window())

    def mark_and_delete_all(self):
        self.interact.controlkeyboard.hotkey('ctrl', 'a')
        self.interact.controlkeyboard.hotkey('del')

    def repeat (self):
        self.interact.controlkeyboard.hotkey('ctrl', 'y')

    def escape (self):
        self.interact.controlkeyboard.hotkey('esc')

    def new_tab(self):
        self.interact.controlkeyboard.hotkey('ctrl', 't')

    def new_window(self):
        self.interact.controlkeyboard.hotkey('ctrl', 'n')

    def close_window(self):
        self.interact.controlkeyboard.hotkey('alt', 'f4')

    def copy (self):
        self.interact.controlkeyboard.hotkey('ctrl', 'c')

    def select_all(self):
        self.interact.controlkeyboard.hotkey('ctrl', 'a')

    def undo (self):
        self.interact.controlkeyboard.hotkey('ctrl', 'z')

    def cut(self):
        self.interact.controlkeyboard.hotkey('ctrl', 'x')

    def delete(self):
        self.interact.controlkeyboard.hotkey('del')

    def select_current_line(self):
        self.interact.controlkeyboard.hotkey('home')
        self.interact.controlkeyboard.hotkey('shift', 'end')

    def delete_current_line (self):
        self.select_current_line()
        self.delete()

    def paste (self):
        if self.consolemode:
            self.interact.controlkeyboard.hotkey('ctrl', 'shift', 'v')
        else:
            self.interact.controlkeyboard.hotkey('ctrl', 'v')

    def delete_last_word(self):
        self.interact.controlkeyboard.hotkey('ctrl', 'backspace')

    def press_enter(self):
        self.interact.controlkeyboard.hotkey('enter')

    def press_space(self):
        self.interact.controlkeyboard.hotkey('space')

class Routines():
    def __init__ (self, guitools, interact, features):
        self.guitools = guitools
        self.interact = interact
        self.features = features

    def morning_routine(self):
        self.interact.talk("Guten Morgen")
        self.features.talk_current_date()
        self.features.talk_calendar_week()
        self.features.talk_current_weather(self.features.basefeatures.get_default_city())
        self.features.play_radio(None, "radio eins")

class AnalyzeAudio ():
    def __init__ (self, guitools, interact, features, routines):
        self.guitools = guitools
        self.interact = interact
        self.features = features
        self.routines = routines
        self.regexes = {
            "^(?:(?:wiederhole was ich sage)|(?:sprich [wm]ir nach))$": {
                "isfake": 1,
                "help": "Spricht das, was gesagt worden ist, erneut aus",
                "say": ["Wiederhole was ich sage", "Sprich mir nach"]
            },
            "^konsolenmodus aktivieren$": {
                "isfake": 1,
                "help": "Startet den Konsolen-Modus",
                "say": ["Konsolenmodus aktivieren"]
            },
            "^konsolenmodus deaktivieren$": {
                "isfake": 1,
                "help": "Deaktiviert den Konsolen-Modus",
                "say": ["Konsolenmodus deaktivieren"]
            },
            "^formel eingeben$": {
                "isfake": 1,
                "help": "Startet den Formel-Modus",
                "say": ["Formel eingeben"]
            },
            "^text eingeben$": {
                "isfake": 1,
                "help": "Beendet den Formel-Modus und gibt wieder normalen Text ein",
                "say": ["Text eingeben"]
            },
            "^mitschreiben$": {
                "isfake": 1,
                "help": "Tippt das, was gesagt worden ist, über eine virtuelle Tastatur ein",
                "say": ["Mitschreiben"]
            },
            "^nicht mehr mitschreiben$": {
                "isfake": 1,
                "help": "Hört auf mitzuschreiben",
                "say": ["Nicht mehr mitschreiben"]
            },
            "^leiser$": {
                "fn": "self.guitools.volume_down", 
                "help": "Lautstärke leiser machen",
                "say": ["leiser"]
            },
            "^lauter$": {
                "fn": "self.guitools.volume_up",
                "help": "Lautstärke lauter machen",
                "say": ["lauter"]
            },
            "(?:(?:(?:(?:ka(?:nn|m)st\s*)?du )?(?:mich|nicht) hören))$": {
                "fn": "self.interact.can_you_hear_me",
                "help": "Antwortet, wenn das Gerät dich hören kann",
                "say": ["Kannst du mich hören?"]
            },
            "^(?:(?:hörst du mich))$": {
                "fn": "self.interact.do_you_hear_me",
                "help": "Antwortet, wenn das Gerät dich hören kann",
                "say": ["Hörst du mich?"]
            },
            "^star?te internet$": {
                "fn": "self.guitools.start_browser",
                "help": "Startet einen Internet-Browser",
                "say": ["Starte Interent"]
            },
            "(?:wochentag|welcher\s*tag)": {
                "fn": "self.features.talk_weekday",
                "help": "Sagt, welcher Wochentag ist",
                "say": ["Welcher Wochentag ist?"]
            },

            "kalenderwoche": {
                "fn": "self.features.talk_calendar_week",
                "help": "Sagt, welches Kalenderwoche ist",
                "say": ["Welche Kalenderwoche ist?"]
            },
            "^.*datum ist heute$": {
                "fn": "self.features.talk_current_date",
                "help": "Sagt, welches Datum heute ist",
                "say": ["Welches Datum ist heute?"]
            },
            "^alles vorlesen$": {
                "fn": "self.features.read_aloud",
                "help": "Lese vor, was gerade an markierbarem Text vor dir ist",
                "say": ["Alles vorlesen"]
            },
            "^(?:diese|aktuelle?)\s*zeile\s*vorlesen$": {
                "fn": "self.features.read_line_aloud",
                "help": "Lese die aktuelle Zeile vor",
                "say": ["Diese Zeile vorlesen", "Aktuelle Zeile vorlesen"]
            },
            "^löschen$": {
                "fn": "self.guitools.delete",
                "help": "Drücke die ENTF Taste",
                "say": ["Löschen"]
            },
            "^(?:aktuelle|dieser?) zeile (?:auswählen|markieren)$": {
                "fn": "self.guitools.select_current_line",
                "help": "Aktuelle Zeile auswählen",
                "say": ["Aktuelle Zeile auswählen", "Diese Zeile auswählen", "Aktuelle Zeile markieren", "Diese Zeile markieren"]
            },
            "^(?:dieser?|aktuelle) zeile löschen$": {
                "fn": "self.guitools.delete_current_line",
                "help": "Aktuelle Zeile löschen",
                "say": ["Aktuelle Zeile löschen", "Diese Zeile löschen"]
            },
            "^aus\s*rechnen$": {
                "fn": "self.features.solve_equation",
                "help": "Aktuelle Zeile als Formel betrachten und ausrechnen",
                "say": ["Ausrechnen"]
            },
            "^wieder\s*holen$": {
                "fn": "self.guitools.repeat",
                "help": "Hole die letzte rückgängig gemachte Änderung wieder",
                "say": ["Wiederholen"]
            },
            "^abbrechen$": {
                "fn": "self.guitools.escape",
                "help": "Bricht aktuellen Vorgang ab (mit ESC)",
                "say": ["Abbrechen"]
            },
            "^kopieren$": {
                "fn": "self.guitools.copy",
                "help": "Kopiere die aktuelle Auswahl",
                "say": ["Kopieren"]
            },
            "^(?:schließe (?:fenster|elster|fester))|(?:(?:fenster|elster|fester) schließen)$": {
                "fn": "self.guitools.close_window",
                "help": "Schließe aktuelles Fenster",
                "say": ["Schließe Fenster", "Fenster schließen"]
            },
            "^einfügen$": {
                "fn": "self.guitools.paste",
                "help": "Text aus dem Clipboard Einfügen",
                "say": ["Einfügen"]
            },
            "^(?:la+\s*le+\s*lu+)|(la la la)$": {
                "fn": "self.features.lalelu",
                "help": "Lalelu",
                "say": ["La le lu"]
            },
            "^la\s*la\s*la\s*la\s*la$": {
                "fn": "self.features.lalalalala",
                "help": "Lalalalala",
                "say": ["La la la la la"]
            },
            "^aus\s*schneiden$": {
                "fn": "self.guitools.cut",
                "help": "Aktuell markierten Text ausschneiden",
                "say": ["Ausschneiden"]
            },
            "^alles (markieren|auswählen)$": {
                "fn": "self.guitools.select_all",
                "help": "Alles auswählen",
                "say": ["Alles markieren", "Alles auswählen"]
            },
            "^alle fenster$": {
                "fn": "self.guitools.all_windows",
                "help": "Alle Fenster auflisten",
                "say": ["Alle Fenster"]
            },
            "^eingabe\s*taster?$": {
                "fn": "self.guitools.press_enter",
                "help": "Drücke die Eingabetaste",
                "say": ["Eingabetaste"]
            },
            "^alles löschen$": {
                "fn": "self.guitools.mark_and_delete_all",
                "help": "Markiert alles und löscht darauf hin alles",
                "say": ["alles löschen"]
            },
            ".{0,20}fenster.*(vordergrund|fokus)$": {
                "fn": "self.guitools.say_current_window",
                "help": "Sagt an, welches Fenster gerade im Fokus ist",
                "say": ["Welches Fenster ist im Fokus?", "Welches Fenster ist im Vordergrund?"]
            },
            "^schließe ta[bp]$": {
                "fn": "self.guitools.close_tab",
                "help": "Schließe Tab (drücke CTRL w)",
                "say": ["Schließe Tab"]
            },
            "^(?:wechsel (?:fenster|elster))|(?:(?:elster|fenster) wechseln?)$": {
                "fn": "self.guitools.switch_window",
                "help": "Wechsel das aktuelle Fenster (alt+tab)",
                "say": ["Wechsel Fenster", "Fenster wechseln"]
            },
            "^wie geht es dir$": {
                "fn": "self.features.how_are_you",
                "help": "Beantwortet die Frage, wie es dem Sprachassistenten geht",
                "say": ["Wie geht es dir?"]
            },
            ".*ist.*grenzwert.*$": {
                "fn": "self.features.grenzwert",
                "help": "Was ist der Grenzwert einer Funktion?",
                "say": ["Was ist der Grenzwert von a/b für b gegen Unendlich?"]
            },
            "^neu(?:er)? ta[bp]$": {
                "fn": "self.guitools.new_tab",
                "help": "Öffnet einen neuen Tab",
                "say": ["Neuer Tab"]
            },
            "^nächster? ta[bp]?$": {
                "fn": "self.guitools.next_tab",
                "help": "Wechselt in den nächsten Tab",
                "say": ["Nächster Tab"]
            },
            "^letzter ta[bp]$": {
                "fn": "self.guitools.previous_tab",
                "help": "Wechselt in den vorherigen Tab",
                "say": ["Letzter Tab"]
            },
            "^neues (?:fenster|elster)$": {
                "fn": "self.guitools.new_window",
                "help": "Öffnet ein neues Fenster",
                "say": ["Neues Fenster"]
            },
            "datei\s*speichern?": {
                "fn": "self.features.save",
                "help": "Speicher Datei",
                "say": ["Datei speichern"]
            },
            "ende der zeile": {
                "fn": "self.features.go_to_end_of_line",
                "help": "Gehe ans Ende der Zeile",
                "say": ["Ans Ende der Zeile gehen"]
            },
            "s?tar?te?r?\s*(?:ein(?:e[nm])?)?\s*(?:text\s*)?editor\s*": {
                "fn": "self.features.start_editor",
                "help": "Starte einen Texteditor",
                "say": ["Starte einen Editor"]
            },
            ".*(?:(?:ende.*(?:dich|selbst))|(?:suizid)).*": {
                "fn": "self.features.suicide",
                "help": "Beendet den Sprachassistenten",
                "say": ["Beende dich selbst"]
            },
            "^(?:ab\s*spielen|spiele ab|pausieren)$": {
                "fn": "self.guitools.press_space",
                "help": "Drückt die Leertaste zum Abspielen bzw. Pausiren von Musik",
                "say": ["Abspielen", "Spiele ab", "Pausieren"]
            },
            "^(?:lautlos|wieder laut)$": {
                "fn": "self.guitools.toggle_volume",
                "help": "Stellt die Lautstärke auf 0 bzw. auf 100%",
                "say": ["Lautlos", "Wieder laut"]
            },
            "^rückgängig$": {
                "fn": "self.guitools.undo",
                "help": "Macht die letzte Aktion rückgängig",
                "say": ["Rückgängig"]
            },
            "(alle\s)|(h[ea]ll?o).*": {
                "fn": "self.features.hello",
                "help": "Begrüßt dich",
                "say": ["Hallo Juli"]
            },
            ".*((was.*)|(welche)).*tag.*": {
                "fn": "self.features.tell_day",
                "help": "Sagt, welcher Tag ist",
                "say": ["Was für ein Tag ist Heute?", "Welcher Tag ist heute?"]
            },
            ".*spät.*ist.*": {
                "fn": "self.features.tell_time",
                "help": "Sagt die Uhrzeit",
                "say": ["Wie spät ist es?"]
            },
            ".*ein(?:e[mn])?.*witz": {
                "fn": "self.features.tell_joke",
                "help": "Erzählt einen Witz",
                "say": ["Erzähl mir einen Witz", "Erzähl mir einen weiteren Witz"]
            },
            ".*[dsl]ag?.*philosophisches": {
                "fn": "self.features.say_something_philosophical",
                "help": "Sagt etwas Philosophisches",
                "say": ["Sag etwas Philosophisches!"]
            },
            "^letztes wort löschen$": {
                "fn": "self.guitools.delete_last_word",
                "help": "Löscht das gesamte letzte Wort",
                "say": ["Letztes Wort löschen"]
            },
            "(?:stop(?:p?en?)?.*radio)|(?:(?:ra)?dio.*stop(?:p?en?)?)|(?:(?:be)?ende.*radio)|(?:(?:ra)?dio.*ende)": {
                "fn": "self.features.stop_radio",
                "help": "Stoppe das aktuell spielende Radio",
                "say": ["Stoppe Radio", "Radio stoppen", "Radio beenden", "Beende Radio"]
            },
            "^(?:(?:v|sp)iel(?:e?r?)?|[mn]ach|s?tar?te) radio (.*)(\s+a[bn])?$": {
                "fn": "self.features.play_radio",
                "param": "regex, text",
                "help": "Startet einen Radiosender. Verfügbare Namen für Radiosender: " + ', '.join(self.features.get_available_radio_names()),
                "say": ["Spiele Radio Eins ab", "Starte Radio Deutschlandfunk", "Mach Radio Sachsen an"]
            },
            "^(.*)(?:(?:aktuell.*bitcoin)|(?:bitcoin\s*preis))(.*)$": {
                "fn": "self.features.bitcoin_price",
                "help": "Sagt den aktuellen Bitcoin-Preis in US-Dollar an",
                "say": ["Was ist der aktuelle Bitcoin-Preis?"]
            },
            "^star?te? doktor haus$": {
                "fn": "self.features.start_dr_house",
                "help": "Startet Dr-House (nur bei mir :-) )",
                "say": ["Starte Doktor House"]
            },
            "^wikipedia\s+(.*)$": {
                "fn": "self.features.read_wikipedia_article",
                "param": "m.group(1) or 'Linux'",
                "help": "Liest die Zusammenfassung eines Wikipedia-Artikels vor",
                "say": ["Wikipedia Straßenbahn"]
            },
            "^.*(?:(?:wetter über\s*morgen)|(?:über\s*morgen.* wetter))(?: in (.*))?$": {
                "fn": "self.features.talk_weather_the_day_after_tomorrow", 
                "param": "m.group(1) or '" + self.features.basefeatures.get_default_city() + "'",
                "help": "Sagt das Wetter übermorgen an (normalerweise in " + self.features.basefeatures.get_default_city() + ", aber auch in anderen Städten)",
                "say": ["Wie wird das Wetter übermorgen?", "Wie wird das Wetter übermorgen in Hamburg?"]
            },
            "^.*(?:(?:wetter morgen)|(?:morgen.* wetter))(?: in (.*))?$": {
                "fn": "self.features.talk_weather_tomorrow", 
                "param": "m.group(1) or '" + self.features.basefeatures.get_default_city() + "'",
                "help": "Sagt das Wetter morgen an (normalerweise in " + self.features.basefeatures.get_default_city() + ", aber auch in anderen Städten)",
                "say": ["Wie wird das Wetter morgen?", "Wie wird das Wetter morgen in Hamburg?"]
            },
            "^.*(?:(?:(?:gerade|jetzt).*wetter)|(?:wetter (?:gerade|jetzt))|(?:wie.*ist.*wetter))(?: in (.*))?$": {
                "fn": "self.features.talk_current_weather", 
                "param": "m.group(1) or '" + self.features.basefeatures.get_default_city() + "'",
                "help": "Sagt das aktuelle Wetter an (normalerweise in " + self.features.basefeatures.get_default_city() + ", aber auch in anderen Städten)",
                "say": ["Wie ist gerade das Wetter morgen?", "Wie ist gerade das Wetter in Hamburg?"]
            },
            "^[wd]as (?:er)?gibt (.*)?$": {
                "fn": "self.features.calculate",
                "param": "m.group(1)",
                "help": "Führt einfache Rechnungen aus",
                "say": ["Was ergibt 5 + 10?"]
            },
            "^[wd]as ist.*lieb(?:lings|es)?\s*lied$": {
                "fn": "self.features.favourite_song",
                "help": "Sagt das Lieblingslied des Sprachassistenten an",
                "say": ["Was ist dein Lieblingslied?"]
            },
            "^guten?\s*morg[ea]n$": {
                "fn": "self.routines.morning_routine",
                "help": "Starte die Morgenroutine",
                "say": ["Guten Morgen!"]
            },
            "^(?:(?:er\s*stelle|generieren?)\s*)?\s*(?:ein\s*)?passwor[td]$": {
                "fn": "self.features.create_password",
                "help": "Erstelle ein zufälliges Passwort",
                "say": ["Erstelle Passwort"]
            },
            "laut\s*st.*rke": {
                "fn": "self.features.say_current_sound_volume",
                "help": "Sagt die aktuelle Lautstärke",
                "say": ["Wie ist die aktuelle Lautstärke?"]
            }
        }

    def show_available_commands (self):
        for regex in self.regexes:
            command = self.regexes[regex]
            helpstr = fg("white") + bg("cyan") + command["help"] + attr("reset")
            saystr = "\n\t" + "\n\t".join(command['say']) + "\n"

            command_help = helpstr + ", sage z.,B.: " + saystr
            if command_help is not None:
                print(command_help)

    def is_valid_command (self, text):
        m = REMatcher(text)

        is_valid = False

        for regex in self.regexes:
            if m.match(regex):
                is_valid = True

        return is_valid 

    def do_what_i_just_said(self, text):
        m = REMatcher(text)

        done_something = False

        for regex in self.regexes:
            if not "isfake" in self.regexes[regex] and m.match(regex):
                fn_name = self.regexes[regex]["fn"]
                param = ''
                if "param" in self.regexes[regex]:
                    param = self.regexes[regex]["param"]
                runcode = fn_name + "(" + param + ")"
                blue_text(runcode)
                eval(runcode)
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
        resample = scipy.signal.resample(data16, resample_size)
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
        self.specialcommands = None

    def set_specialcommands (self, specialcommands):
        self.specialcommands = specialcommands

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


        if frames is None:
            frames = self.frame_generator()
        num_padding_frames = padding_ms // self.frame_duration_ms
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False

        for frame in frames:
            if self.specialcommands is None:
                print("ERROR: SpecialCommands not set")
            else:
                self.specialcommands.assistant_name_timeout()
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

class SpecialCommands():
    def __init__(self, analyzeaudio, interact, guitools, textreplacements, spinner, spinner_text_default, basefeatures):
        self.analyzeaudio = analyzeaudio
        self.interact = interact
        self.guitools = guitools
        self.textreplacements = textreplacements
        self.spinner = spinner
        self.basefeatures = basefeatures

        self.spinner_default_write_mode = "Was du jetzt sagst wird aufgeschrieben"
        self.spinner_default_command_mode = "Ich warte auf deinen Befehl"
        self.spinner_default_repeat_mode = "Was du jetzt aussprichst wird wiederholt"
        self.spinner_default_command_line_mode = "Du bist im Konsolenmodus"
        self.spinner_default_equation_mode = "Du bist im Formel-Modus"
        self.spinner_text_default = spinner_text_default
        self.spinner_text = self.spinner_text_default
        self.last_spinner_text_changed = self.basefeatures.get_unixtime()

        self.last_command_enabled = False
        self.enabled = False
        self.repeat_after_me = False
        self.start_writing = False
        self.is_formel = False
        self.start_writing = False
        self.done_something = False
        self.assistant_name_said_time = None

        self.timeout = 15

    def get_assistant_name_said_time(self):
        if self.assistant_name_said_time is not None:
            return self.assistant_name_said_time
        else:
            return 0

    def assistant_name_timeout(self):
        if self.enabled and not self.start_writing:
            assistant_name_seconds_ago = self.basefeatures.get_unixtime() - self.get_assistant_name_said_time()
            if not assistant_name_seconds_ago < self.timeout:
                self.enabled = False
                self.interact.play_sound_not_ok()
                self.set_spinner_text(self.spinner_text_default)

    def set_spinner_text (self, text):
        self.last_spinner_text_changed = self.basefeatures.get_unixtime()
        self.spinner_text = text

    def needs_to_be_muted (self):
        if self.spinner_text == self.spinner_default_command_mode or self.spinner_text == self.spinner_default_write_mode or self.spinner_text == self.spinner_default_repeat_mode:
            return True
        return False

    def check_if_assistants_name_has_been_said (self, text):
        if not self.enabled and self.basefeatures.get_assistant_name() in text:
            self.enabled = True
            self.last_command_enabled = True
            if text == self.basefeatures.get_assistant_name():
                self.interact.talk("Ja?")
            text = text.replace(self.basefeatures.get_assistant_name() + " ", "")
            text = text.replace(self.basefeatures.get_assistant_name(), "")
            self.set_spinner_text(self.spinner_default_command_mode)
            self.assistant_name_said_time = self.basefeatures.get_unixtime()
        return text

    def write(self, text):
        if text == 'nicht mehr mitschreiben' or text == 'nicht mehr mit schreiben' or text == 'nicht mit schreiben':
            print("Es wird nicht mehr mitgeschrieben")
            if self.enabled:
                self.set_spinner_text(self.spinner_default_command_mode)
            else:
                self.set_spinner_text(self.spinner_text_default)
            self.interact.play_sound_not_ok()
            self.start_writing = False
            self.done_something = False
            self.enabled = False
        elif text:
            if self.is_formel:
                text = self.textreplacements.replace_in_formula_mode(text)
            else:
                text = text + " "
                text = self.textreplacements.replace_in_text_mode(text)
            self.interact.type_unicode(text)
            self.done_something = True

    def get_spinner_text(self):
        return self.spinner_text

    def mute_if_neccessary(self):
        if self.needs_to_be_muted():
            self.basefeatures.save_original_volume_set_other_value("0%")
        else:
            self.basefeatures.restore_original_sound_level()
            self.basefeatures.save_current_audio_level_as_original()

    def while_loop_function (self, text):
        text = " ".join(text.split())

        if not text == "":
            green_text("Recognized: %s" % text)

            text = self.check_if_assistants_name_has_been_said(text)

            if self.repeat_after_me:
                self.interact.talk(text)
                self.set_spinner_text(self.spinner_text_default)
                self.repeat_after_me = False
    
            if (self.start_writing or self.enabled) and not text == "":
                assistant_name_seconds_ago = self.basefeatures.get_unixtime() - self.get_assistant_name_said_time()
                if self.start_writing or assistant_name_seconds_ago < self.timeout:
                    self.done_something = self.analyzeaudio.do_what_i_just_said(text)
                elif self.enabled and not self.start_writing:
                    self.enabled = False
                    self.interact.play_sound_not_ok()
                    self.set_spinner_text(self.spinner_text_default)

            if self.done_something and not self.last_command_enabled:
                self.enabled = False
                self.set_spinner_text(self.spinner_text_default)
            else:
                self.last_command_enabled = False
                m = REMatcher(text)
                if m.match("formell? ein\s*geben"):
                    self.interact.talk("Sprich zeichen für zeichen ein und sage wenn fertig 'wieder text eingeben'")
                    self.is_formel = True
                    self.interact.play_sound_ok()
                    self.done_something = True
                    self.set_spinner_text(self.spinner_default_equation_mode)
                elif m.match("konsole.*\s+aktivier") or m.match("konsolen\s*modus"):
                    self.guitools.is_console()
                    self.interact.talk("Konsolenmodus aktiviert")
                    self.done_something = True
                    self.set_spinner_text(self.spinner_default_command_line_mode)
                elif m.match("(?:nicht.*konsole)|(?:konsole.*deaktivier)"):
                    self.guitools.is_not_console()
                    self.interact.talk("Konsolenmodus de-aktiviert")
                    self.done_something = True
                    self.set_spinner_text(self.spinner_default_write_mode)
                elif m.match("(?:wiederhole.*ich.*sage)|(?:sprich ([wm]ir|mehr) nach)"):
                    self.interact.talk("OK")
                    self.repeat_after_me = True
                    self.done_something = True
                    self.set_spinner_text(self.spinner_default_repeat_mode)
                elif self.is_formel and m.match("wie\s*der text ein\s*geben"):
                    self.interact.talk("Ab jetzt wieder Text")
                    self.is_formel = False
                    self.interact.play_sound_ok()
                    self.done_something = True
                    self.set_spinner_text(self.spinner_default_write_mode)
                elif self.start_writing:
                    self.write(text)
                else:
                    if m.match("^mit\s*schreiben$"):
                        self.start_writing = True
                        logging.info("Starte schreiben")
                        self.interact.play_sound_ok()
                        self.done_something = True
                        self.set_spinner_text(self.spinner_default_write_mode)
                    else:
                        print("Sage 'mitschreiben', damit mitgeschrieben wird")
                        self.done_something = False
        else:
            self.done_something = False

def main(ARGS):
    # Load DeepSpeech model
    if os.path.isdir(ARGS.model):
        model_dir = ARGS.model
        ARGS.model = os.path.join(model_dir, 'output_graph.pb')
        ARGS.scorer = os.path.join(model_dir, ARGS.scorer)

    print('Initialisiere Modell...')
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

    basefeatures = BaseFeatures()

    controlkeyboard = ControlKeyboard()
    textreplacements = TextReplacements()
    interact = Interaction(vad_audio, controlkeyboard, basefeatures)
    guitools = GUITools(interact)
    features = Features(interact, controlkeyboard, textreplacements, guitools, basefeatures)
    routines = Routines(guitools, interact, features)
    analyzeaudio = AnalyzeAudio(guitools, interact, features, routines)

    if ARGS.helpspeech:
        analyzeaudio.show_available_commands()
        sys.exit(0)

    interact.talk("Mein Name ist " + basefeatures.get_assistant_name())
    green_text("Sage " + basefeatures.get_assistant_name() + " um den Assistenten zu aktivieren")

    print("Sage 'mitschreiben', damit mitgeschrieben wird")
    frames = vad_audio.vad_collector()

    # Stream from microphone to DeepSpeech using VAD
    spinner = None
    spinner_text = "Sage " + basefeatures.get_assistant_name() + " um Befehle zu erteilen"
    spinner = Halo(text=spinner_text, spinner='dots')
    specialcommands = SpecialCommands(analyzeaudio, interact, guitools, textreplacements, spinner, spinner_text, basefeatures)
    stream_context = model.createStream()

    vad_audio.set_specialcommands(specialcommands)

    wav_data = bytearray()

    for frame in frames:


        if frame is not None:
            if spinner:
                spinner.text = specialcommands.get_spinner_text()
                spinner.start()
            logging.debug("streaming frame")
            stream_context.feedAudioContent(np.frombuffer(frame, np.int16))
            if ARGS.savewav:
                wav_data.extend(frame)
        else:
            if spinner:
                spinner.stop()
            logging.debug("end utterence")
            if ARGS.savewav:
                vad_audio.write_wav(os.path.join(ARGS.savewav, datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")), wav_data)
                wav_data = bytearray()
            text = stream_context.finishStream()
            specialcommands.while_loop_function(text)
            stream_context = model.createStream()

if __name__ == '__main__':
    DEFAULT_SAMPLE_RATE = 16000

    parser = argparse.ArgumentParser(description="Stream from microphone to DeepSpeech using VAD")

    parser.add_argument('--helpspeech', action='store_true', help="Show all available speech commands")
    parser.add_argument('-v', '--vad_aggressiveness', type=int, default=3,
                        help="Set aggressiveness of VAD: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive. Default: 3")
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
