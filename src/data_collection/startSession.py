"""
Start a data collection session.
""" 
from pylsl import StreamInfo, StreamInlet, resolve_stream

def main():
    streams = resolve_stream()
    