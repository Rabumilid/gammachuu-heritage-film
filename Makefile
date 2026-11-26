PYTHON := .venv/bin/python

.PHONY: validate radio-cut keyframes shots music assemble film

validate:
	$(PYTHON) -c "from pipeline.utils import load_and_validate; load_and_validate(); print('storyboard.json VALID')"

radio-cut: validate
	$(PYTHON) pipeline/narration.py
	$(PYTHON) pipeline/assemble.py --radio-cut

keyframes: validate
	$(PYTHON) pipeline/keyframes.py

shots: validate
	$(PYTHON) pipeline/shots.py

music: validate
	$(PYTHON) pipeline/music.py

assemble: validate
	$(PYTHON) pipeline/assemble.py

film: validate
	$(PYTHON) pipeline/narration.py
	$(PYTHON) pipeline/keyframes.py
	$(PYTHON) pipeline/shots.py
	$(PYTHON) pipeline/music.py
	$(PYTHON) pipeline/assemble.py
