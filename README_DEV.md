# How to deploy a new package.

Once the PR has been merged, an administrator has to locally run those two commands:

```
python -m pip install build
python -m twine upload dist/*
```

If it is the first time they do it, they will probably need to do first:
```
python -m pip install build
python -m pip install --upgrade twine
```