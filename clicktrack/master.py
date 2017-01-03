import time

"""
Back-end class for representing the clicktrack master
"""

class ClickMaster:
	songs = []
	song_index = None
	
	def __init__(self):
		self.add_song()
		self.select_song(0)
	
	"""
	Add a new song
	"""
	def add_song(self):
		self.songs.append(Song())
	
	"""
	Select the last song in the list
	"""
	def last_song(self):
		self.select_song(len(self.songs)-1)
	
	"""
	Select a song by index
	"""
	def select_song(self, index):
		if index < 0 or index > self.count_songs():
			raise ClickMasterError("Index %d out of bounds" % (index))
			
		self.song_index = index
	
	"""
	Change the tempo of the current song
	"""
	def change_tempo(self, change):
		self.songs[self.song_index].change_tempo(change)
	
	"""
	Get the tempo of the current song
	"""
	def get_tempo(self):
		return self.songs[self.song_index].get_tempo()
		
	"""
	Get the index of the current song
	"""
	def get_song(self):
		return self.song_index
	
	"""
	Get number of songs - 1
	"""
	def count_songs(self):
		return len(self.songs) - 1

"""
Back-end class for clicktrack songs
"""
class Song:
	tempo = 120
	
	def __init__(self):
		pass
	
	def change_tempo(self, change):
		if (self.tempo + change) > 500 or (self.tempo + change) < 30:
			raise ClickMasterError("Tempo must be between 30 and 500 bpm")
		
		self.tempo += change
	
	def get_tempo(self):
		return self.tempo

"""
Tempo detector
"""
class TempoDetector:
	beats = []
	
	def beat(self):
		self.beats.append(time.monotonic())
	
	def get_tempo(self):
		if len(self.beats) < 2:
			raise ClickMasterError('Need at least 2 beats recorded')
			
		# remove beats that were recorded more than 5s before the last one
		while min(self.beats) < max(self.beats) - 5:
			self.beats.remove(min(self.beats))
		
		deltas = []
		for i in range(1, len(self.beats)):
			deltas.append(self.beats[i] - self.beats[i-1])
		
		average = sum(deltas) / len(deltas)
		
		bpm = 60 / average
		
		# if we get a very high result, divide the result by 24 as we must be
		# measuring by ppqn, not bpm
		if bpm >= 500:
			return bpm / 24
		
		return bpm

class ClickMasterError(Exception):
	message = ''
	def __init__(self, message):
		super(self.__class__, self).__init__()
		self.message = message