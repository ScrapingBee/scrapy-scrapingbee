# How to deploy a new package.

Once the PR has been merged, an administrator has to locally run those commands from a clean checkout:

```
rm -rf dist build
python -m pip install -r requirements.txt
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```