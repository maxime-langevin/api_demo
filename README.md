## Setup environment

Environment management is done with Poetry.
To setup projet, install Poetry, then in the root folder run: `poetry install`

## CI

Testing and linting is performed automatically on all pushes to remote as a GitHub action.

### Autoformat and lint

Autoformating is done with black and isort, linting is done with ruff.
To autoformat the project, run: `poetry run sh ./autoformat.sh`

### Testing is done with pytest

Run `poetry run pytest tests`

### Running streamlit 

Run `poetry run streamlit run app.py`