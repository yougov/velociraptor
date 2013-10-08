"""
Block until a lock (indicated by sys.argv[1]) is obtained, and thereafter
stream the stdin to stdout.
"""

from __future__ import print_function

import sys
import os
import argparse

sys.path.append(os.path.dirname(__file__))

import yg.lockfile

BLOCK_SIZE=2**15

def stream():
	for block in sys.stdin.read(BLOCK_SIZE):
		sys.stdout.write(block)

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('filename', help='lock file name')
	return parser.parse_args()

def main():
	filename = get_args().filename
	print("Obtaining lock on", filename)
	with yg.lockfile.LockFile(filename, timeout=600):
		stream()

main()
