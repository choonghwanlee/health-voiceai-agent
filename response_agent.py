import re
from typing import AsyncGenerator, Optional, Tuple

from langchain import OpenAI
from typing import Generator
import logging

import openai
from vocode import getenv

from vocode.streaming.agent.base_agent import BaseAgent, RespondAgent
from vocode.streaming.agent.utils import collate_response_async, openai_get_tokens
from vocode.streaming.models.agent import LLMAgentConfig


class CustomLLMAgent(RespondAgent[LLMAgentConfig]):
    SENTENCE_ENDINGS = [".", "!", "?"] ## classify punctuation as sentence endings

    DEFAULT_PROMPT_TEMPLATE = "{history}\nHuman: {human_input}\nAI:" ## generate AI response based on history + human input

    RESPONSE_CHECK_TEMPLATE = """Answer the question using the context below.
        Context: {human_input}
        Question: {response_check}
        Answer:
    """ ## custom Q&A prompt engineering template to check user input for required information 

    def __init__(
        self,
        agent_config: LLMAgentConfig,
        logger: Optional[logging.Logger] = None,
        sender="AI",
        recipient="Human",
        openai_api_key: Optional[str] = None,
    ):
        super().__init__(agent_config)
        self.prompt_template = (
            f"{agent_config.prompt_preamble}\n\n{self.DEFAULT_PROMPT_TEMPLATE}"
        ) ## add prompt preamble 
        self.check_template = (
            f"{self.RESPONSE_CHECK_TEMPLATE}"
        ) ## initialize response check template
        self.initial_bot_message = (
            agent_config.initial_message.text if agent_config.initial_message else None
        ) ## init initial message 
        self.logger = logger or logging.getLogger(__name__)
        self.sender = sender
        self.recipient = recipient
        self.memory = (
            [f"AI: {agent_config.initial_message.text}"]
            if agent_config.initial_message
            else []
        ) ## create memory
        ## create a dictionary object to track information already gathered, init to empty dict
        self.fulfilled = {}
        self.custom_prompts =  self.load_file('custom_prompts.txt') ## list of custom prompts for LLMAgent
        self.response_checks = self.load_file('response_checks.txt') ## list of response checks for each requirement
        self.num_fulfilled = 0 ## keep count of number of informations items received. if == len(dict), trigger end call! 
        openai_api_key = openai_api_key or getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment or passed in")
        self.llm = OpenAI(  # type: ignore
            model_name=self.agent_config.model_name, ## determine correct model name, use default for now
            temperature=self.agent_config.temperature, 
            max_tokens=self.agent_config.max_tokens,
            openai_api_key=openai_api_key,
        )
        self.stop_tokens = [f"{recipient}:"] 
        self.first_response = (
            self.llm(
                self.prompt_template.format(
                    history="", human_input=agent_config.expected_first_prompt
                ),
                stop=self.stop_tokens,
            ).strip()
            if agent_config.expected_first_prompt
            else None
        )
        self.is_first_response = True

    def create_prompt(self, human_input):
        history = "\n".join(self.memory[-5:]) ## use last 5 entries to memory
        return self.prompt_template.format(history=history, human_input=human_input)

    def create_check(self, human_input):
        ## create response check to feed into LLM
        return self.check_template.format(human_input=human_input, response_check = self.response_checks[self.num_fulfilled])

    def get_memory_entry(self, human_input, response):
        return f"{self.recipient}: {human_input}\n{self.sender}: {response}"

    async def respond(
        self,
        human_input,
        conversation_id: str,
        is_interrupt: bool = False,
    ) -> Tuple[str, bool]:
        info_fulfilled = self.process_human_input(human_input) ## check human input for requested information 
        if is_interrupt and self.agent_config.cut_off_response:
            cut_off_response = self.get_cut_off_response()
            self.memory.append(self.get_memory_entry(human_input, cut_off_response))
            return cut_off_response, False
        self.logger.debug("LLM responding to human input")
        if self.is_first_response and self.first_response: ## won't ever hit, we don't init expected_first_prompt
            self.logger.debug("First response is cached")
            self.is_first_response = False 
            response = self.first_response
        elif info_fulfilled: ## requested information is received, we can ask the next prompt  
            response = self.custom_prompts[self.num_fulfilled]
        else:
            response = (
                (
                    await self.llm.agenerate(
                        [self.create_prompt(human_input)], stop=self.stop_tokens
                    ) ## generate based on history and human input
                )
                .generations[0][0]
                .text
            )
            response = response.replace(f"{self.sender}:", "") ## replace stop token with empty string 
        self.memory.append(self.get_memory_entry(human_input, response)) ## append to memory
        self.logger.debug(f"LLM response: {response}") ## generated response
        return response, False

    async def _stream_sentences(self, prompt):
        stream = await openai.Completion.acreate(
            prompt=prompt,
            max_tokens=self.agent_config.max_tokens,
            temperature=self.agent_config.temperature,
            model=self.agent_config.model_name,
            stop=self.stop_tokens,
            stream=True,
        )
        async for sentence in collate_response_async(
            openai_get_tokens(gen=stream),
        ):
            yield sentence

    async def _agen_from_list(self, l):
        for item in l:
            yield item

    async def generate_response(
        self,
        human_input,
        conversation_id: str,
        is_interrupt: bool = False,
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        self.logger.debug("LLM generating response to human input")
        if is_interrupt and self.agent_config.cut_off_response:
            cut_off_response = self.get_cut_off_response()
            self.memory.append(self.get_memory_entry(human_input, cut_off_response))
            yield cut_off_response, False
            return
        self.memory.append(self.get_memory_entry(human_input, ""))
        if self.is_first_response and self.first_response:
            self.logger.debug("First response is cached")
            self.is_first_response = False
            sentences = self._agen_from_list([self.first_response])
        else:
            self.logger.debug("Creating LLM prompt")
            prompt = self.create_prompt(human_input)
            self.logger.debug("Streaming LLM response")
            sentences = self._stream_sentences(prompt)
        response_buffer = ""
        async for sentence in sentences:
            sentence = sentence.replace(f"{self.sender}:", "")
            sentence = re.sub(r"^\s+(.*)", r" \1", sentence)
            response_buffer += sentence
            self.memory[-1] = self.get_memory_entry(human_input, response_buffer)
            yield sentence, True

    def load_file(self, filename):
        ## init custom prompts from txt file
        with open(filename) as file:
            file_list = [line.rstrip() for line in file]
        return file_list
    
    async def process_human_input(self, human_input) -> bool:
        ## process human input to determine whether information need was fulfilled
        response = (
            (
                await self.llm.agenerate(
                    [self.create_check(human_input)], stop=self.stop_tokens
                ) ## generate based on history and human input
            )
            .generations[0][0]
            .text
        )
        if "None" in response: ## not all information is collected
            return False
        self.fulfilled[self.num_fulfilled] = response
        self.num_fulfilled += 1
        return True 

    def update_last_bot_message_on_cut_off(self, message: str):
        last_message = self.memory[-1]
        new_last_message = (
            last_message.split("\n", 1)[0] + f"\n{self.sender}: {message}"
        )
        self.memory[-1] = new_last_message