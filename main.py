from fastapi import FastAPI
import os 
import logging

from vocode.streaming.models.telephony import TwilioConfig
from vocode.streaming.telephony.server.base import (
    TwilioInboundCallConfig,
    TelephonyServer,
)
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.models.transcriber import DeepgramTranscriberConfig, PunctuationEndpointingConfig
from vocode.streaming.telephony.config_manager.in_memory_config_manager import InMemoryConfigManager
from event_manager import EventsManager

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = FastAPI(docs_url=None)

CONFIG_MANAGER = InMemoryConfigManager()

TWILIO_CONFIG = TwilioConfig(
  account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
  auth_token=os.getenv("TWILIO_AUTH_TOKEN"), 
)

BASE_URL = os.getenv("BASE_URL")

# Get the instructions for the assistant
def get_assistant_instructions():
  with open('instructions.txt', 'r') as file:
    return file.read()

DEEPGRAM_CONFIG = DeepgramTranscriberConfig.from_telephone_input_device(endpointing_config=PunctuationEndpointingConfig())

AGENT_CONFIG = ChatGPTAgentConfig(
  initial_message=BaseMessage(text="Hello! This is Charlie, an AI assistant to help you book your next appointment"),
  prompt_preamble=get_assistant_instructions(),
  generate_responses=True,
)

SYNTH_CONFIG = ElevenLabsSynthesizerConfig.from_telephone_output_device(
  api_key=os.getenv("ELEVEN_LABS_API_KEY"),
  voice_id = os.getenv("VOICE_ID")
)

telephony_server = TelephonyServer(
    base_url=BASE_URL,
    config_manager=CONFIG_MANAGER,
    inbound_call_configs=[
        TwilioInboundCallConfig(
            url="/inbound_call",
            agent_config=AGENT_CONFIG,
            twilio_config=TWILIO_CONFIG, 
            synthesizer_config=SYNTH_CONFIG,   
            transcriber_config=DEEPGRAM_CONFIG        
        )
    ],
    events_manager=EventsManager(),
    agent_factory=None,
    logger=logger,
)

app.include_router(telephony_server.get_router())