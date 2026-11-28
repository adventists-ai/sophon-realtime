"""Check that mac/install.sh copies every local file the Mac programs need.

install.sh copies a fixed list of files into $SOPHON_HOME/app. This walks the imports of each installed
program (and of the local modules they pull in) and fails if a local module or data file is missing from
that list, so a clean install cannot break the way #26 did.  Run: python3 mac/check_install.py"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def copy_list():
    src = open(os.path.join(HERE, "install.sh"), encoding="utf-8").read()
    m = re.search(r'for f in ([^;]+); do[^\n]*\$H/app/', src)
    if not m:
        sys.exit("check_install: cannot find the copy list in mac/install.sh")
    return m.group(1).split()


def local_needs(path):
    """Local modules imported by a .py file, and local data files it names."""
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    need = {m + ".py" for m in mods if os.path.exists(os.path.join(HERE, m + ".py"))}
    for node in ast.walk(tree):        # data files next to the code, e.g. "system_prompt.json"
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.fullmatch(r"[\w.-]+\.(json|txt|onnx)", node.value):
            if os.path.exists(os.path.join(HERE, node.value)):
                need.add(node.value)
    return need


def main():
    listed = copy_list()
    bad = [f for f in listed if not os.path.exists(os.path.join(HERE, f))]
    seen, todo = set(), [f for f in listed if f.endswith(".py")]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        for n in local_needs(os.path.join(HERE, f)):
            if n.endswith(".py"):
                todo.append(n)
            seen.add(n)
    missing = sorted(n for n in seen if n not in listed)
    for f in bad:
        print(f"mac/install.sh copies {f}, but mac/{f} does not exist")
    for f in missing:
        print(f"mac/{f} is needed by an installed program but mac/install.sh does not copy it")
    if bad or missing:
        sys.exit(1)
    print(f"mac/install.sh copies everything the installed programs need ({len(listed)} files)")


if __name__ == "__main__":
    main()
