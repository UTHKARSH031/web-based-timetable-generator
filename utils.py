# utils.py - Utility functions
from datetime import datetime, time
import json

def convert_time_to_minutes(time_str):
    """Convert time string to minutes since midnight"""
    time_obj = datetime.strptime(time_str, '%H:%M').time()
    return time_obj.hour * 60 + time_obj.minute

def convert_minutes_to_time(minutes):
    """Convert minutes since midnight to time string"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def validate_json_field(json_string):
    """Validate and parse JSON field"""
    if not json_string:
        return []
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return []

def get_day_number(day_name):
    """Convert day name to number"""
    days = {
        'monday': 1, 'tuesday': 2, 'wednesday': 3, 
        'thursday': 4, 'friday': 5, 'saturday': 6, 'sunday': 7
    }
    return days.get(day_name.lower(), 1)

def get_day_name(day_number):
    """Convert day number to name"""
    days = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 
            5: 'Friday', 6: 'Saturday', 7: 'Sunday'}
    return days.get(day_number, 'Monday')
