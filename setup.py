#!/usr/bin/env python3

from setuptools import setup

setup(
	name='piclicktrack',
	version='0.0.0',
	license='GPLv3+',
	description='Metronome/click track GUI with full MIDI support and extremely accurate timekeeping.',
	keywords='midi metronome clicktrack',
	# From https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers=[
		# Development status
		'Development Status :: 2 - Pre-Alpha',
		# Target audience
		'Intended Audience :: End Users/Desktop',
		# Type of software
		'Topic :: Multimedia :: Sound/Audio :: MIDI',
		# Kind of software
		'Environment :: X11 Applications :: Qt',
		# License (must match license field)
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		# Operating systems supported
		'Operating System :: POSIX :: Linux',
		# Supported Python versions
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3 :: Only',
		'Programming Language :: Python :: 3.5',
		],
	author='Dan Fuhry',
	author_email='dan@fuhry.com',
	url='https://github.com/fuhry/piclicktrack',
	packages=['clicktrack'],
	install_requires=[
		'PyQt5',
		'python-rtmidi',
		'pyalsaaudio',
		],
	scripts=['piclicktrack'],
)
