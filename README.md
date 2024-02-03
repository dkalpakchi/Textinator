![Textinator logo](https://github.com/dkalpakchi/Textinator/raw/master/docs/source/logo.png "Textinator")

[![DOI](https://zenodo.org/badge/192495914.svg)](https://zenodo.org/badge/latestdoi/192495914)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/1ac2ba5f4bc14883a02cd395df913859)](https://www.codacy.com/gh/dkalpakchi/Textinator/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=dkalpakchi/Textinator&amp;utm_campaign=Badge_Grade)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

:warning: This project's functionality has grown quite rapidly at some point to the point that some previous funcationality has stopped working. To keep it running, the project needs a major refactoring, and a lot of testing, which at this point is simply too much work. Instead Textinator will get a spiritual successor keeping all the advantages of the current project: internationalization, customizable project setup, flexible labeling system supporting nested and overlapping labeling (although, not perfectly due to introduced bugs that need fixing), focus on both annotation and human evaluation. At the same time, the lessons learnt during developing Textinator will hopefully result in a more maintainable code base (in particular with easy-to-test front-end). I'm truly grateful to all open-source projects (and their developers and maintainers) for letting me embark on this fun journey with Textinator. Thank you!

## New here?

Check out some introductory resources:

*   [Documentation](https://textinator.readthedocs.io/en/latest/)
*   [Video tutorials](https://www.youtube.com/channel/UCUVbyJJFIUwfl129FGhPGJw)
*   Interested how Textinator compares to other Open Source annotation tools for NLP? Check our paper published at LREC 2022: https://aclanthology.org/2022.lrec-1.90.pdf

## Try out Textinator on your own machine

First you will need to [install Docker](https://docs.docker.com/engine/install/) and [docker-compose](https://docs.docker.com/compose/install/). Afterwards just follow these steps:

1.  Clone this repository by running `git clone https://github.com/dkalpakchi/Textinator.git` or download one of the releases and unpack it.
2.  Build and run container in either development or production mode, following the instructions in of the corresponding section below.

## Deployment guide

The recommended way of deploying Textinator is through building a production version of the Docker container, as described in the [Deployment guidelines](https://github.com/dkalpakchi/Textinator/blob/master/notes/DEPLOYING.md). Note that the production version is most definitely more secure and reliable than the development version. However, it's not extremely scalable and hosts both database and Textinator instance on the same machine. The ultimate solution would be to use something like Kubernetes, but it is currently not supported out of the box.

## Developer guide

A good starting place for familiarizing yourself with a codebase is via our [API documentation](https://textinator.readthedocs.io/en/latest/api.html). The documentation for developers is an ongoing effort, but some established workflows are described in our [Development guidelines](https://github.com/dkalpakchi/Textinator/blob/master/notes/DEVELOPING.md), (for instance, how to run a development Docker instance).

## Contributing

Want to contribute to Textinator? Check out our [Contribution guidelines](https://github.com/dkalpakchi/Textinator/blob/master/notes/CONTRIBUTING.md).

## Internationalization

The software is developed in English.

Partial translation is available for these languages (in alphabetical order):
*   \[ ] Russian thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)
*   \[ ] Swedish thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)
*   \[ ] Ukrainian thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)

Upcoming languages

*   \[ ] Dutch
*   \[ ] Spanish

## Credits
Textinator depends on so many other wonderful open-source projects, that they deserve a special [Credits file](https://github.com/dkalpakchi/Textinator/blob/master/notes/CREDITS.md)

## Cite Textinator
```
@inproceedings{kalpakchi-boye-2022-textinator,
    title = "Textinator: an Internationalized Tool for Annotation and Human Evaluation in Natural Language Processing and Generation",
    author = "Kalpakchi, Dmytro  and
      Boye, Johan",
    booktitle = "Proceedings of the Thirteenth Language Resources and Evaluation Conference",
    month = jun,
    year = "2022",
    address = "Marseille, France",
    publisher = "European Language Resources Association",
    url = "https://aclanthology.org/2022.lrec-1.90",
    pages = "856--866"
}
```
