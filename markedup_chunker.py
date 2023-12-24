import re

partial_delim_re = re.compile("</?O?u?t?p?u?t?>?", re.DOTALL)
buffer_ = ""
begin_delim_found = False
end_delim_found = False
max_buff_size = 150
sent_pos = -1
lstrip_next_chunk = False
begin_delim = "<Output>"
end_delim = "</Output>"

def reset_chunker():
    global begin_delim_found, end_delim_found, buffer_, sent_pos, lstrip_next_chunk
    begin_delim_found = False
    end_delim_found = False
    buffer_ = ""
    sent_pos = -1
    lstrip_next_chunk = False

def markedup_chunker_decorator(func):
    def root_chunker(self_, chunk):
        global begin_delim_found, end_delim_found, sent_pos, lstrip_next_chunk
        ret = None
        if begin_delim_found and end_delim_found:
            return
        add_to_buffer(chunk)
        if partial_delim_re.search(buffer_):
            if not begin_delim_found:
                print("match")
                parts = partial_delim_re.split(buffer_)
                pos = buffer_.find(begin_delim)
                if pos != -1:
                    begin_delim_found = True
                    sent_pos = pos + len(begin_delim)
                    if len(parts[1]):
                        ret = invoke_func(func, self_, buffer_[sent_pos:].lstrip())
                        sent_pos += len(parts[1])
                    else:
                        print("here")
                        lstrip_next_chunk = True
            elif not end_delim_found:
                parts = split_from_back(buffer_)
                pos = buffer_.find(end_delim)
                len_prefix = len(parts[0])
                print(f"*** pos: {pos}, len_prefix: {len_prefix}")
                if len_prefix and pos != -1:
                    end_delim_found = True
                    if sent_pos < pos:
                        ret = invoke_func(func, self_, buffer_[sent_pos:pos])
                        sent_pos += (pos - sent_pos)
                elif pos != -1:
                    end_delim_found = True
                elif len(parts[1]):
                    ret = invoke_func(func, self_, buffer_[sent_pos:])
                    sent_pos += len(buffer_) - sent_pos
                elif len_prefix and sent_pos < len_prefix:
                    ret = invoke_func(func, self_, buffer_[sent_pos:len_prefix])
                    sent_pos += len_prefix - sent_pos
        elif begin_delim_found and not end_delim_found:
            print("*** Normal chunk")
            ret = invoke_func(func, self_, chunk)
            sent_pos += len(chunk)
        if ret != None:
            return ret

    return root_chunker

def invoke_func(func, self_, chunk):
    global lstrip_next_chunk
    if lstrip_next_chunk:
        print("stripping")
        chunk = chunk.lstrip()
        lstrip_next_chunk = False
    return func(self_, chunk)

def split_from_back(text):
    match_gaps = []
    matches = []
    start_pos = 0
    for match in partial_delim_re.finditer(text):
        match_gaps.append(text[start_pos:match.start()])
        matches.append(text[match.start():match.end()])
        start_pos = match.end()
    if start_pos < len(text):
        match_gaps.append(text[start_pos:])
    elif len(match_gaps):
        match_gaps.append("")
    if len(match_gaps) == 2:
        return match_gaps
    elif len(match_gaps) == 1:
        return [text]
    prefix = ""
    for i in range(len(matches) - 1):
        prefix += match_gaps[i]
        prefix += matches[i]
    prefix += match_gaps[len(matches) - 1]
    return (prefix, match_gaps[-1:][0])

def add_to_buffer(text):
    global buffer_, sent_pos
    len_new_text = len(text)
    buffer_len = len(buffer_)
    if buffer_len + len_new_text > max_buff_size:
        diff = buffer_len + len_new_text - max_buff_size
        buffer_ = buffer_[diff:]
        if sent_pos > -1:
            sent_pos -= diff
    buffer_ += text
    print(f"sent_pos: {sent_pos}, buffer: '{buffer_}'")
