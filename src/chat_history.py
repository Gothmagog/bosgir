import re
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    BaseMessage
)
import logging

log = logging.getLogger("main")
directive_re = re.compile("\n[ \t]*H:")

def clean_msg(message):
    if type(message) is AIMessage:
        match = directive_re.search(message.content)
        if match:
            return AIMessage(content=message.content[:match.start])
    return message
    
class BosgirChatHistory(BaseChatMessageHistory):
    def __init__(self, gamestate):
        self.messages = []
        self.gamestate = gamestate
        self.add_to_gamestate = True
        # self.add_user_message(background)
        
    def get_history(self):
        return [m.content for m in self.messages]

    def load_from_hist(self):
        self.add_to_gamestate = False
        for i, item in enumerate(self.gamestate.history):
            if i % 2 == 0:
                self.add_ai_message(item)
            else:
                self.add_user_message(item)
        self.add_to_gamestate = True
    
    def add_message(self, message):
        log.debug(message)
        cleaned_message = clean_msg(message)
        if not cleaned_message is message:
            log.warning("LLM tried to include human responses, cutting it off")
        self.messages.append(cleaned_message)
        if self.add_to_gamestate:
            self.gamestate.history.append(cleaned_message.content)

    def get_num_ai_messages(self):
        count = 0
        for m in self.messages:
            if type(m) is AIMessage:
                count += 1
        return count
    
    def clear(self):
        self.messages = []
