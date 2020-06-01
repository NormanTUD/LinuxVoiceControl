# LinuxVoiceControl

This is a script that allows some parts of the computer to be voice controlled. It is based on the `mic_wav_streaming.py`
of the DeepSpeech-examples, but expands some small features. Right now, only german inputs are supported.

## Warning

When cloning, you need git lfs or you won't get the full repo!

## Was kann man sagen?

> python3 voicecontrol.py  --model 51.565295.output_graph.pb --scorer de_kenlm.scorer --helpspeech

## Installation

See install.sh

## !!!WORK IN PROGRESS!!!

This is very much work in progress. Not all commands are listed (check source code for all commands). Also, the german language model
is far from finished!

## How to run this?

> python3 voicecontrol.py --model 51.565295.output_graph.pb --scorer de_kenlm.scorer

## "commands" not found from wmctrl

Edit the file /usr/local/lib/python3.7/dist-package/wmctrl.py and a change line 2 to

> from subprocess import getoutput
