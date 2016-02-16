# Build Calculator

## Usage

A python implementation of a build calculator for League of Legends.

See `example.py` for examples on how to use the code, which you can use by running `python example.py`.

Mastery data is stored in `resources/patch_number/mastery.json`. If you find errors, let us know or send us a pull request with the updates. Note that as long as the masteries have not changed, previous patch data may still be correct.

## Setup

To install, clone the repository (or download the zip and unzip the contents) into a folder of your choice. Add this folder to your `PYTHONPATH` environment variable (try googling for "add new pythonpath environment variable" if you don't know how to do this).

While you add (or edit) your `PYTHONPATH`, you can also create a new environment variable called `DEV_KEY` and set it to your Riot API development key. This allows you to run `python example.py` without inputing your API key, because `example.py` will read it from your system.

Dependencies include [Cassiopeia](https://github.com/meraki-analytics/cassiopeia) and python's tabulate module. You can `pip install` both of these, but if you want to ensure you have the most up-to-date version of Cassiopeia, you can clone it and follow the same directions as above to add its location to your `PYTHONPATH`.
