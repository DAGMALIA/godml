# test_cli_encoding.py
"""
F1-20: `godml --help` crashed with UnicodeEncodeError when stdout was not
UTF-8 (Windows cp1252 consoles, redirected output, CI logs): the dataprep
help had an emoji and the texts have accents/dashes.
"""

import os
import re
import subprocess
import sys

import pytest

EMOJI = re.compile("[\U0001f000-\U0001faff☀-➿⬀-⯿️]")


def run_cli(args, cwd, encoding):
    code = (
        "import sys; sys.argv = ['godml'] + sys.argv[1:]; "
        "from godml.godml_cli import main; main()"
    )
    env = {**os.environ, "PYTHONIOENCODING": encoding, "PYTHONUTF8": "0"}
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        timeout=120,
    )


@pytest.mark.parametrize("args", [["--help"], ["dataprep", "--help"]])
@pytest.mark.parametrize("encoding", ["ascii", "cp1252"])
def test_help_works_with_non_utf8_output(tmp_path, args, encoding):
    result = run_cli(args, tmp_path, encoding)
    out = result.stdout.decode(encoding, errors="replace")
    err = result.stderr.decode(encoding, errors="replace")
    assert result.returncode == 0, err
    assert "Usage" in out
    assert "UnicodeEncodeError" not in err


def test_help_texts_have_no_emoji():
    from typer.main import get_command

    from godml.cli.app import app

    def walk(command):
        yield command
        for sub in getattr(command, "commands", {}).values():
            yield from walk(sub)

    texts = [
        text
        for command in walk(get_command(app))
        for text in (command.help, command.short_help)
        if text
    ]
    assert texts and not [t for t in texts if EMOJI.search(t)]
