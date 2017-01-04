# piclicktrack: graphical metronome + MIDI clock master

I am quite astonished and frustrated at the state of metronome apps in the world today. It seems the vast majority of them are written by people who don't understand schedulers, `usleep()`, or jitter.

My keyboards also have shitty MIDI implementations that do not forward clock events, and their internal clocks are (unsurprisingly) also inaccurate (thanks Nord!). So for some time, I have been desperately searching for a way to get everything synced up to real time and found absolutely nothing.

So here you have it: piclicktrack.

## Features

* Qt GUI designed for small touchscreen interfaces
* Microsecond-accuracy metronome
* Dispatches MIDI clock events to all connected MIDI devices
* Can act as a master (originating clock events) or dispatcher (receiving and forwarding clock events)

While it is designed to run on a Raspberry Pi (hence the name) with an SPI touchscreen such as Adafruit's 2.8" or 3.5" PiTFT modules, it is capable of running on any Linux system that meets the required dependencies.

## Dependencies

* Python 3
* [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi)
* pyqt4
* [pyalsaaudio](https://github.com/larsimmisch/pyalsaaudio)

# Operating modes

There are two operating modes: master and thru. They do exactly what you would expect. Master mode causes the application to be the initiator of all clock/click events, setting its own tempo. Thru mode requires you to select a MIDI input device, after which point the application will forward any clock events received on that input device and make some attempt at guessing the tempo.

## Master mode

Upon entering master mode, the application will show a UI allowing you to select a song and set the tempo. If you have multiple songs, advancing between them will recall that song's tempo.

## Thru mode

When you enter thru mode, you will be prompted to select a MIDI input device. After selecting your input device the GUI will begin forwarding events from that device to all connected MIDI output ports. An indicator in the UI will blink to show activity and the UI will do its best to guess the incoming tempo.

## Technical details

The metronome's timekeeping uses the monotonic system clock (`time.monotonic()` in Python). Even if the CPU gets choked up for a second, when things calm down the metronome will be accurate to where it originally was when it started.

This is critical to keeping your MIDI equipment in sync with the rest of the band on stage.

The clock events are dispatched from a timekeeping thread (`TimedDispatcher` in [dispatcher.py](clicktrack/dispatcher.py)) to workers for MIDI events (`ClickOutput`) and OSS (`ClickSound`). These workers take care of getting the click message out asynchronously while the main thread continues its job of keeping time.

The core of this is the `HrTimer` (high resolution timer) class, which uses a backoff algorithm to approach the deadline - it sleeps for ~90% of the gap remaining between now and the next event, which backs down then triggers it as soon as the deadline has passed. Further events are based on the interval from the start time, not on the event trigger time.

# Author

[Dan Fuhry](mailto:dan+piclicktrack@fuhry.com)

> piclicktrack - a highly accurate Python metronome
> Copyright (C) 2017 Dan Fuhry
> 
> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
> 
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                                                                                                                                                                                       
> GNU General Public License for more details.
> 
> You should have received a copy of the GNU General Public License
> along with this program.  If not, see [http://www.gnu.org/licenses/](http://www.gnu.org/licenses/).

Please note: I am serious about keeping this code free and have little patience for those who disregard the GPL. If you use this in a commercial product and don't release the source code to any application that uses it, I will aggressively enforce the license.
