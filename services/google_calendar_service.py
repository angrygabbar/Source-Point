"""
Google Calendar Service for creating interview events with Google Meet links.
Supports both OAuth2 (with token.pickle) and Service Account authentication.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import current_app

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


class GoogleCalendarService:
    """Service for interacting with Google Calendar API"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
    
    def _authenticate(self):
        """Authenticate with Google Calendar API (OAuth or Service Account)"""
        if self.service is not None:
            return
        
        token_file = 'token.pickle'
        service_account_file = current_app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
        
        # Priority 1: OAuth token (created via setup_google_oauth.py)
        if os.path.exists(token_file):
            current_app.logger.info("Using OAuth authentication (token.pickle)")
            with open(token_file, 'rb') as token:
                self.credentials = pickle.load(token)
            
            # Refresh if expired
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    with open(token_file, 'wb') as token:
                        pickle.dump(self.credentials, token)
                except Exception as e:
                    current_app.logger.error(f"Failed to refresh token: {e}")
                    raise Exception("Google Calendar token expired. Please run setup_google_oauth.py again.")
        
        # Priority 2: Service Account
        elif os.path.exists(service_account_file):
            current_app.logger.info("Using Service Account authentication")
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES
            )
        
        else:
            raise FileNotFoundError(
                "No Google credentials found. Please either:\n"
                "1. Run 'python3 setup_google_oauth.py' for OAuth setup, or\n"
                "2. Add service_account.json for Service Account auth"
            )
        
        # Build the service
        self.service = build('calendar', 'v3', credentials=self.credentials)
        current_app.logger.info("Google Calendar service initialized successfully")
    
    def create_interview_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        duration_minutes: int,
        attendees: List[str],
        timezone: str = None
    ) -> Dict:
        """Create a Google Calendar event with Google Meet link."""
        self._authenticate()
        
        if timezone is None:
            timezone = current_app.config.get('GOOGLE_CALENDAR_TIMEZONE', 'Asia/Kolkata')
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Check if using OAuth (can add attendees and Meet)
        is_oauth = os.path.exists('token.pickle')
        
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 60},
                ],
            },
        }
        
        # Add attendees and Meet only for OAuth (not service account)
        if is_oauth:
            event['attendees'] = [{'email': email} for email in attendees]
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': f"meet-{start_time.timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        
        try:
            calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID', 'primary')
            
            if is_oauth:
                # OAuth: Create with Meet link
                created_event = self.service.events().insert(
                    calendarId=calendar_id,
                    body=event,
                    conferenceDataVersion=1,
                    sendUpdates='all'
                ).execute()
                meet_link = created_event.get('hangoutLink', '')
            else:
                # Service Account: Create without Meet (generate placeholder)
                created_event = self.service.events().insert(
                    calendarId=calendar_id,
                    body=event,
                    sendUpdates='none'
                ).execute()
                # Generate Jitsi Meet link as fallback
                import uuid
                meet_code = str(uuid.uuid4())[:10].replace('-', '')
                meet_link = f"https://meet.jit.si/sourcepoint-interview-{meet_code}"
            
            event_id = created_event.get('id', '')
            current_app.logger.info(f"Created calendar event: {event_id}, Meet link: {meet_link}")
            
            return {
                'event_id': event_id,
                'meet_link': meet_link,
                'html_link': created_event.get('htmlLink', '')
            }
        
        except HttpError as error:
            current_app.logger.error(f"Google Calendar API error: {error}")
            raise Exception(f"Failed to create calendar event: {error}")
    
    def cancel_interview_event(self, event_id: str) -> bool:
        """Cancel a calendar event."""
        self._authenticate()
        try:
            calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID', 'primary')
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates='all'
            ).execute()
            return True
        except HttpError as error:
            current_app.logger.error(f"Google Calendar API error: {error}")
            raise Exception(f"Failed to cancel calendar event: {error}")
