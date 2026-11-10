# Document Assistant — Flutter client

Native Flutter client for the Document Assistant API in the parent directory.

## Run

Start the backend using the [project setup guide](../README.md), then run:

```sh
flutter pub get
flutter run -d macos
```

Android Emulator uses `http://10.0.2.2:8000`; macOS and iOS Simulator use `http://127.0.0.1:8000`. Override with `--dart-define=API_BASE_URL=http://YOUR_SERVER:8000` when needed. Keep the prototype backend local; it has no authentication.

The client supports file upload, a persistent document library, scoped retrieval, source cards, optional local generation, and document deletion. All embedding and LLM inference happens in the backend, not on the phone. Scanned PDFs are not supported.

## Verify

```sh
flutter analyze
flutter test
```

Physical-device networking, file picking, and signing need separate native-device validation.
