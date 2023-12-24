import textwrap
import re

sep = "\n"

repl_nl1 = re.compile("([ \t]*\n){2,}")
repl_nl2 = re.compile("[ \t]*\n")

def normalize_newlines_str(str_, num_newlines_to_add):
    new_str = repl_nl1.sub("|||", str_)
    #print(f"111\n{new_str}\n111\n")
    new_str = repl_nl2.sub(" ", new_str)
    #print(f"222\n{new_str}\n222\n")
    ret = new_str.replace("|||", "\n\n")
    #print(f"333\n{new_str}\n333\n")
    return ret

def normalize_newlines_arr(str, num_newlines_to_add, width):
    paragraphs = str.splitlines()
    new_lines = []
    for p in paragraphs:
        if p.isspace() or not len(p):
            new_lines.append("")
        else:
            wrapped = textwrap.wrap(p, width)
            new_lines += wrapped

    new_lines += ([""] * num_newlines_to_add)
    
    return new_lines
