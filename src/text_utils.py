import textwrap
import re
import logging

log = logging.getLogger("main")

sep = "\n"

repl_nl1 = re.compile("([ \t]*\n){2,}")
repl_nl2 = re.compile("[ \t]*\n")

# Removes superflous whitespace from a string
def normalize_newlines_str(str_, num_newlines_to_add):
    new_str = repl_nl1.sub("|||", str_)
    new_str = repl_nl2.sub(" ", new_str)
    ret = new_str.replace("|||", "\n\n")
    return ret

# If width > 0, applies word wrapping to the text and returns and
# array of strings that conform to the width given. Regardless of
# whether word-wrapping is applied, newline characters are removed
# (each str in the array is a separate line), and paragraphs are
# separated by a single blank line.
def normalize_newlines_arr(str, num_newlines_to_add, width = 0):
    paragraphs = str.lstrip().splitlines()
    new_lines = []
    for p in paragraphs:
        if p.isspace() or not len(p):
            new_lines.append("")
        elif width > 0:
            wrapped = textwrap.wrap(p, width)
            new_lines += wrapped
        else:
            new_lines += [p.rstrip()]

    new_lines += ([""] * num_newlines_to_add)
    
    return new_lines

# Given an array of strings returned from normalize_newlines_arr,
# return a single string with double newline characters separating
# paragraphs, and no other newlines.
def str_from_arr(arr):
    ret = ""
    sep = "\n\n"
    for (i, ln) in enumerate(arr):
        line_len = len(ln)
        if line_len and i == 0:
            ret += ln
        elif line_len:
            ret += " " + ln
        else:
            ret += "\n\n"
    return ret
