# QOI Stuff

My attempt at making an en/decoder for the [QOI image format](https://qoiformat.org/) in Python

## Issues

The encoder transforms all the images into RGBA format before encoding them, which means that the 13th byte(colour channels) will always be set to 4.
