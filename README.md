# bsdeej
Python app to monitor sliders for volume control

Original source - https://bendiksens.net/posts/deej-sound-control-for-linux-written-in-python/

The original has been modified as follows:
* selectable master slide
* all output device volumes are changed when master slide is changed
* app process binary names are used instead of app names
* volumes not changed unless slide value changes by +-5
* moving slide up increases volume / moving it down decreases volume
* tty device and number of sliders set via variables at top of script

## Running it locally

Create a virtual environment and install dependencies

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
requirements.txt:

```
pulsectl
pyserial-asyncio
asyncio
```
Make sure your user can talk to the serial device (you will probably need to restart after being added to the group). Your group name maybe different.

```
sudo usermod -a -G uucp $USER
```
Start the script
```
source venv/bin/activate
python bsdeej.py
```

You should see messages about connecting to the serial port and setting volumes.
