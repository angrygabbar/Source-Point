"""
Jitsi Meet Service for creating video meeting links.
No authentication required - generates instant, working meeting links.
"""

import uuid
import hashlib
from datetime import datetime
from typing import Optional
from flask import current_app


class JitsiMeetService:
    """Service for generating Jitsi Meet video conferencing links"""
    
    # Default Jitsi server (free, public)
    DEFAULT_SERVER = "meet.jit.si"
    
    def __init__(self, server: str = None):
        """
        Initialize Jitsi Meet service.
        
        Args:
            server: Custom Jitsi server URL (optional, defaults to meet.jit.si)
        """
        self.server = server or current_app.config.get('JITSI_SERVER', self.DEFAULT_SERVER)
    
    def create_meeting(
        self,
        title: str,
        interview_id: int = None,
        scheduled_time: datetime = None
    ) -> dict:
        """
        Create a Jitsi Meet room link.
        
        Args:
            title: Meeting title (used to generate room name)
            interview_id: Optional interview ID for uniqueness
            scheduled_time: Optional scheduled time
        
        Returns:
            Dict with 'meet_link' and 'room_name'
        """
        # Generate unique room name
        room_name = self._generate_room_name(title, interview_id, scheduled_time)
        
        # Create meeting URL
        meet_link = f"https://{self.server}/{room_name}"
        
        current_app.logger.info(f"Created Jitsi Meet room: {room_name}")
        
        return {
            'meet_link': meet_link,
            'room_name': room_name,
            'server': self.server
        }
    
    def _generate_room_name(
        self,
        title: str,
        interview_id: int = None,
        scheduled_time: datetime = None
    ) -> str:
        """
        Generate a unique, readable room name.
        
        Format: SourcePoint-{sanitized-title}-{unique-code}
        Example: SourcePoint-TechInterview-a3b7c9
        """
        # Sanitize title (remove special chars, limit length)
        safe_title = ''.join(c for c in title if c.isalnum() or c == ' ')
        safe_title = safe_title.replace(' ', '')[:20]
        
        # Generate unique code
        unique_string = f"{title}-{interview_id or ''}-{scheduled_time or ''}-{uuid.uuid4()}"
        unique_hash = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        
        # Combine into room name
        room_name = f"SourcePoint-{safe_title}-{unique_hash}"
        
        return room_name
    
    def get_meeting_info(self, room_name: str) -> dict:
        """
        Get meeting information and URLs.
        
        Args:
            room_name: The Jitsi room name
        
        Returns:
            Dict with meeting details
        """
        return {
            'meet_link': f"https://{self.server}/{room_name}",
            'room_name': room_name,
            'server': self.server,
            'features': {
                'video': True,
                'audio': True,
                'screen_share': True,
                'chat': True,
                'recording': True,
                'no_account_required': True
            }
        }


# Convenience function for quick link generation
def generate_jitsi_link(title: str, interview_id: int = None) -> str:
    """
    Quick helper to generate a Jitsi Meet link.
    
    Args:
        title: Meeting title
        interview_id: Optional interview ID
    
    Returns:
        Full Jitsi Meet URL
    """
    service = JitsiMeetService()
    result = service.create_meeting(title=title, interview_id=interview_id)
    return result['meet_link']
