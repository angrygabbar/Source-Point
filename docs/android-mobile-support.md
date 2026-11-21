# Android session, push, sync, and issue reporting

## Firebase push setup

Invoice alerts use Firebase Cloud Messaging (FCM). The Android project can build without Firebase values, but push registration and delivery stay off until a Firebase Android app and server credentials are configured.

1. Register a Firebase Android app with the same application ID as the APK (`APPLICATION_ID` in `SourcePoint APK /sourcepoint.properties`).
2. Set `FIREBASE_API_KEY`, `FIREBASE_APP_ID`, `FIREBASE_PROJECT_ID`, and `FIREBASE_SENDER_ID` in the local `SourcePoint APK /sourcepoint.properties` before building. These are Firebase client identifiers, not server credentials. The app registers its Firebase Installation ID (FID) with SourcePoint for direct push delivery.
3. Enable the Firebase Cloud Messaging API for the project and configure a service account on the SourcePoint server. Set either `FIREBASE_SERVICE_ACCOUNT_FILE` to a protected server-side JSON file or `FIREBASE_SERVICE_ACCOUNT_JSON` to its JSON contents. Set `FIREBASE_PROJECT_ID` on the server if it is not present in the service account file.
4. Deploy the database migration and restart the Flask web/API service and Celery worker. Invoice emails and scheduled invoice reminders queue the matching push delivery through Celery.
5. Install the newly built APK, sign in, and allow invoice notifications when Android asks. A push is sent only when the invoice recipient has a linked SourcePoint user account and a registered Android device.

Do not commit a service-account JSON file or put server credentials in `sourcepoint.properties` or the APK.

## Session and sync behavior

The mobile login returns Flask's remember cookie with a ten-year duration. Android stores the authentication cookies encrypted with Android Keystore and removes them when the user signs out. A saved session is checked before the public landing screen is shown.

The app syncs the signed-in user's server summary on foreground resume and every five minutes while open. WorkManager repeats the summary sync in the background with network access; Android may defer that work, and its minimum repeat interval is 15 minutes. Feature screens load their current records from the server when opened. Invoice alerts use FCM for prompt delivery, while the background sync keeps the account summary current.

## Issue reports

The floating **Report issue** action is available on native screens and integrated web modules. The report stores the user's description, error code, page, app/device versions, and (when selected) a bounded local trail of recent API and app errors. The trail excludes request bodies, passwords, and session cookies. Admin users can review the latest 100 reports from **Mobile issue reports** in the admin app.
