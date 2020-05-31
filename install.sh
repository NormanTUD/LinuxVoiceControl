#!/bin/bash
sudo apt install -y python3 python3-pip libasound2-dev libspeexdsp-dev qalc xsel sed wmctrl
sudo apt install -y libxml2-dev libxslt1-dev zlib1g-dev libffi-dev
sudo apt install -y libsasl2-dev libldap2-dev libssl-dev portaudio19-dev

echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "If libttspico-utils cannot be installed, please"
echo "enable non-free repositories!"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

sudo apt install -y libttspico-utils
sudo pip3 install pyopenssl
sudo pip3 install secrets colored wmctrl pyperclip pyautogui scipy halo webrtcvad wave pyaudio numpy deepspeech==0.7.1 zahlwort2num
