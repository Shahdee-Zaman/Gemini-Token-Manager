import redis
import json
from datetime import datetime, timezone
from typing import Optional
from frontend_data import get_token_usage, get_stats

"""
    Usage:
    1. Initialize with Redis connection parameters and per-day token limit (TPD).
    2. Call generate(tokens) before making a model call to check if there are enough tokens left.
        - If True is returned, proceed with the model call.
        - If False is returned, do not make the call (limit exceeded).
    3. After receiving the model response, call response_count(tokens) to add the output tokens used.

"""
# ----------------- Start Of Class Creation -----------------

"""
    RTCLimit: manages token counting, daily reset, history and a 30-day archive in Redis
    RTCLimit stop further calls from being made when the tier limit is reached, allowing anyone to avoid incurring extra charges.
    Automatically check for Daily Reset using UTC timezone before every call.

    Redis keys used: date, token_usage, input_tokens, output_tokens, token_history, token_archive, yesterday_total
"""

class RTCLimit:
    """Initialize Redis connection and set the per-day token limit (TPD). 
    Limit is provider limit; subtract 50k buffer."""
    def __init__(self, host: str, port: int, limit: int, db : int=0):
        # Redis setup
        # Redis client (decode_responses True -> returns strings).
        self.database = redis.Redis(host, port, db, decode_responses=True)
        # self.Gemini_TPD_limit: effective soft limit used to block calls when exceeded.
        self.Gemini_TPD_limit = limit - 50000

    # Check for Daily TPD reset
    # Called before token operations to ensure daily counters reset at UTC day boundary.
    def check_daily_reset(self) -> None:
        # current_date: get current date in two-digit year:month:day ('%y:%m:%d') used as the daily key.
        current_date = datetime.now(timezone.utc).strftime('%y:%m:%d')
        current_month = datetime.now(timezone.utc).strftime('%y:%m')
        # stored_date: last saved date in Redis (if different -> new UTC day).
        stored_date = self.database.get('date')
        stored_month = self.database.get('current_month')
        # Stored date to compare with current_date
        if stored_date != current_date:
            today_total = self.database.get('token_usage')
            if today_total:
                today_total_int = int(today_total)
                
                # Update lifetime total
                lifetime = self.database.get('lifetime_tokens')
                if lifetime:
                    self.database.incrby('lifetime_tokens', today_total_int)
                else:
                    self.database.set('lifetime_tokens', today_total_int)
                
                # Update monthly total
                if stored_month == current_month:
                    self.database.incrby('monthly_tokens', today_total_int)
                else:
                    # New month, reset monthly counter
                    self.database.set('monthly_tokens', today_total_int)
                    self.database.set('current_month', current_month)
                
                # Check if today beat the record
                peak_day = self.database.get('peak_day_tokens')
                if not peak_day or today_total_int > int(peak_day):
                    self.database.set('peak_day_tokens', today_total_int)
            # Archive previous day's history (if any) before resetting counters.
            self._archive_previous_day(stored_date)
            # If there were tokens yesterday, save yesterday_total.
            yesterday_tokens =  self.database.get('token_usage')
            if yesterday_tokens:
                self.database.set('yesterday_total', yesterday_tokens)

            # Reset date and zero token_usage, input_tokens, output_tokens and clear token_history.
            self.database.set('date', current_date)
            self.database.set('token_usage', 0)
            self.database.set('input_tokens', 0)
            self.database.set('output_tokens', 0)
            self.database.delete('token_history')

    # Private: build an archive entry from yesterday's history and append to token_archive (keeps 30 days).
    def _archive_previous_day(self, previous_date) -> None:
        """Save previous day's data before it gets deleted"""
        try:
            # Guard: skip archive if no previous_date or no token_history stored.
            if not previous_date:
                return
            
            # Get the data from yesterday
            history_data = self.database.get('token_history')
            if not history_data:
                return
            
            # Get total tokens used yesterday
            total_tokens = self.database.get('token_usage') or 0
            
            """
                archive_entry fields:
                - date: previous_date (string)
                - total_tokens: int total_tokens for that day
                - hourly_data: parsed JSON list of hourly points
                - archived_at: UTC timestamp when archived
                """
            archive_entry = {
                'date': previous_date,
                'total_tokens': int(total_tokens),
                'hourly_data': json.loads(history_data),
                'archived_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Load existing token_archive (JSON list), append new entry, trim to last 30 entries, write back.
            archive = self.database.get('token_archive')
            if archive:
                archive_list = json.loads(archive)
            else:
                archive_list = []
            
            # Add yesterday's data
            archive_list.append(archive_entry)
            
            # Keeps track of recent 30 days of token history
            if len(archive_list) > 30:
                archive_list = archive_list[-30:]
            
            # Save archive
            self.database.set('token_archive', json.dumps(archive_list))
            
        except Exception as e:
            print(f"Error archiving data: {e}")


    # Private: append a sampled datapoint (hour, tokens, timestamp) to today's token_history.
    def _add_to_history(self, tokens) -> None:
        try:
            now = datetime.now(timezone.utc)
            # hour_decimal: fractional hour used for plotting (hour + minutes/60).
            hour_decimal = now.hour + (now.minute / 60)
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            
            existing_data = self.database.get('token_history')
            data_list = json.loads(existing_data) if existing_data else []
            
            current_tokens = self.database.get('token_usage')
            current_tokens = int(current_tokens) if current_tokens else 0
            
            # new_point stores the current token usage snapshot (uses token_usage key as current total).
            new_point = {
                'hour': round(hour_decimal, 2),
                'tokens': int(current_tokens),
                'timestamp': timestamp
            }
            
            data_list.append(new_point)
            
            # Keep only the latest 100 points to limit size
            if len(data_list) > 100:
                data_list = data_list[-100:]
            
            self.database.set('token_history', json.dumps(data_list))
            
        except Exception as e:
            print(f"Error adding to history: {e}")



    # Check if the prompt is within the Daily Token limit
    # Returns True if within limit and increments input_tokens and token_usage
    def has_tokens(self, tokens) -> bool:
        current_usage = self.database.get('token_usage')
        current_usage = int(current_usage) if current_usage else 0
        # estimated_total = current_usage + requested tokens
        estimated_total = current_usage + tokens
        # If within limit -> increment token_usage and input_tokens, add to history
        if estimated_total <= self.Gemini_TPD_limit:
            self.database.incrby('token_usage', tokens)
            self.database.incrby('input_tokens', tokens)
            self._add_to_history(tokens)
            return True
        return False

# ----------------- End Of Class Creation -----------------

    # ----------------- Helper Functions -----------------

    # Helper: returns current day's total token usage (calls check_daily_reset to ensure accuracy).
    def tokens_used(self) -> int:
        self.check_daily_reset()
        token_usage = self.database.get('token_usage')
        # Return 0 if no token was called since Redis initialization
        return int(token_usage) if token_usage else 0

    # get_history: returns parsed token_history (today)
    def get_history(self) -> list:
        # Returns today's historical token usage data
        data = self.database.get('token_history')
        return json.loads(data) if data else []
    
    # get_archive: returns parsed token_archive (past up to 30 days)
    def get_archive(self) -> list:
        # Returns archived data from previous days
        archive = self.database.get('token_archive')
        return json.loads(archive) if archive else []

    # get_history_count: quick length of today's history list (0 if none)
    def get_history_count(self) -> int:
        data = self.database.get('token_history')
        return len(json.loads(data)) if data else 0


    # ----------------- End of Helper Functions -----------------

    # ----------------- Main Function -----------------

    ## The required function that needs to be called to properly run the Class

    """ 
    Generate: main function to be called before making a model call.
    1. Checks for daily reset
    2. Checks if there are enough tokens left for the requested call
    3. Returns True if call can proceed, False if limit exceeded
    """

    def generate(self, tokens) -> bool:
        self.check_daily_reset()
        if self.has_tokens(tokens):
            return True
        return False

    # response_count: call to add output tokens (response size) to totals and history.
    def response_count(self, token) -> None:
        self.database.incrby('token_usage', token)
        self.database.incrby('output_tokens', token)
        self._add_to_history(token)

