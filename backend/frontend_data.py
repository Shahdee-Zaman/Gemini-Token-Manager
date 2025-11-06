from flask import Flask, jsonify
from flask_cors import CORS
import redis
import json

# Flask app exposing simple read endpoints for frontend charts and stat cards.
app = Flask(__name__)
CORS(app)

# Connect to local Redis (used by RTCLimit). decode_responses=True returns string values.
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Endpoint: /api/token-usage — returns today's token_history as JSON array for charting.
@app.route('/api/token-usage', methods=['GET'])
def get_token_usage():
    # Attempt to read token_history. If present, parse JSON and return list; else return [].
    try:
        data = r.get('token_history')
        
        if data:
            data_list = json.loads(data)
            return jsonify(data_list)
        else:
            return jsonify([])
    # Log and return 500 on Redis/read errors.       
    except Exception as e:
        print(f"Error fetching from Redis: {e}")
        return jsonify({'error': str(e)}), 500

# Endpoint: /api/graph-stats - returns daily token stats for graph sidebar.
@app.route('/api/graph-stats', methods=['GET'])
def get_graph_stats():
    """Get stats for the graph sidebar"""
    try:
        input_tokens = r.get('input_tokens')
        output_tokens = r.get('output_tokens')
        yesterday_total = r.get('yesterday_total')
        today_total = r.get('token_usage')
        
        # Calculate peak hour from today's history
        history = r.get('token_history')
        peak_hour = "N/A"
        if history:
            data_list = json.loads(history)
            if data_list:
                max_point = max(data_list, key=lambda x: x['tokens'])
                hour = int(max_point['hour'])
                minute = int((max_point['hour'] - hour) * 60)
                peak_hour = f"{hour:02d}:{minute:02d}"
        
        # Calculate daily change
        daily_change = "0%"
        if yesterday_total and today_total:
            yesterday = int(yesterday_total)
            today = int(today_total)
            if yesterday > 0:
                change = ((today - yesterday) / yesterday) * 100
                daily_change = f"{change:+.1f}%"
        
        return jsonify({
            'input_tokens': int(input_tokens) if input_tokens else 0,
            'output_tokens': int(output_tokens) if output_tokens else 0,
            'peak_hours': peak_hour,
            'daily_change': daily_change
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

# Endpoint: /api/stats — returns current stats for UI stat cards.
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get current stats for the stat cards"""
    try:
        # Get all token stats
        daily_total = r.get('token_usage')
        monthly_total = r.get('monthly_tokens')
        peak_day = r.get('peak_day_tokens')
        lifetime_total = r.get('lifetime_tokens')
        
        return jsonify({
            'daily_total': int(daily_total) if daily_total else 0,
            'monthly_total': int(monthly_total) if monthly_total else 0,
            'peak_day': int(peak_day) if peak_day else 0,
            'lifetime_total': int(lifetime_total) if lifetime_total else 0
        })
        
    # Log and return 500 on any errors.  
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
  

# Dev server run: debug mode on port 5000 — for local testing only, not production.
if __name__ == '__main__':
    app.run(debug=True, port=5000)