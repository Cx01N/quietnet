import queue
import threading
import time
import pyaudio
import numpy as np
import quietnet
import options
import sys
import psk

FORMAT = pyaudio.paInt16
frame_length = options.frame_length
chunk = options.chunk
search_freq = options.freq
rate = options.rate
sigil = [int(x) for x in options.sigil]
frames_per_buffer = chunk * 10

in_length = 4000
in_frames = queue.Queue(in_length)
points = queue.Queue(in_length)
bits = queue.Queue(in_length // frame_length)

wait_for_sample_timeout = 0.1
wait_for_frames_timeout = 0.1
wait_for_point_timeout = 0.1
wait_for_byte_timeout = 0.1

bottom_threshold = 8000

def process_frames():
    while True:
        try:
            frame = in_frames.get(False)
            fft = quietnet.fft(frame)
            point = quietnet.has_freq(fft, search_freq, rate, chunk)
            points.put(point)
        except queue.Empty:
            time.sleep(wait_for_frames_timeout)

def process_points():
    while True:
        cur_points = []
        while len(cur_points) < frame_length:
            try:
                cur_points.append(points.get(False))
            except queue.Empty:
                time.sleep(wait_for_point_timeout)

        while True:
            while np.average(cur_points) > bottom_threshold:
                try:
                    cur_points.append(points.get(False))
                    cur_points = cur_points[1:]
                except queue.Empty:
                    time.sleep(wait_for_point_timeout)
            next_point = None
            while next_point is None:
                try:
                    next_point = points.get(False)
                except queue.Empty:
                    time.sleep(wait_for_point_timeout)
            if next_point > bottom_threshold:
                bits.put(0)
                bits.put(0)
                cur_points = [cur_points[-1]]
                break
        print("")

        last_bits = []
        while True:
            if len(cur_points) == frame_length:
                bit = int(quietnet.get_bit(cur_points, frame_length) > bottom_threshold)
                cur_points = []
                bits.put(bit)
                last_bits.append(bit)
            if len(last_bits) > 3:
                if sum(last_bits) == 0:
                    break
                else:
                    last_bits = last_bits[1:]
            while len(cur_points) < frame_length:
                try:
                    cur_points.append(points.get(False))
                except queue.Empty:
                    time.sleep(wait_for_point_timeout)

def callback(in_data, frame_count, time_info, status):
    frames = list(quietnet.chunks(quietnet.unpack(in_data), chunk))
    for frame in frames:
        in_frames.put(frame)
    return (None, pyaudio.paContinue)

def start_analysing_stream():
    threads = [
        threading.Thread(target=process_frames),
        threading.Thread(target=process_points)
    ]

    for thread in threads:
        thread.daemon = True
        thread.start()

    while True:
        bit_sequence = []
        while len(bit_sequence) < len(sigil):
            try:
                bit_sequence.append(bits.get(False))
            except queue.Empty:
                time.sleep(wait_for_sample_timeout)

        if bit_sequence[-len(sigil):] == sigil:
            message_bits = []
            while True:
                try:
                    bit = bits.get(False)
                    message_bits.append(bit)
                    if message_bits[-len(sigil):] == sigil:
                        break
                except queue.Empty:
                    time.sleep(wait_for_sample_timeout)

            # Print the received bit sequence for debugging
            print(f"Received bit sequence: {message_bits[:-len(sigil)]}")

            try:
                decoded_message = psk.decode(message_bits[:-len(sigil)])
                print(f"Decoded message: {decoded_message}")
            except ValueError as e:
                print(f"Decoding error: {e}")

if __name__ == "__main__":
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=rate, input=True, frames_per_buffer=frames_per_buffer, stream_callback=callback)
    start_analysing_stream()
