# Bridge iOS

SwiftUI client for the Bridge server.

The app is intentionally small:

- Apps tab: available mini-apps, with Podcast This prioritized for v0.
- Active tab: generic jobs and persistent sessions.
- Settings tab: server URL, mock-data toggle, connection status.

## Generate the Project

```bash
cd ios
xcodegen generate
open Bridge.xcodeproj
```

## Local Server

```bash
cd ../server
uv run bridge serve --host 0.0.0.0 --port 8080
```

Set the iOS app server URL to:

- simulator: `http://127.0.0.1:8080`
- phone on a private network: `http://<private-host-or-ip>:8080`

Mock Data in Settings lets the UI run without a server while the backend or Podcast
This integration is moving.
