install:
	pip install -e .[app,dev]

test:
	python -m pytest -q

app:
	mhc-atlas app --demo cross_allele_demo

demo:
	mhc-atlas list-demos

package-check:
	python -m build
