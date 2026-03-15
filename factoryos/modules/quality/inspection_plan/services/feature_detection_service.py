import os
from factoryos.utils.drawing_analysis import detect_circles

def detect_drawing_features(image_path):
    return detect_circles(image_path)
