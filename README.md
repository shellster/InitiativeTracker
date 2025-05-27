# TTRPG Initiative Tracker

This project allows TTRPG initative tracking via small screens typically used for displaying PC Hardware settings

![Initiative Tracker in Holder](screenshots/InitiativeTracker.png "Initiative Tracker in Holder")

Before attempting to use this library please carefully read the "Acknowledgements and Important Compatibility Notes" section.


## Instructions

### Install Requirements

Install python3.10+.

Use your preferred virtual environment creation method and create a virtual environment in the root project folder and enter enter the virtual environment.  If you are not familar with python, I recommend `pipenv`.  After installing it you can simply run:

`pipenv shell` 

Install the required libraries:

`pip install -r requirements.txt`


### Configure Settings

The initative tracker is operated from a simple `initative.json` config file (by default, or you can provide a path as an argument when you run the tracker).  A sample is provided in this repo, and
we will go through it line by line here, for the configurable options.

**IMPORTANT NOTE ON COLORS**:
Several of the options deal with color specifications.  Each color should be specified as an array of three integers from 0-255, in the order: [red, green, blue].  
On my RevA, I've found that some perfectly valid color combinations will cause to screen to glitch out and lock-up, requiring a power cycle.  If you experience this, try 
tweaking your color values slightly until you find something that works.

* **screen_port**: Defaults to `"AUTO"`.  This corresponds to the Serial/COM port the screen you are using is attached to.  In most cases you can
either not specify it or set it to `"AUTO"` for autodetection of the appropriate port.

* **screen_model**: Defaults to `"LcdCommRevA"`. This corresponds to a supported model of screen.  Current supported options are: `"LcdCommRevA"`, `"LcdCommRevB"`, `"LcdCommRevC"`, `"LcdCommRevD"`, `"LcdSimulated"`

* **screen_brightness_percentage**: Defaults to `100`.  This is an integer representing the percentage brightness the screen should be.  Apparently original Turing RevA screens warn about getting hot at 100%, but I have not observed any problems.

* **default_foreground_color**: Defaults to `[0, 9, 148]`.  This is the default font color if no other special condition applies.

* **default_background_color**: Defaults to `[0, 0, 0]`.  This is the default background color for the row if no other special condition applies.

* **currently_up_foreground_color**: Defaults to `[0, 9, 148]`.  This is the font color of the player(s) currently acting.

* **currently_up_background_color**: Defaults to `[255, 255, 255]`.  This is the background color for the row(s) of the player(s) currently acting.

* **on_deck_foreground_color**: Defaults to `[0, 9, 148]`.  This is the font color of the player(s) next to act.

* **on_deck_background_color**: Defaults to `[229, 194, 157]`.  This is the background color for the row(s) of the player(s) next to act.

* **enemy_foreground_color**: If provided, enemy font color will always appear as this in the initiative list, otherwise enemy will be the same colors as a player for currently up, on deck, other.

* **enemy_background_color**: If provided, enemy background row color will always appear as this in the initiative list, otherwise it will be the same background colors as a player for currently up, on deck, other.

* **player_order**: This is object where the keys are the player's names (or player-aligned characters in this initiative) and the values are either an integer representing their initiative order, or an array of two values 
representing the inclusive range of their initiative.  In the latter case, a random initiative value in the provided range will be rolled at runtime.  Order of players in object is not important (they are sorted at runtime).  
Adding a `-` to the front of the player name will result in the player not appearing in the initiative list (a quick way to temporarily remove a player without deleting them).  Player names will be truncated as necessary to 
fit on the screen.  For my screen, it will truncate all names to 11 characters.

* **enemy_order**: This follows all the same rules and configuration options as player_order, but it represents any "enemy" characters in relation to the players.

### Run Tracker

Once you have configured your initiative.json file, you can run the program like so:

```
usage: python tracker.py [-h] [-c] [config_file]

TTRPG Initiative Tracker

positional arguments:
  config_file

options:
  -h, --help         show this help message and exit
  -c, --clear-cache
```

(config_file is optional, will default to `initiative.json`)

Assuming you've configured everything correctly, the initiative should appear after a few seconds on your little screen.

In your console, you'll see something like this:

```
Currently Up:
        Bob: 22

On Deck:
        Korak: 19
        Hobgoblin 1: 19

Next?
```

This allows the DM to see the currently active entity and upcoming entities while having the screen pointing out to the players.

The "Next?" message will only appear once the screen is fully drawn (which can take several seconds).

Pressing `Enter` will advance the initiative one entity.

`Ctrl + C` will turn off the screen and exit.


**Notes on Initiative Order**: 

If a player or players and one or more enemies share initiative order, the code will always ensure that the player(s) appear first in the initiative list.
Also, unless the `-c` option is specified, the order will be cached.  Upon starting the tracker again, any initiative in the config that was specified as a range
will instead use the cached value if one exists for that enemy or player.  This allows you stop initiative and added or remove players or enemies and restart
without having enemy initiative orders jump around if you had specified an range to auto-roll for your enemies.  If you want to re-roll, or it is a new fight,
make sure to pass the `-c` option to discard an recache the initiative order.


## Acknowledgements and Important Compatibility Notes

This project absolutely would not be possible without the fantastic work and library found here:
https://github.com/mathoudebine/turing-smart-screen-python

Support for screens is thus reliant on the screen support provided by this library.  If you wish to utilize this module, please ensure
that your screen is compatible or alternatively try the LcdSimulated option.  Furthermore, I have only tested the configuration on an 
LcdCommRevA.  For other screens, you may need to adjust the font sizes, ClearScreen function, and other parameters if the existing ones 
don't work well (they almost certainly will not for other resolution screens)

Pull Requests are welcome and appreciated for increasing support.

If additional screen revisions become available, providing the code does not otherwise change, you should be able to copy the new revision
from turing-smart-screen-python.library.lcd.<revision> into this projects library.lcd folder.  Then add it to the list of models in
`get_lcd_instance`

## 3D Printed Case

Checkout the cad folder for 3D printable holders for your screen that will clip to the back of a DM screen.


## Versions

* Version 0.1:  Initial Release

* Version 1.0:  Refactor, clean-up, and support for caching initiatives