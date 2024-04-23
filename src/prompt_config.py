import logging
from pathlib import Path

log = logging.getLogger("main")
cur_dir = Path(__file__).parent

class PromptsConfig:
    def __init__(self, config_file):
        self.file = cur_dir / "../data" / config_file
        self.full_text = ""
        self.prompts_dict = {}

    def fetch(self):
        text = self.file.read_text()
        if text != self.full_text:
            self.full_text = text
            self.parse_full_text()

    def parse_full_text(self):
        sections = None
        cur_section_id = None
        cur_section_content = ""

        self.prompts_dict = {}
        log.info("Parsing prompts config content into separate prompt templates")
        for i, l in enumerate(self.full_text.splitlines(keepends=True)):
            if i == 0:
                sections = l.strip().split(",")
                sections[-1] = sections[-1].strip()
            elif not l.isspace() and len(l) > 0 and ((not cur_section_id) or l.strip() in sections):
                if len(cur_section_content) > 0:
                    self.prompts_dict[cur_section_id] = cur_section_content
                cur_section_id = l.strip()
                cur_section_content = ""
            elif cur_section_id:
                cur_section_content += l
        self.prompts_dict[sections[-1]] = cur_section_content
        
    def get(self, prompt_id, fetch=False):
        if fetch:
            self.fetch()
        return self.prompts_dict[prompt_id]
