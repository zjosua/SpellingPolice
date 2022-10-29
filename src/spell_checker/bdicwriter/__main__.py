from typing import Optional
from . import create_bdic


if __name__ == "__main__":
    import sys
    from pathlib import Path

    input_dic = Path(sys.argv[1])
    input_aff = input_dic.parent / (input_dic.stem + ".aff")
    output_bdic = Path(sys.argv[2])
    dic_file = input_dic.read_text()
    lines = dic_file.split("\n")[1:]  # first line contains word count
    words = list(filter(lambda i: i, map(lambda line: line.strip(), lines)))

    aff_string: Optional[str] = None
    if input_aff.exists():
        print("Using input aff")
        aff_string = input_aff.read_text()
    else:
        print("Using default aff")

    b = create_bdic(words, aff=aff_string)
    output_bdic.write_bytes(b)
