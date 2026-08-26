"""Validate the CHILD source embedded inside a probe.

ast.parse on the probe only checks the WRAPPER. The child is a string, so a
syntax error in it survives every local check and only surfaces after a
20-minute install on Kaggle. This extracts the textwrap.dedent(...) block and
parses it as real code.
"""
import ast, re, sys, textwrap

def extract_child(path):
    src = open(path).read()
    m = re.search(r"CHILD\s*=\s*textwrap\.dedent\(\s*('''|\"\"\")(.*?)\1\s*\)", src, re.S)
    if not m:
        return None
    return textwrap.dedent(m.group(2))

for path in sys.argv[1:]:
    child = extract_child(path)
    if child is None:
        print(f"  {path}: no CHILD block found"); continue
    try:
        ast.parse(child)
        print(f"  {path}: CHILD syntax OK ({len(child.splitlines())} lines)")
    except SyntaxError as e:
        print(f"  {path}: CHILD SyntaxError line {e.lineno}: {e.msg}")
        lines = child.splitlines()
        lo = max(0, e.lineno-4); hi = min(len(lines), e.lineno+3)
        for i in range(lo, hi):
            mark = ">>" if i == e.lineno-1 else "  "
            print(f"    {mark} {i+1:>4}| {lines[i][:100]}")
        sys.exit(1)
