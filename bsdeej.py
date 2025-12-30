import asyncio
import serial_asyncio
import pulsectl
from pulsectl import PulseVolumeInfo

# Initialize PulseAudio control
pulse = pulsectl.Pulse('audio-control')

SERIAL_PORT = '/dev/ttyUSB1'
SLIDER_COUNT = 5
MASTER_VOLUME_SLIDER = 4 # counting from 0 on the left

# Mapping of slider indexes to target application process names.
# you can list multiple applications as a list.
slider_mapping = {
    0: "youtube-music",
    1: [
        "vlc",
        "mpv"
        ],
    2: [
        "chromium",
        "firefox",
        "msedge"
        ],
    3: "chrome"
}

class SerialReaderProtocol(asyncio.Protocol):
    def __init__(self, pulse):
        self.pulse = pulse
        self.buffer = b""
        self.last_values = None
        self.connection_lost_future = asyncio.get_running_loop().create_future()

    def connection_made(self, transport):
        self.transport = transport
        print("Serial connection opened. Connected successfully!")

    def data_received(self, data):
        self.buffer += data
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                decoded_line = line.decode('utf-8').strip()
            except UnicodeDecodeError as e:
                continue
            self.process_line(decoded_line)

    def process_line(self, line):
        # Expected format: "1023|1023|1023|1023|1023"
        parts = line.split('|')
        if len(parts) != 5:
            return

        try:
            slider_values = [int(val) for val in parts]
        except ValueError:
            return

        # Only process if the slider values have changed more than 5 from original
        if not self.last_values:
            self.last_values = slider_values

        changed = False
        master_volume_changed = False

        # check each slider for changes
        for vol_key, vol_value in enumerate(slider_values):
            if (vol_value > (self.last_values[vol_key] + 5)) or (vol_value < (self.last_values[vol_key] - 5)):
                changed = True

        # did the master volume slider change
        if (slider_values[MASTER_VOLUME_SLIDER] > self.last_values[MASTER_VOLUME_SLIDER] + 5) or (slider_values[MASTER_VOLUME_SLIDER] < self.last_values[MASTER_VOLUME_SLIDER] - 5):
            master_volume_changed = True

        # no changes
        if changed == False and master_volume_changed == False:
                return  # Data hasn't changed; ignore it.

        self.last_values = slider_values

        # Map slider values to volume 0-100 higher is louder
        volumes = [value / 1023 for value in slider_values]

        # change all volumes when master slider is moved and not just the default device
        if master_volume_changed:
            for sink in self.pulse.sink_list():
                self.pulse.volume_set_all_chans(sink, volumes[MASTER_VOLUME_SLIDER])
            master_volume_changed = False

        # Sliders for specific applications.
        for idx in range(0, SLIDER_COUNT):
            mapping = slider_mapping.get(idx)
            if mapping and idx != MASTER_VOLUME_SLIDER:
                if isinstance(mapping, list):
                    for app in mapping:
                        self.set_volume_for_app(app, volumes[idx])
                else:
                    self.set_volume_for_app(mapping, volumes[idx])

    def set_master_volume(self, volume):
        default_sink_name = self.pulse.server_info().default_sink_name
        default_sink = next((sink for sink in self.pulse.sink_list() 
                             if sink.name == default_sink_name), None)
        if default_sink is not None:
            new_vol = PulseVolumeInfo([volume] * len(default_sink.volume.values))
            self.pulse.volume_set(default_sink, new_vol)

    def set_volume_for_app(self, app_name, volume):
        sink_inputs = self.pulse.sink_input_list()
        found = False
        for sink_input in sink_inputs:
            if sink_input.proplist.get('application.process.binary') == app_name:
                new_vol = PulseVolumeInfo([volume] * len(sink_input.volume.values))
                self.pulse.volume_set(sink_input, new_vol)
                found = True

    def connection_lost(self, exc):
        print("Serial connection lost.")
        if not self.connection_lost_future.done():
            self.connection_lost_future.set_result(True)

async def main():
    loop = asyncio.get_running_loop()
    serial_port = SERIAL_PORT
    baud_rate = 9600

    while True:
        try:
            # Attempt to create a serial connection.
            print(f"Trying to connect to {serial_port} at {baud_rate} baud...")
            transport, protocol = await serial_asyncio.create_serial_connection(
                loop, lambda: SerialReaderProtocol(pulse), serial_port, baudrate=baud_rate
            )
            # Wait until the protocol signals that the connection was lost.
            await protocol.connection_lost_future
            print("Connection closed. Reconnecting...")
        except Exception as e:
            print("Error during serial connection:", e)
        # Wait before attempting to reconnect.
        await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())

