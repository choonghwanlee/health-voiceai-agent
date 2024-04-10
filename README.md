# assort-health-take-home
Assort Health Take Home – Voice AI Agent

Credits to Vocode documentation and telephony_app template code for helping me get started.

In our project, we use Python, FastAPI (to set up server endpoints), Ngrok (for local dev & testing), Render (for server deployment & hosting), Poetry (package management), Docker (container images), and the following open-source packages:
- Vocode
- Deepgram (for speech transcriber)
- ElevenLabs (for custom voice & synthesizer)
- Twilio (for telephony & SMS)
- OpenAI/ChatGPT (for our LLM)

TL;DR: In main.py, we set up an /inbound_call endpoint on our server that routes to a TelephonyServer. In agent_factory.py, we implement a custom LLMRespondAgent that checks user input for each of our call requirements (defined in response_checks.txt), and uses ChatGPT to generate the appropriate Agent response. We also implement an EventManager that triggers a SMS message using Twilio once the call ends (not actually implemented due to regulation issues, but I include the boilerplate code to highlight how it'd function).

Long Explanation:

When seeing this take-home assignment, my first worry was how LLMs can hallucinate and begin veering off track from our conversation. It's also difficult to understand whether all information has been received or not. Given the linear and structured format of the information we need (it's slightly less conversational and more Q&A style), I use a ChatGPT-3.5-Instruct model to determine whether a target question (defined in `response_checks.txt`) has been answered by the human input. If the question has been answered, we store the relevant information in a dictionary dictionary `fulfilled` that keeps track of all key information during the call. This is useful for three reasons. 

1. it allows our customers (our client companies) to obtain structured data about patients.
2. it is easier to know when all information was collected.
3. it is easier to send automated SMS and emails using the provider name, date/time of appointment, and patient phone number that was collected.

If the question is answered, we move on to the next question in `response_checks.txt`, and generate a manual response using the corresponding question in the `custom_prompts.txt` file. This allows us to have some consistency across our customer agent calls and for calls to flow in the right direction. If the question is not answered by a human input, our LLM Agent uses information from the memory chain to generate responses that guide the caller to eventually answer the target question – allowing us to have natural conversation. 

When all key pieces of information are stored, we save the responses to a temporary json file that we use to send a SMS text when the call ends. Theoretically, we'd want to automatically trigger a call end action, but after digging across the source code for Vocode I'm pretty confident that's not available for inbound calls ://

Bulk of my work can be found in the `response_agent.py` file. 

