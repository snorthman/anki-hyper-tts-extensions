# Anki HyperTTS Community Contributions

This repository contains community-contributed services for the HyperTTS Anki addon (https://github.com/Vocab-Apps/anki-hyper-tts)

# How to use the services
## Download the service file
You can use any of the services in the [services](services/) directory by simply downloading them and placing them in the correct directory. First look for your Anki profile, then go to the HyperTTS addon directory, and place the downloaded service among other services python files (which should be named `service_<name>.py`)
### Windows
`%APPDATA%/Anki2/addons21/111623432/hypertts_addon/services/`
### MacOSX
`~/Library/Application Support/Anki2/addons21/111623432/hypertts_addon/services/`
### Linux
`~/.local/share/Anki2/addons21/111623432/hypertts_addon/services/`
## Enable the service in HyperTTS
go to Anki `Tools` menu, then `HyperTTS: Services Configuration`, locate the service you just added, and enable it. You may need to set some configuration files.

# Creating new services
If you'd like to create new HyperTTS services which interface with a TTS engine, whether local, open source or online, it's very easy, it only requires creating a single python script.
