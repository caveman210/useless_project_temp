import base64
import cv2
import uvicorn
import socketio
import numpy as np
import torch
from fastapi import FastAPI  # Make sure this is imported
from torchvision import models
from torchvision.transforms import functional as F
from scipy.spatial.distance import cosine
from ultralytics import YOLO
from threading import Thread
import queue
import os
from dotenv import load_dotenv

# Initialize FastAPI app
fastapi_app = FastAPI()

# Initialize Socket.IO server
# The async_mode='asgi' is crucial for integrating with FastAPI
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Wrap the FastAPI app with the Socket.IO middleware
app = socketio.ASGIApp(sio, fastapi_app)

# Load the pre-trained YOLOv8 model
# 'yolov8n.pt' is the nano version, it's fast but less accurate.
# For better accuracy, consider 'yolov8m.pt' (medium) or 'yolov8l.pt' (large).
# model = YOLO('yolov8n.pt')

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")
detection_model = YOLO('yolov8m.pt')
reid_model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
reid_model = torch.nn.Sequential(
    *(list(reid_model.children())[:-1])).to(device)
reid_model.eval()

load_dotenv()
video_stream_url = os.getenv("IP_ADDR")

# Open a connection to the default camera (index 0)
# If you have multiple cameras, you might need to change the index (e.g., 1, 2).
# This class reads the camera stream in a separate thread to prevent frame backlog


class VideoStreamReader:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.q = queue.Queue()
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while True:
            success, frame = self.stream.read()
            if not self.q.empty():
                try:
                    self.q.get_nowait()  # Discard previous (old) frame
                except queue.Empty:
                    pass
            self.q.put((success, frame))

    def read(self):
        return self.q.get()


# Setup the camera using the new threaded reader
video_stream_url = os.getenv("IP_ADDR")

try:
    print("Connecting to local ADB-forwarded stream...")
    camera = VideoStreamReader(video_stream_url)
    print("✅ Successfully connected to reliable ADB stream!")
except Exception as e:
    print(f"Error starting threaded video stream: {e}")
    camera = None

# --- State Management ---
# This set will store the track IDs of unique dogs detected.
# In a real-world scenario, for persistence over long periods (hours/days),
# you would replace this with a more robust Re-ID model and a database.
# For a single session, the tracker's ID is a good proxy.
unique_dog_ids = set()

# --- Socket.IO Event Handlers ---


@sio.event
async def connect(sid, environ):
    """Handles a new client connection."""
    print(f"Client connected: {sid}")
    # Start sending the video feed to the newly connected client
    sio.start_background_task(send_video_feed, sid)


@sio.event
async def disconnect(sid):
    """Handles a client disconnection."""
    print(f"Client disconnected: {sid}")

# --- Core Logic ---


async def send_video_feed(sid):
    """
    Continuously captures frames, processes them for dog detection/tracking,
    and sends the results to a specific client.
    """
    if not camera:
        print("Camera not available. Cannot send video feed.")
        return

    while True:
        # Read a frame from the camera
        success, frame = camera.read()
        if not success:
            await sio.sleep(0.1)  # Wait a bit before trying again
            continue

        # Use YOLO's track() method for combined detection and tracking
        # The 'persist=True' flag tells the tracker to remember tracks between frames.
        # class 16 is 'dog' in COCO dataset
        results = detection_model.track(
            frame, persist=True, classes=[16], verbose=False)

        # Get the annotated frame with boxes drawn on it
        annotated_frame = results[0].plot()

        # Extract tracking information
        if results[0].boxes.id is not None:
            track_ids = results[0].boxes.id.int().cpu().tolist()
            for track_id in track_ids:
                # This logic determines the color of the bounding box
                # Red for a new dog, Green for a returning one.
                # In the annotated_frame from results[0].plot(), boxes are colored by track ID.
                # We can update our unique set here.
                if track_id not in unique_dog_ids:
                    print(f"New unique dog detected! ID: {track_id}")
                    unique_dog_ids.add(track_id)

        # Get the current count of unique dogs
        dog_count = len(unique_dog_ids)

        # Encode the processed frame to JPEG and then to Base64
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        # Prepare the data payload
        data_to_send = {
            'image': f'data:image/jpeg;base64,{frame_base64}',
            'count': dog_count
        }

        # Emit the data to the client's room
        await sio.emit('update', data_to_send, room=sid)

        # A small delay to allow other async tasks to run
        await sio.sleep(0.01)


@fastapi_app.get("/")
def read_root():
    return {"Status": "Dog Re-ID Backend is Running"}

# --- How to Run ---
# In your terminal, run the following command:
# uvicorn main:app --reload --host 0.0.0.0
