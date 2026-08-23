#!/usr/bin/env python3
"""Render final-report.md into index.html using the GitHub Pages minimal theme.

C++ blocks are highlighted with Pygments; the generated classes match the
.highlight rules in stylesheets/pygment_trac.css.

    python3 build.py
"""

import html
import os
import re
import sys

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import CppLexer

HERE = os.path.dirname(os.path.abspath(__file__))
FORMATTER = HtmlFormatter(cssclass="highlight", nowrap=False)

HEAD = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8" />
        <meta http-equiv="X-UA-Compatible" content="chrome=1" />
        <title>{title} | GSoC @ LLVM 2026</title>
        <link rel="icon" href="./favicon.ico" />
        <link rel="stylesheet" href="stylesheets/styles.css" />
        <link rel="stylesheet" href="stylesheets/pygment_trac.css" />
        <meta name="viewport" content="width=device-width" />
    </head>
    <body>
        <div class="wrapper">
            <header>
                <a href="?">
                    <img src="./img/LLVMWyvernBig.png" />
                </a>
            </header>
            <section>
"""

FOOT = """            </section>
            <footer>
                <p>
                    <small>Hosted on GitHub Pages &mdash; Theme by
                        <a href="https://github.com/orderedlist" target="_blank">orderedlist</a></small>
                </p>
            </footer>
        </div>
        <script src="javascripts/scale.fix.js"></script>
    </body>
</html>
"""


def inline(text):
    """Convert inline Markdown to HTML on a single block of text."""
    spans = []

    def stash(markup):
        spans.append(markup)
        return "\x00%d\x00" % (len(spans) - 1)

    def code(m):
        return stash("<code>%s</code>" % html.escape(m.group(1)))

    text = re.sub(r"`([^`]+)`", code, text)
    text = html.escape(text, quote=False)

    def link(m):
        label, url = m.group(1), html.escape(m.group(2), quote=True)
        return stash('<a href="%s" target="_blank">%s</a>' % (url, label))

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)

    def autolink(m):
        url = m.group(0)
        return stash('<a href="%s" target="_blank">%s</a>' % (url, url))

    text = re.sub(r"https?://[^\s<>\"]+[^\s<>\".,;:)]", autolink, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)
    return text


def render_body(blocks):
    out = []
    for kind, payload in blocks:
        if kind == "h2":
            out.append("                <h2>%s</h2>" % inline(payload))
        elif kind == "h3":
            out.append("                <h3>%s</h3>" % inline(payload))
        elif kind == "p":
            out.append("                <p>%s</p>" % inline(payload))
        elif kind == "ul":
            out.append("                <ul>")
            for item in payload:
                out.append("                    <li>%s</li>" % inline(item))
            out.append("                </ul>")
        elif kind == "cpp":
            out.append(highlight(payload, CppLexer(), FORMATTER).rstrip())
        elif kind == "text":
            out.append("<pre><code>%s</code></pre>" % html.escape(payload, quote=False))
        out.append("")
    return "\n".join(out)


def parse(md):
    lines = md.split("\n")
    blocks, i = [], 0
    para, bullets = [], []

    def flush():
        if para:
            blocks.append(("p", " ".join(para)))
            para.clear()
        if bullets:
            blocks.append(("ul", list(bullets)))
            bullets.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip() or "text"
            i += 1
            body = []
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            flush()
            blocks.append(("cpp" if lang == "cpp" else "text", "\n".join(body)))
        elif line.startswith("### "):
            flush()
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("## "):
            flush()
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("- "):
            if para:
                blocks.append(("p", " ".join(para)))
                para.clear()
            bullets.append(line[2:].strip())
        elif not line.strip():
            flush()
        else:
            if bullets:
                bullets[-1] += " " + line.strip()
            else:
                para.append(line.strip())
        i += 1
    flush()
    return blocks


def main():
    md = open(os.path.join(HERE, "final-report.md"), encoding="utf-8").read()
    lines = md.split("\n")

    title = lines[0].lstrip("# ").strip()
    start = next(n for n, l in enumerate(lines) if l.startswith("## "))
    # group the front matter into blocks separated by blank lines, so that
    # hard wrapped lines are rejoined before they are rendered
    front, block = [], []
    for l in lines[1:start]:
        if l.strip():
            block.append(l.strip())
        elif block:
            front.append(" ".join(block))
            block = []
    if block:
        front.append(" ".join(block))
    program, byline, links = front[0], front[1], front[2]

    head = HEAD.format(title=html.escape(title))
    intro = "\n".join([
        "                <h1>%s</h1>" % html.escape(title),
        "                <h3>%s</h3>" % inline(program.strip("*")),
        "                <p>",
        "                    <span class=\"nameContainer\"><strong>Benedek Kaibás</strong></span>",
        "                    %s" % html.escape(byline.split(",", 1)[1].strip()),
        "                    <br />",
        "                    %s" % inline(links),
        "                </p>",
        "",
    ])
    body = render_body(parse("\n".join(lines[start:])))
    out = head + intro + body + FOOT

    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(out)
    print("index.html: %d lines" % out.count("\n"))


if __name__ == "__main__":
    sys.exit(main())
