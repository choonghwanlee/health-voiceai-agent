import os
import typing
from typing import Optional
from twilio.rest import Client

import json 
# Import all required utils
from call_transcript_utils import add_transcript
from vocode.streaming.models.events import Event, EventType, Sender, ActionEvent 
from vocode.streaming.models.transcript import TranscriptEvent, TranscriptCompleteEvent
from vocode.streaming.utils import events_manager

import httpx
    
class EventsManager(events_manager.EventsManager):

    def __init__(self):
        super().__init__(subscriptions=[EventType.TRANSCRIPT_COMPLETE, EventType.TRANSCRIPT, EventType.PHONE_CALL_ENDED])
        
    async def handle_event(self, event: Event):
        if event.type == EventType.TRANSCRIPT_COMPLETE:
            transcript_complete_event = typing.cast(TranscriptCompleteEvent, event)
            add_transcript(
                transcript_complete_event.conversation_id,
                transcript_complete_event.transcript.to_string(),
            )
            # Prepare the data to be sent
            data = {
                "conversation_id": transcript_complete_event.conversation_id,
                "user_id": 1,  # demo user id
                "transcript": transcript_complete_event.transcript.to_string()
            }

            # # URL of the webhook endpoint you want to send the data to
            # webhook_url = os.getenv("TRANSCRIPT_CALLBACK_URL")

            # # Make the async HTTP POST request
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(webhook_url, json=data)

            #     # Handle the response as needed (e.g., check for success or failure)
            #     if response.status_code == 200:
            #         print("Transcript sent successfully.")
            #     else:
            #         print("Failed to send transcript.")
        elif event.type == EventType.PHONE_CALL_ENDED:
            ## TO-DO: trigger endpoint for sending text message
            account_sid = os.getenv['TWILIO_ACCOUNT_SID']
            auth_token = os.getenv['TWILIO_AUTH_TOKEN']
            client = Client(account_sid, auth_token)
            if os.path.exists('results.json'):
                with open('results.json') as json_file:
                    data = json.load(json_file)
                    body = 'Your appointment with {provider} has been scheduled for {time}'
                    message = client.messages.create(body=body.format(provider=data[4], time=data[5]),
                                                from_='+18663434218',
                                                to=data[7])
                    print(message.sid)
                    os.remove('results.json') ## remove after sending
            else:
                None

