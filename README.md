# pynvdrs

Shared utilities extracted from NVDRS-style projects. Install when published:

```
pip install pynvdrs
```

Optional extras:

```bash
pip install "pynvdrs[gpt]"
pip install "pynvdrs[text]"
pip install "pynvdrs[iaa]"
pip install "pynvdrs[gpt,text,iaa]"
```

Or during development:

```
pip install -e ".[gpt,text,iaa]"
```

## Quick Start

```python
from pathlib import Path

from pynvdrs.paths import data_dir, project_root
from pynvdrs.text import clean_text, load_symspell
from pynvdrs.umgpt import GPTClient, parse_response
from pynvdrs.annotation import disagreements, IAA, model_performance
from pynvdrs.demographics import bin_age, load_demographics

root = project_root(Path.cwd())
data = data_dir(project_root=root)
print(root, data)
```

```python
from pynvdrs.text import clean_text

print(clean_text("pt. with t.v. and helo"))
```

```python
from types import SimpleNamespace

from pynvdrs.umgpt import GPTClient, parse_response

class MockClient:
	def __init__(self):
		self.chat = SimpleNamespace(completions=self)

	def create(self, **kwargs):
		self.last_call = kwargs
		return SimpleNamespace(
			choices=[SimpleNamespace(message=SimpleNamespace(content='{"flag": true}'))]
		)


client = GPTClient(MockClient(), model="gpt-4o-mini")
print(client.generate("system", "prompt", "narrative"))
print(parse_response('{"flag": true}', ["flag"]))
```

```python
import pandas as pd

from pynvdrs.annotation import disagreements, IAA, model_performance

index = pd.MultiIndex.from_tuples(
	[(1, "A"), (1, "B")], names=["PersonID", "Annotator"]
)
annotations = pd.DataFrame({"CodeA": [1, 0]}, index=index)
print(disagreements(annotations))
print(IAA(annotations))
```

```python
from pynvdrs.demographics import bin_age

print(bin_age(27))
```

## Migration from `pr-ifip`

Replace local imports with `pynvdrs` imports:

```python
from pynvdrs.paths import project_root, data_dir
from pynvdrs.text import clean_text, load_symspell
from pynvdrs.annotation import disagreements, IAA, model_performance, resolve_disagreements
from pynvdrs.demographics import load_demographics, get_processed_demographics
from pynvdrs.umgpt import GPTClient, generate_response, parse_response
```

The new helpers accept explicit inputs and paths; avoid depending on repository-local globals such as `PROJECT_ROOT` or hardcoded `pr-ifip` directories.
