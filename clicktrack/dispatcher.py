import threading
import rtmidi
import time
import wave
import alsaaudio
import os
import re
from queue import Queue

MSG_CLOCK_START = 0xFA
MSG_CLOCK_BEAT  = 0xF8
MSG_CLOCK_CONTINUE = 0xFB
MSG_CLOCK_STOP  = 0xFC

"""
Front-end to the click dispatcher.

The click dispatcher uses a thread pool consisting of one thread per MIDI output
and one master thread. The master thread runs an HrTimer (see below) that
dispatches click events to the port threads as close to synchronously as
possible (the lag time is the time it takes for Queue.put()).
"""

class ClickRouter:
	threads = []
	backend = None
	dispatcher = None
	started = False
	debounce_ports = []
	multiplier = 1
	
	tempo = 120.0
	input_port = None
	
	def __init__(self, backend=None):
		self.backend = backend if backend else TimedDispatcher
	
	"""
	Initialization function called before start() kicks off the threads. This
	was originally the constructor, but threading has been cranky about
	restarting threads that were previously stopped.
	"""
	def init(self, callback=None):
		midi_out = rtmidi.MidiOut()
		for i in range(0, midi_out.get_port_count()):
			name = midi_out.get_port_name(i)
			# this is necessary to avoid reflection back into our own port which
			# causes horrible bouncing issues
			if re.search('^RtMidiIn Client:', name):
				continue
			
			print("Opening MIDI output port: %s" % (name))
			self._open_port(i)
		
		# add a thread for playing the audible click
		self.threads.append(ClickSound(self.multiplier))
		
		if callback:
			self.threads.append(ClickCallback(callback))
		
		self.dispatcher = self.backend(self.click)
		
		if isinstance(self.dispatcher, TimedDispatcher):
			self.dispatcher.set_tempo(self.tempo)
		
		if isinstance(self.dispatcher, MIDIInputDispatcher):
			self.dispatcher.set_input_port(self.input_port)
	
	def _open_port(self, i):
		midi_out = rtmidi.MidiOut()
		midi_out.open_port(i)
		
		self.threads.append(ClickOutput(midi_out, i, self))
		
	"""
	Dispatches a click event to the MIDI output ports.
	"""
	def click(self, msg='click'):
		for port in self.threads:
			port.queue.put(msg)
	
	"""
	Start the selected dispatcher.
	"""
	def start(self, callback=None):
		self.init(callback)
		# First start all of the output threads so that they're ready to accept
		# events as soon as the dispatcher starts up.
		#
		# This also sends MSG_CLOCK_START to all slaves.
		for t in self.threads:
			t.start()
		
		# Start the dispatcher, which will instantly begin dispatching click
		# events.
		self.dispatcher.start()
		
		self.started = True
	
	"""
	Stop the selected dispatcher and cleanly terminate all threads.
	"""
	def stop(self):
		self.dispatcher.stop()
		
		for t in self.threads:
			t.stop()
		
		self.threads = []
		self.dispatcher = None
		
		self.started = False
	
	"""
	Change the tempo. Only valid for the timed dispatcher.
	"""
	def set_tempo(self, tempo, multiplier=1):
		self.tempo = tempo
		self.multiplier = multiplier
		if self.dispatcher:
			self.dispatcher.set_tempo(tempo)
		
		for t in self.threads:
			t.set_multiplier(multiplier)
	
	"""
	Set the input port. Only valid for the MIDI input dispatcher.
	"""
	def set_input_port(self, port):
		self.input_port = port
		if self.dispatcher:
			self.dispatcher.set_input_port(port)

"""
Timed clock event dispatcher. This is the "master" thread, which dispatches the
individual clock events to the output thread pool.
"""
class TimedDispatcher(threading.Thread):
	timer = None
	tempo = 120.0
	callback = None
	
	def __init__(self, callback):
		super(self.__class__, self).__init__()
		self.callback = callback
		
		interval = 60.0 / self.tempo / 24.0
		self.timer = HrTimer(interval, self.callback)
	
	def set_tempo(self, tempo):
		self.tempo = tempo
		self.timer.interval = 60.0 / self.tempo / 24.0
	
	def start(self):
		self.timer.should_stop = False
		super(self.__class__, self).start()
	
	def run(self):
		self.timer.run()
	
	def stop(self):
		self.timer.should_stop = True
		self.join()

"""
MIDI clock event based dispatcher
"""
class MIDIInputDispatcher(threading.Thread):
	callback = None
	quit = False
	input_port = None
	
	def __init__(self, callback):
		super(self.__class__, self).__init__()
		self.callback = callback
	
	def start(self):
		self.quit = False
		super(self.__class__, self).start()
	
	def run(self):
		self.input_port.ignore_types(timing=False)
		self.input_port.set_callback(self.recv_message)
		while True:
			if self.quit:
				return
			time.sleep(0.01)
	
	def recv_message(self, result, data=None):
			message, delta_time = result
			if message[0] == MSG_CLOCK_BEAT:
				self.callback()
			elif message[0] == MSG_CLOCK_START:
				self.callback('start')
			elif message[0] == MSG_CLOCK_STOP:
				self.callback('pause')
			elif message[0] == MSG_CLOCK_CONTINUE:
				self.callback('continue')
	
	def stop(self):
		self.quit = True
		self.join()
		
	def set_input_port(self, port):
		self.input_port = port

"""
High resolution interval timer. Runs the provided callback at precise intervals,
limiting CPU usage as much as possible. This uses the monotonic clock to
determine if we are at or past the target time, and uses a backoff algorithm to
approach the deadline as closely as possible.
"""
class HrTimer:
	interval = 0.0
	callback = None
	should_stop = False
	
	"""
	Constructor
	
	@param float
		Interval
	@param callback
		Callback to run when the timer expires. Make sure this is a very fast
		function!
	"""
	def __init__(self, interval, callback):
		self.interval = interval
		self.callback = callback
	
	def run(self):
		last = time.monotonic()
		self.callback()
		while True:
			if self.should_stop:
				break
			
			now = time.monotonic()
			rem = (last + self.interval) - now
			if rem <= 0:
				self.callback()
				# Base the next runtime on the last runtime, which ties back to
				# the start time. This guarantees that we stay very close to
				# alignment to our original start time.
				last += self.interval
			else:
				time.sleep(rem * 0.925)

"""
Output thread for individual MIDI connections.
"""
class ClickOutput(threading.Thread):
	queue = None
	port = None
	index = 0
	router = None
	
	def __init__(self, port, index, router):
		super(self.__class__, self).__init__()
		self.queue = Queue()
		self.port = port
		self.index = index
		self.router = router
		
	def start(self):
		self.port.send_message([MSG_CLOCK_START])
		super(self.__class__, self).start()
	
	def run(self):
		while True:
			msg = self.queue.get()
			if msg == 'click':
				self.port.send_message([MSG_CLOCK_BEAT])
			elif msg == 'stop':
				return
	
	def stop(self):
		self.queue.put('stop')
		self.join()
		self.port.send_message([MSG_CLOCK_STOP])
	
	def set_multiplier(self, multiplier):
		pass

"""
Output thread for the click sound that will be played through the speakers.
"""
class ClickSound(threading.Thread):
	queue = None
	multiplier = 1

	def __init__(self, multiplier):
		super(self.__class__, self).__init__()
		self.queue = Queue()
		self.multiplier = multiplier

	def start(self):
		super(self.__class__, self).start()

	def run(self):
		# search the system for a click file
		paths = [
			os.path.dirname(os.path.realpath(__file__)) + '/data/click.wav',
			'/usr/local/share/piclicktrack/click.wav',
			'/usr/share/piclicktrack/click.wav'
		]
		
		path = None
		
		for p in paths:
			print(p)
			if os.path.exists(p):
				path = p
		
		if not path:
			return
		
		wavfile = wave.open(path, 'rb')
		(num_channels, sample_width, framerate, num_frames, comptype, compname) = wavfile.getparams()
		data = wavfile.readframes(num_frames)
		wavfile.close()
		i = 0

		alsadev = alsaaudio.PCM()
		alsadev.setperiodsize(num_frames)
		if sample_width == 1:
			alsadev.setformat(alsaaudio.PCM_FORMAT_U8)
		elif sample_width == 2:
			alsadev.setformat(alsaaudio.PCM_FORMAT_S16_LE)
		elif sample_width == 3:
			alsadev.setformat(alsaaudio.PCM_FORMAT_S24_LE)
		elif sample_width == 4:
			alsadev.setformat(alsaaudio.PCM_FORMAT_S32_LE)

		while True:
			msg = self.queue.get()
			if msg == 'click':
				if i % (24/self.multiplier) == 0:
					alsadev.write(data)

				i += 1
			elif msg == 'start':
				i = 0
			elif msg == 'stop':
				alsadev.close()
				return

	def stop(self):
		self.queue.put('stop')
		self.join()
	
	def set_multiplier(self, multiplier):
		self.multiplier = multiplier

"""
Output thread for a custom callback
"""
class ClickCallback(threading.Thread):
	queue = None
	callback = None
	
	def __init__(self, callback):
		super(self.__class__, self).__init__()
		self.queue = Queue()
		self.callback = callback
		
	def start(self):
		super(self.__class__, self).start()
	
	def run(self):
		while True:
			msg = self.queue.get()
			if msg == 'click':
				self.callback()
			elif msg == 'stop':
				return
	
	def stop(self):
		self.queue.put('stop')
		self.join()
	
	def set_multiplier(self, multiplier):
		pass
