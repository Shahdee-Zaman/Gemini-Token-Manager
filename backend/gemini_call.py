import os
import google.generativeai as genai
import redis
from rtc import RTCLimit

""""
    This is purely an example class to show rtc.py functions.
"""

api_key = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=api_key)

# Multiple dbs used rather than ports to lower resource usage
# RTCLimit automatically sets aside 50,000 tokens for last output before reaching the limit.
flash = RTCLimit(host='localhost', port=6379, db=0, limit=1000000)
lite = RTCLimit(host='localhost', port=6379, db=1, limit=1000000)

# Multiple models can be created as long as the token count is not shared between the models.
first_model = genai.GenerativeModel('gemini-2.0-flash')
second_model = genai.GenerativeModel('gemini-2.0-flash-lite')


prompt = input("Ask any question.\n")

# Gemini counts the token from input and returns an integer
# total_tokens is required to receive an integer otherwise it will return an object 'CountTokensResponse'.
input_token = first_model.count_tokens(prompt).total_tokens

# Proceed only if there is enough tokens left
if flash.generate(input_token):
    response = first_model.generate_content(prompt)
    print(response.text)
    # Increment the response to Redis database. Gemini automatically does token count
    flash.response_count(response.usage_metadata.candidates_token_count)

# Different model called if the first model has reached the token limit
elif lite.generate(input_token):
    response = second_model.generate_content(prompt)
    print(response.text)
    # Response incremented for proper tracking
    lite.response_count(response.usage_metadata.candidates_token_count)



