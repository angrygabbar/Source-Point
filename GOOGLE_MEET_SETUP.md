# Google Meet Scheduling - Quick Setup Guide

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Apply Database Migration
```bash
flask db upgrade
```

### 3. Google Calendar API Setup

#### For Development (OAuth2):
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project
3. Enable **Google Calendar API**
4. Create **OAuth 2.0 Client ID** (Desktop app)
5. Download as `credentials.json` → place in project root

#### For Production (Service Account):
1. Create service account in Google Cloud Console
2. Download JSON key
3. Set environment variable:
   ```bash
   export GOOGLE_CALENDAR_CREDENTIALS_FILE=/path/to/service-account.json
   ```

### 4. Environment Variables
Add to `.env`:
```bash
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_TIMEZONE=Asia/Kolkata
```

### 5. First Run
```bash
python app.py
```
On first run, browser will open for Google OAuth consent. Approve to create `token.pickle`.

## 📝 Usage

### Schedule Interview
1. Admin Dashboard → **Schedule Interview**
2. Fill form:
   - Title, description
   - Select candidate
   - Select moderators (multiple)
   - Date, time, duration
3. Submit → Google Meet link created automatically

### Manage Interviews
- View: `/admin/hiring/interviews`
- Filter: All, Upcoming, Past, Cancelled
- Actions: Join Meet, Resend Invites, Cancel

## 🔐 Important Files

**DO NOT COMMIT:**
- `credentials.json` - OAuth2 credentials
- `token.pickle` - Auth token
- Service account JSON keys

Add to `.gitignore`:
```
credentials.json
token.pickle
*.json
```

## ✅ Verify Installation

Test that everything works:
```bash
# Check models imported
python -c "from models.interview import Interview, InterviewParticipant; print('✓ Models OK')"

# Check service
python -c "from services.google_calendar_service import GoogleCalendarService; print('✓ Service OK')"
```

## 🎯 Routes Available

- `GET /admin/hiring/interviews/schedule` - Schedule form
- `POST /admin/hiring/interviews/create` - Create interview
- `GET /admin/hiring/interviews` - View all
- `POST /admin/hiring/interviews/<id>/cancel` - Cancel
- `POST /admin/hiring/interviews/<id>/resend-invites` - Resend

## 📧 Email Templates

Located in `templates/mail/`:
- `interview_scheduled_moderator.html`
- `interview_scheduled_candidate.html`
- `interview_cancelled.html`

## 🐛 Troubleshooting

**"credentials.json not found"**
→ Download OAuth2 credentials from Google Cloud Console

**"Token expired"**
→ Delete `token.pickle` and re-authenticate

**"Calendar API not enabled"**
→ Enable Google Calendar API in Google Cloud Console

**"No module named google.auth"**
→ Run `pip install -r requirements.txt`

## 📚 Full Documentation

See `walkthrough.md` for complete implementation details.
