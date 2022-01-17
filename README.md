[![Scan-o-Matic CI](https://github.com/Scan-o-Matic/scanomatic-standalone/actions/workflows/ci.yml/badge.svg)](https://github.com/Scan-o-Matic/scanomatic-standalone/actions/workflows/ci.yml)

# Scan-o-matic (program) and scanomatic (python module)

This project contains the code for the massive microbial phenotyping platform Scan-o-matic.

Scan-o-matic was published in [G3 September 2016](http://g3journal.org/content/6/9/3003.full).

Please refer to the general [Scan-o-Matic Wiki](https://github.com/Scan-o-Matic/scanomatic/wiki) for further instructions, though setup and starting should like described below.

# Setting up and running

1. Clone this library `git@github.com:Scan-o-Matic/scanomatic-standalone.git`
2. And change directory: `cd scanomatic-standalone`
3. Build the image `docker-compose build`
4. Create an environment-file or export the `SOM_PROJECTS_ROOT` and `SOM_SETTINGS` variables. Each pointing to a location where you wish to store your projects and settings respectively. See https://docs.docker.com/compose/environment-variables/#the-env-file for specifying them in an env-file, else include them in e.g. your `.bashrc`. Neither path should point to directories inside the local copy of the git-repository.
5. Run `docker-compose up -d`. Omit the `-d` if you don't wish to run it in the background.
6. In your browser navigate to `http://localhost:5000`

## Reporting issues

If you have a problem please create and issue here on the git repository.
If it relates to a specific project please include the relevant log-files for that project.
There are also a set of files that probably is relevant: `.project.settings`, `.project.compilation`, `.project.compilation.instructions`, `.scan.instructions`, `.analysis.instructions`...
Please also include the server and ui-server log files (those will be localized to a hidden folder called `.scan-o-matic/logs` in your users directory.

Do however please note, that if you are doing something super secret, the files will contain some information on what you are doing and it may be needed that you go through them before uploading them publically.
In this case, only redact the sensitive information, but keep general systematic parts of these lines as intact as possible.

# Developers

This section contains information relevant to those contributing to the source-code.

## Tests and quality assurance

Scan-o-Matic has three kinds of tests: unit, integration, and system tests. In addition the Scan-o-Matic code should be lint free and pass type checking.
Backend tests, linting and typechecking are run by `tox` while front-end tests are run with `karma` and lint with `eslint`.

The tox environments are `lint`, `mypy`, `unit`, `integration` and `system`. Only the latter requires additional dependencies.

### Tox mypy type checking

Currently this is not required as the code is still riddled with type errors, however there's a `typecheck-changed.sh` that filters out errors only in files changed in the branch. It should be used to guarantee that no new errors are introduced and it is encouraged to clean up unrelated errors in the files touched.

### System tests

System tests require `firefox`, `geckodriver`, `google-chrome` and `chromedriver` to be installed on host system.
After that it run with `tox -e system`.
