[Part 2] Creating a new data source
====================================

Currently we support 4 types of data sources:

- plain text -- input text directly in the admin interface (mostly for testing)
- plain text files -- a bunch of files hosted on the same server as Textinator
- JSON files -- a bunchf of JSON files hosted on the same server as Textinator
- Texts API -- a REST API that will be used for getting each datapoint (the endpoint should be specified)

Textinator does **NOT** support uploading data directly via Web interface for multiple reasons:

1. *Disk space limitation*.
2. *Security and privacy considerations*.