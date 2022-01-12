[![Build Status](https://travis-ci.org/Scan-o-Matic/scanomatic.svg?branch=master)](https://travis-ci.org/Scan-o-Matic/scanomatic)

# Scan-o-matic (program) and scanomatic (python module)

This project contains the code for the massive microbial phenotyping platform Scan-o-matic.

Scan-o-matic was published in [G3 September 2016](http://g3journal.org/content/6/9/3003.full).

Please refer to the [Wiki](https://github.com/local-minimum/scanomatic/wiki) for instructions on use, installation and so on.

We have a newsletter that informs about important changes and updates to Scan-o-matic, you can sign up [here](http://cmb.us13.list-manage1.com/subscribe?u=a6a16e48af209606d0f418c95&id=2ebf1ce16f).

If you are considering setting up Scan-o-matic at your lab, we would be very happy and would love to hear from you.

Gothenburg University is currently buying further development and service from private company Molflow. Expect to hear more about this soon.

Before you decide on this, the Faculty of Science at University of Gothenburg has included Scan-o-matic among its high-throughput phenomics infrastructure and it is our expressed interest that external researchers come to us. If you are interested there's some more information and contact information here: [The center for large scale cell based screeening](http://cmb.gu.se/english/research/microbiology/center-for-large-scale-cell-based-screening). It is yet to become listed on the page, but don't worry, it is part of the list.

## Current focus

The ability to add new Cell Count Calibrations via UI is being developed.

Completing and securing up the code for the first release of 2.x

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

The tox environments are `lint`, `mypy`, `unit`, `integration` and `system`. Only the latter require additional dependencies.

### Tox mypy type checking

Currently this is not required as the code still is riddled with type errors, however there's a `typecheck-changed.sh` that filteres out errors only in files changed in the branch. It should be used to guarantee that no new errors are introduced and it is encouraged to clean up unrelated errors in the files touched.

### System tests

System tests require `firefox`, `geckodriver`, `google-chrome` and `chromedriver` to be installed on host system.
After that it run with `tox -e system`.
