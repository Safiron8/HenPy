# HenPy
Automates all the work around your anime image folder

## Features
Things HenPy can do

- Image size optimization
- Detection and management of duplicates
- Increasing resolution using AI

## TODO
Things I plan to add at some point

- Settings using parameters
- Tagging images by content
- Scraping images from various sources

## Tech

HenPy uses a number of open source projects to function properly:

- [difPy](https://github.com/elisemercury/Duplicate-Image-Finder) - Duplicate Image Finder
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) - AI Upscaller
- [MozJPEG](https://github.com/wanadev/mozjpeg-lossless-optimization) - Image optimalizer

## Installation

Setup environment using [Anaconda](https://www.anaconda.com)
```sh
conda env create -f HenPy.yml
conda activate HenPy
```

Run script
```sh
python HenPy.py
```

## License

GNU General Public License v3.0
(Let me know if there are any problems)