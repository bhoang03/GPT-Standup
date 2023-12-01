from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Set up the Google Calendar API credentials
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = None

# The file token.json stores the user's access and refresh tokens
TOKEN_PATH = 'token.json'

if os.path.exists(TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, 'w') as token:
        token.write(creds.to_json())

# Connect to the Google Calendar API
service = build('calendar', 'v3', credentials=creds)

def get_free_busy_data(calendar_id, time_min, time_max):
    events_result = service.freebusy().query(
        body={
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": calendar_id}],
        }
    ).execute()

    return events_result.get('calendars', {}).get(calendar_id, {}).get('busy', [])

def find_free_time_slots(teammate_calendars, duration_minutes, time_min, time_max):
    busy_times = []
    for calendar_id in teammate_calendars:
        busy_times.extend(get_free_busy_data(calendar_id, time_min, time_max))

    busy_times.sort(key=lambda x: x['start'])
    
    free_time_slots = []
    current_time = time_min
    for busy_time in busy_times:
        busy_start = datetime.fromisoformat(busy_time['start'])
        busy_end = datetime.fromisoformat(busy_time['end'])

        if current_time < busy_start:
            free_time_slots.append({
                'start': current_time.isoformat(),
                'end': busy_start.isoformat()
            })

        current_time = max(current_time, busy_end)

    if current_time < time_max:
        free_time_slots.append({
            'start': current_time.isoformat(),
            'end': time_max.isoformat()
        })

    return [slot for slot in free_time_slots if (datetime.fromisoformat(slot['end']) - datetime.fromisoformat(slot['start'])).seconds >= duration_minutes * 60]

def schedule_meeting(teammate_calendars, duration_minutes, meeting_start, meeting_end, meeting_title):
    event = {
        'summary': meeting_title,
        'start': {
            'dateTime': meeting_start,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': meeting_end,
            'timeZone': 'UTC',
        },
        'attendees': [{'email': email} for email in teammate_calendars],
    }

    service.events().insert(
        calendarId='primary',
        body=event,
    ).execute()

# Set up teammates' calendar IDs
teammate_calendars = ['teammate1@example.com', 'teammate2@example.com']

# Set up meeting details
meeting_duration = 30  # in minutes
meeting_title = 'Stand-up Meeting'
current_time = datetime.utcnow()
meeting_start = current_time + timedelta(days=1, hours=10, minutes=0)
meeting_end = meeting_start + timedelta(minutes=meeting_duration)

# Find available time slots
available_time_slots = find_free_time_slots(teammate_calendars, meeting_duration, current_time.isoformat(), (current_time + timedelta(days=7)).isoformat())

if available_time_slots:
    # Schedule the first available time slot
    first_slot = available_time_slots[0]
    schedule_meeting(teammate_calendars, meeting_duration, first_slot['start'], first_slot['end'], meeting_title)
    print(f'Meeting scheduled: {first_slot["start"]} to {first_slot["end"]}')
else:
    print('No available time slots found.')
