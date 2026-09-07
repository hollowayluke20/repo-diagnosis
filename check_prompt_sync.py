"""Fail if the two copies of the diagnosis prompt have drifted apart.

prompts/diagnosis-v3.txt is what the runner actually sends. The .md is the same
content with formatting, kept for reading. Nothing stopped them disagreeing,
which means the prompt could be edited in the copy nobody runs and every result
afterwards would be attributed to the wrong instructions.

Compares meaning, not formatting: markdown emphasis, list markers, dashes and
whitespace are normalised away first.

Exit code 1 on drift, so it can gate a commit.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
TXT = ROOT / "prompts" / "diagnosis-v3.txt"
MD = ROOT / "prompts" / "diagnosis-v3-source.md"


def normalise(s):
    # the .md carries a header block above a --- rule; the prompt is below it
    if "\n---\n" in s:
        s = s.split("\n---\n", 1)[1]
    s = s.replace("**", "").replace("`", "")
    s = re.sub(r"\*(\S[^*]*?\S|\S)\*", r"\1", s)   # *italics* -> italics
    s = re.sub(r"^#+\s*", "", s, flags=re.M)      # headings
    s = re.sub(r"^\s*[-*]\s+", "", s, flags=re.M)  # bullets
    s = re.sub(r"^\s*\d+\.\s+", "", s, flags=re.M)  # numbered items
    s = s.replace("—", "-").replace("–", "-")  # em/en dash
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    if not TXT.exists():
        sys.exit(f"missing: {TXT.name} - there is no prompt to run")
    if not MD.exists():
        # the intended state: one file, so nothing can disagree with it
        others = [p for p in (ROOT / "prompts").glob("*")
                  if p.name != TXT.name and p.suffix in (".md", ".txt")]
        if others:
            print("A second copy of the prompt has appeared: "
                  + ", ".join(p.name for p in others))
            print("Two copies drift. Delete it, or teach this check to compare it.")
            sys.exit(1)
        print("prompt has a single source of truth")
        return
    a, b = normalise(TXT.read_text(encoding="utf-8")), \
           normalise(MD.read_text(encoding="utf-8"))
    if a == b:
        print("prompt copies agree")
        return
    print("PROMPT DRIFT: the two copies say different things.\n")
    aw, bw = a.split(), b.split()
    for i in range(min(len(aw), len(bw))):
        if aw[i] != bw[i]:
            lo = max(0, i - 8)
            print("  .txt (what actually runs): ..." + " ".join(aw[lo:i + 8]))
            print("  .md  (what you read)     : ..." + " ".join(bw[lo:i + 8]))
            break
    else:
        longer = ".txt" if len(aw) > len(bw) else ".md"
        print(f"  same up to the end; {longer} has "
              f"{abs(len(aw)-len(bw))} extra words")
    sys.exit(1)


if __name__ == "__main__":
    main()
