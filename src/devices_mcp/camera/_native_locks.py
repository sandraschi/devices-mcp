"""Process-wide locks for native (non-thread-safe) camera libraries.

OpenCV/DirectShow capture opens and graph teardown crash the native heap
(0xc0000374) when they run concurrently - observed as several executor threads
inside ``webcam._probe_resolution`` at crash time (faulthandler trace). Every
``cv2.VideoCapture(...)`` construction in this repo must hold ``cv_open_lock``.
Reads on already-open captures stay concurrent.
"""

import threading

cv_open_lock = threading.Lock()
