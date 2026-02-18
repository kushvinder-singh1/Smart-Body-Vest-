"""
Run the Firebase cloud listener (Module 2).
Listens for sensor data, runs LSTM + DNN + safety, writes heating command.
Requires: .env with FIREBASE_CREDENTIALS and FIREBASE_DB_URL, or set them in the environment.
"""
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def main():
    from module2.firebase_bridge import listen_and_process, FIREBASE_AVAILABLE, init_firebase

    if not FIREBASE_AVAILABLE:
        print("Install: pip install firebase-admin")
        sys.exit(1)
    if not init_firebase():
        print("Firebase not configured.")
        print("  - Set FIREBASE_CREDENTIALS to your service account JSON path (e.g. serviceAccountKey.json)")
        print("  - Set FIREBASE_DB_URL to your Realtime Database URL (e.g. https://YOUR_PROJECT.firebaseio.com)")
        print("  - Or create a .env file in the project root with these variables.")
        sys.exit(1)
    print("Starting listener (Ctrl+C to stop)...")
    listen_and_process()

if __name__ == "__main__":
    main()
