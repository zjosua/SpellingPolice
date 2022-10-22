"""
Create a new bdic file with a single word

You can create a bdic file from hunspell .dic and .aff with 
qwebengine_convert_dict tool that comes with qt

Useful Links
https://spylls.readthedocs.io/en/latest/hunspell.html#code-walkthrough
https://chromium.googlesource.com/chromium/deps/hunspell/+/61b053c9d102442e72af854d9f0a28ce60d539f5/google/bdict.h
https://chromium.googlesource.com/chromium/deps/hunspell/+/61b053c9d102442e72af854d9f0a28ce60d539f5/google/bdict_writer.cc
https://chromium.googlesource.com/chromium/src/+/refs/heads/main/chrome/tools/convert_dict/convert_dict.cc
"""
import hashlib

# TODO: remove TRY cmd as it's not needed when there's only one word
def aff_bytes() -> bytes:
    """
SET UTF-8
TRY esianrtolcdugmphbyfvkwzESIANRTOLCDUGMPHBYFVKWZ'
ICONV 1
ICONV ’ '
    """
    return b'\x32\x00\x00\x00\x38\x00\x00\x00\x39\x00\x00\x00\x3A\x00\x00\x00\x0A\x0A\x41\x46\x20\x30\x00\x00\x00\x00\x54\x52\x59\x20\x65\x73\x69\x61\x6E\x72\x74\x6F\x6C\x63\x64\x75\x67\x6D\x70\x68\x62\x79\x66\x76\x6B\x77\x7A\x45\x53\x49\x41\x4E\x52\x54\x4F\x4C\x43\x44\x55\x47\x4D\x50\x48\x42\x59\x46\x56\x4B\x57\x5A\x27\x00\x49\x43\x4F\x4E\x56\x20\x31\x00\x49\x43\x4F\x4E\x56\x20\xE2\x80\x99\x20\x27\x00\x00'

def aff_and_word(word: str) -> bytes:
    word_bytes = bytes(word, "utf-8")
    if len(word_bytes) < 2:
        raise Exception("Word must have at least 2 characters")
    # error occurs when using qwebengine_convert_dict on a word longer than 127
    if len(word_bytes) > 127: 
        raise Exception("Word can have up to 127 characters")

    output = aff_bytes()
    # dict words
    output += b'\xE2'
    if word[0] == 'a':
        placeholder_word = 'I'
    else:
        placeholder_word = 'a'

    # Calculate 'word body bytes' before 'word prefix bytes'
    word_body_bytes = b''
    word_body_bytes += word_bytes[1:]
    if placeholder_word < word[0]:
        word_body_bytes += b'\x00'
    else:
        word_body_bytes += b'\x00\x00\x00'

    if placeholder_word < word[0]:
        output += bytes(placeholder_word, "utf-8")
        output += b'\x00'
        output += word_bytes[:1]
        output += b'\x02\x00\x00'
    else:
        output += word_bytes[:1]
        output += b'\x00'
        output += bytes(placeholder_word, "utf-8")
        output += len(word_body_bytes).to_bytes(1, byteorder="big")
    output += b'\x40\x00'
    output += word_body_bytes

    return output


def create_bdic(word: str) -> bytes:
    """Create a .bdic file content containing a single word (and a placeholder word 'a' or 'I')"""
    dic_data = aff_and_word(word)
    result = hashlib.md5(dic_data)
    md5 = result.digest()
    
    # bdic header
    output = b'\x42\x44\x69\x63\x02\x00\x00\x00\x20\x00\x00\x00\x83\x00\x00\x00'
    output += md5
    output += dic_data
    return output