# Contributing

Contributions are welcome, and they are greatly appreciated!

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs as [Github issues](https://github.com/chr1st1ank/dike/issues).

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug, ideally a minimal script which triggers the issue.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

dike could always use more documentation, whether as part of the
official dike docs, in docstrings, or even on the web in blog posts,
articles, and such.

### Submit Feedback

The best way to send feedback is to file an [issue on Github](https://github.com/chr1st1ank/dike/issues).

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

## Get Started!

Ready to contribute? Here's how to set up `dike` for local development.

1. Fork the `dike` repo on GitHub.
2. Clone your fork locally

```
    $ git clone git@github.com:your_name_here/dike.git
```

3. Ensure [poetry](https://python-poetry.org/docs/) is installed.
4. Install dependencies and start your virtualenv:

```
    $ poetry install --with=test,doc,dev
```

5. Create a branch for local development:

```
    $ git checkout -b name-of-your-bugfix-or-feature
```

   Now you can make your changes locally.

6. When you're done making changes, check that your changes pass the
   tests, including testing other Python versions, with tox:

```
    $ tox
```

7. Commit your changes and push your branch to GitHub:

```
    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature
```

8. Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.md.
3. The pull request should work for CPython 3.7, 3.8 and 3.9. Check
   https://github.com/chr1st1ank/dike/actions
   and make sure that the tests pass for all supported Python versions.

## Deploying

A reminder for the maintainers on how to deploy.

On branch "main":
- Adjust CHANGELOG.md as described on https://keepachangelog.com
- Then run `inv version [major | minor | patch]`. This updates the version numbers and creates a tagged commit.
- Push the commit to github: `git push origin main && git push --tags`.
- A github action will automatically create a github release and publish to pypi.
