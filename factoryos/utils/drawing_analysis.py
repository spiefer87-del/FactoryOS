import cv2
import numpy as np


def detect_circles(image_path):
    """
    Detect circles (holes/features) in a drawing image.

    Returns:
        list of dict:
        [
            {"x": int, "y": int, "r": int}
        ]
    """

    # Bild laden
    img = cv2.imread(image_path)

    if img is None:
        return []

    # Graustufen
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Noise reduzieren
    gray = cv2.GaussianBlur(gray, (9, 9), 1.5)

    # Kreiserkennung
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=40,
        param1=50,
        param2=30,
        minRadius=5,
        maxRadius=200
    )

    result = []

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")

        for (x, y, r) in circles:
            result.append({
                "x": int(x),
                "y": int(y),
                "r": int(r)
            })

    return result