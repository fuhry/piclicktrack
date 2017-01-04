import sys
import rtmidi

try:
    from PyQt5 import QtWidgets as QtGui
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtGui, QtCore

import clicktrack.master as ctmaster
from clicktrack.dispatcher import ClickRouter, TimedDispatcher, MIDIInputDispatcher

def munge_widget_size(target):
	policy = QtGui.QSizePolicy()
	policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
	policy.setVerticalPolicy(QtGui.QSizePolicy.Expanding)
	policy.setHorizontalStretch(1)
	policy.setVerticalStretch(1)
	
	target.setSizePolicy(policy)
	for c in target.children():
		if isinstance(c, QtGui.QWidget):
			c.setSizePolicy(policy)
		
		if isinstance(c, QtGui.QPushButton) or isinstance(c, QtGui.QLabel):
			font = c.font()
			font.setPixelSize(20)
			c.setFont(font)
		
		if isinstance(c, QtGui.QLabel):
			c.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

"""
Primary widget that constructs the UI chrome and every stage inside it.
"""
class MainWidget(QtGui.QWidget):
	def __init__(self):
		super(self.__class__, self).__init__()
		
		
		master_layout = QtGui.QVBoxLayout()
		
		self.mode_selector = ModeSelector(self)
		master_layout.addWidget(self.mode_selector)
		
		self.master_ui = MasterMode(self)
		master_layout.addWidget(self.master_ui)
		
		self.thru_inputsel_ui = ThruModeInputSel(self)
		master_layout.addWidget(self.thru_inputsel_ui)
		
		self.thru_ui = ThruMode(self)
		master_layout.addWidget(self.thru_ui)
		
		self.setLayout(master_layout)
		munge_widget_size(self)
		
		self.show_child(self.mode_selector)
		
	def show_child(self, child):
		self.mode_selector.hide()
		self.master_ui.hide()
		self.thru_inputsel_ui.hide()
		self.thru_ui.hide()
		child.start()
		child.show()
	
	def shutdown(self):
		self.master_ui.shutdown()
		self.thru_ui.shutdown()

"""
Mode selector UI
"""
class ModeSelector(QtGui.QWidget):
	main_widget = None
	def __init__(self, main_widget):
		super(self.__class__, self).__init__()
		
		self.main_widget = main_widget
		
		layout = QtGui.QVBoxLayout()
		label = QtGui.QLabel("Select mode")
		label.maximumHeight = 20
		layout.addWidget(label)
		
		btn_master = QtGui.QPushButton('Master')
		btn_master.clicked.connect(self.select_master)
		layout.addWidget(btn_master)
		layout.setStretchFactor(btn_master, 3)
		
		btn_thru = QtGui.QPushButton('Thru')
		btn_thru.clicked.connect(self.select_thru)
		layout.addWidget(btn_thru)
		layout.setStretchFactor(btn_thru, 3)
		
		self.setLayout(layout)
		munge_widget_size(self)
		
	def start(self):
		pass
		
	@QtCore.pyqtSlot()
	def select_master(self):
		self.main_widget.show_child(self.main_widget.master_ui)
	
	@QtCore.pyqtSlot()
	def select_thru(self):
		self.main_widget.show_child(self.main_widget.thru_inputsel_ui)

"""
Master mode UI
"""
class MasterMode(QtGui.QWidget):
	main_widget = None
	master = None
	
	song_lbl = None
	tempo_lbl = None
	
	start_btn = None
	
	clicker = None
	
	def __init__(self, main_widget):
		super(self.__class__, self).__init__()
		
		self.main_widget = main_widget
		self.master = ctmaster.ClickMaster()
		self.clicker = ClickRouter()
		
		layout = QtGui.QVBoxLayout()
		
		# Row 1: song selection
		song_row = QtGui.QHBoxLayout()
		
		# previous song
		prev_btn = QtGui.QPushButton('<')
		prev_btn.clicked.connect(self.prev_song)
		song_row.addWidget(prev_btn)
		
		# song display
		self.song_lbl = QtGui.QLabel()
		song_row.addWidget(self.song_lbl)
		
		# next song
		next_btn = QtGui.QPushButton('>')
		next_btn.clicked.connect(self.next_song)
		song_row.addWidget(next_btn)
		
		# add song
		add_btn = QtGui.QPushButton('+')
		add_btn.clicked.connect(self.add_song)
		song_row.addWidget(add_btn)
		
		layout.addLayout(song_row)
		
		# Row 2: tempo selection
		tempo_row = QtGui.QHBoxLayout()
		
		tempo_row_lbl = QtGui.QLabel('Tempo:')
		tempo_row.addWidget(tempo_row_lbl)
		
		# decrement tempo by 10
		dec10_button = QtGui.QPushButton('-10')
		dec10_button.clicked.connect(self.decrement_tempo_10)
		tempo_row.addWidget(dec10_button)
		
		# decrement tempo by 1
		dec1_button = QtGui.QPushButton('-1')
		dec1_button.clicked.connect(self.decrement_tempo_1)
		tempo_row.addWidget(dec1_button)
		
		# tempo display
		self.tempo_lbl = QtGui.QLabel()
		tempo_row.addWidget(self.tempo_lbl)
		
		# increment tempo by 1
		inc1_button = QtGui.QPushButton('+1')
		inc1_button.clicked.connect(self.increment_tempo_1)
		tempo_row.addWidget(inc1_button)
		
		# increment tempo by 10
		inc10_button = QtGui.QPushButton('+10')
		inc10_button.clicked.connect(self.increment_tempo_10)
		tempo_row.addWidget(inc10_button)
		
		layout.addLayout(tempo_row)
		
		# row 3: start/stop button
		start_row = QtGui.QHBoxLayout()
		
		self.start_btn = QtGui.QPushButton("I don't know my state")
		self.start_btn.clicked.connect(self.toggle)
		
		start_row.addWidget(self.start_btn)
		
		layout.addLayout(start_row)
		
		self.setLayout(layout)
		munge_widget_size(self)
		self._redraw()
	
	def start(self):
		self.clicker.start()
		self.start_btn.setText('Stop')
	
	def stop(self):
		self.clicker.stop()
		self.start_btn.setText('Start')
		
	def shutdown(self):
		if self.clicker.started:
			self.stop()
	
	def toggle(self):
		if self.clicker.started:
			self.stop()
		else:
			self.start()
	
	def _redraw(self):
		self.song_lbl.setText("Song %d/%d" % (self.master.get_song() + 1, self.master.count_songs() + 1))
		self.tempo_lbl.setText("%d" % (self.master.get_tempo()))
		self.clicker.set_tempo(float(self.master.get_tempo()))
		
	def _errmsg(self, exception):
		mbox = QtGui.QMessageBox()
		mbox.setIcon(QtGui.QMessageBox.Critical)
		mbox.setText(exception.message)
		mbox.addButton(QtGui.QMessageBox.Ok)
		mbox.setDefaultButton(QtGui.QMessageBox.Ok)
		mbox.exec_()
	
	@QtCore.pyqtSlot()
	def prev_song(self):
		index = self.master.get_song() - 1
		try:
			self.master.select_song(index)
		except ctmaster.ClickMasterError as e:
			pass
		
		self._redraw()
	
	@QtCore.pyqtSlot()
	def next_song(self):
		index = self.master.get_song() + 1
		try:
			self.master.select_song(index)
		except ctmaster.ClickMasterError as e:
			pass
		
		self._redraw()
	
	@QtCore.pyqtSlot()
	def add_song(self):
		self.master.add_song()
		self.master.last_song()
		
		self._redraw()
	
	@QtCore.pyqtSlot()
	def decrement_tempo_10(self):
		try:
			self.master.change_tempo(-10)
		except ctmaster.ClickMasterError as e:
			self._errmsg(e)
			
		self._redraw()
	
	@QtCore.pyqtSlot()
	def decrement_tempo_1(self):
		try:
			self.master.change_tempo(-1)
		except ctmaster.ClickMasterError as e:
			self._errmsg(e)
		self._redraw()
	
	@QtCore.pyqtSlot()
	def increment_tempo_1(self):
		try:
			self.master.change_tempo(1)
		except ctmaster.ClickMasterError as e:
			self._errmsg(e)
		self._redraw()
	
	@QtCore.pyqtSlot()
	def increment_tempo_10(self):
		try:
			self.master.change_tempo(10)
		except ctmaster.ClickMasterError as e:
			self._errmsg(e)
		self._redraw()
	

"""
Thru mode UI - input selector
"""
class ThruModeInputSel(QtGui.QWidget):
	main_widget = None
	midi_input = None
	
	def __init__(self, main_widget):
		super(self.__class__, self).__init__()
		
		self.main_widget = main_widget
		
		layout = QtGui.QVBoxLayout()
		
		layout.addWidget(QtGui.QLabel('Select a MIDI input device for clock source:'))
		
		self.input_list = QtGui.QListWidget()
		for port in self._get_midi_inputs():
			self.input_list.addItem(QtGui.QListWidgetItem(port))
		
		layout.addWidget(self.input_list)
		
		select_btn = QtGui.QPushButton('Continue')
		select_btn.clicked.connect(self.i_choose_you)
		layout.addWidget(select_btn)
		
		self.setLayout(layout)
		
	def start(self):
		pass
	
	def shutdown(self):
		pass
	
	def _get_midi_inputs(self):
		if not self.midi_input:
			self.midi_input = rtmidi.MidiIn()
		
		names = []
		
		for i in range(0, self.midi_input.get_port_count()):
			names.append(self.midi_input.get_port_name(i))
		
		return names
		
	@QtCore.pyqtSlot()
	def i_choose_you(self):
		chosen = self.input_list.currentItem()
		if not chosen:
			return
			
		chosen = chosen.text()
		
		opened = False
		for i in range(0, self.midi_input.get_port_count()):
			if chosen == self.midi_input.get_port_name(i):
				self.midi_input.open_port(i)
				opened = True
		
		if not opened:
			raise 'MIDI port disappeared before we could open it'
		
		self.main_widget.thru_ui.set_port(self.midi_input)
		self.main_widget.show_child(self.main_widget.thru_ui)

"""
Thru mode UI
"""
class ThruMode(QtGui.QWidget):
	main_widget = None
	port = None
	tempo_label = None
	clicker = None
	detector = None
	
	def __init__(self, main_widget):
		super(self.__class__, self).__init__()
		
		self.detector = ctmaster.TempoDetector()
		
		layout = QtGui.QVBoxLayout()
		
		self.tempo_label = QtGui.QLabel('0')
		font = self.tempo_label.font()
		font.setPixelSize(72)
		self.tempo_label.setFont(font)
		self.tempo_label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
		layout.addWidget(self.tempo_label)
		
		self.setLayout(layout)
		
		self.main_widget = main_widget
	
	def start(self):
		if not self.port:
			raise 'No port selected'
		
		self.clicker = ClickRouter(MIDIInputDispatcher)
		self.clicker.set_input_port(self.port)
		self.clicker.start(self.update_tempo)
	
	def shutdown(self):
		if not self.port:
			return
			
		self.clicker.stop()
	
	def set_port(self, port):
		self.port = port
	
	def update_tempo(self):
		self.detector.beat()
		try:
			tempo = round(self.detector.get_tempo())
			self.tempo_label.setText("%d" % (tempo))
		except ctmaster.ClickMasterError:
			pass
		

"""
Primary class for the application.
"""
class MainUI:
	main_widget = False
	app = False
	
	def __init__(self):
		self.app = QtGui.QApplication(sys.argv)
		self.main_widget = MainWidget()
	
	"""
	Run the application.
	"""
	def run(self):
		geom = self.app.desktop().screenGeometry()
		if geom.width() <= 480 and geom.height() <= 320:
			self.main_widget.showFullScreen()
		else:
			self.main_widget.resize(480, 320)
			self.main_widget.show()
		
		result = self.app.exec_()
		self.main_widget.shutdown()
		return result