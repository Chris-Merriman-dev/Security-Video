# Security Video

An application designed for facial recognition and security video analysis. This project was a way to practice **Python** and build a working facial recognition tool. It allows you to select a camera, detect faces in the video feed, and store information about recognized individuals in a database.

### Features
* **Facial Recognition:** Utilizes the `face_recognition` library to detect and identify faces.
* **Device Camera Selection:** You can choose which device camera to use for the live video feed.
* **Database Integration:** Stores recognized faces and personal information in a **Pandas** database.
* **Occurrence Tracking:** Keeps a log of every time a recognized individual is seen.
* **Multiprocessing:** Employs multiple CPU cores to handle facial recognition without slowing down the video feed.

### Files Needed
* `face_data.py`