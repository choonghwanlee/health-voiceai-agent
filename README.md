# assort-health-take-home
Assort Health Take Home – Voice AI Agent

Credits to Vocode documentation and telephony_app template code for helping me get started.

In our project, we use Python, FastAPI (to set up server endpoints), Ngrok (for local dev & testing), Render (for server deployment & hosting), Poetry (package management), Docker (container images), and the following open-source packages:
- Vocode
- Deepgram (for speech transcriber)
- ElevenLabs (for custom voice & synthesizer)
- Twilio (for telephony & SMS)
- OpenAI/ChatGPT (for our LLM)

TL;DR: In main.py, we set up an /inbound_call endpoint on our server that routes to a TelephonyServer. In agent_factory.py, we implement a custom RespondAgent that checks user input for each of our call requirements, and uses ChatGPT to generate the appropriate Agent response. We also implement an EventManager that triggers a SMS message using Twilio once the call ends. 

