# Getting Started with ARES Android Agent

## Prerequisites
- Android Studio Hedgehog (2023.1.1) or newer
- JDK 17
- Android SDK 34 (Android 14) with Build-Tools 34.0.0
- An Android Emulator (API 34 Recommended) or physical Android device in Developer Mode

---

## 1. Project Import
1. Open Android Studio.
2. Select **Open an Existing Project** and navigate to `android-agent/`.
3. Wait for Gradle sync to complete.

---

## 2. Running on Android Emulator
1. Launch an Android Virtual Device (AVD) running Android 14 (API 34).
2. The emulator automatically maps `10.0.2.2` to the host machine's `localhost`.
3. Ensure the ARES FastAPI backend is running:
   ```bash
   cd ares/backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Click **Run 'app'** in Android Studio.
5. Grant Notification permission when prompted to allow the foreground assessment service to run.

---

## 3. Running Unit Tests
To execute all local JVM unit tests without an emulator:
```bash
cd android-agent
./gradlew test
```
(On Windows: `gradlew.bat test`)
