from clicktrack import gui

"""

"""

def run(argv=[]):
	window_mode = 'auto'
	if '-w' in argv:
		window_mode = 'windowed'
	elif '-f' in argv:
		window_mode = 'fullscreen'
	g = gui.MainUI()
	g.run(window_mode=window_mode)
