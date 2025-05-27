import argparse
import importlib
import itertools
import json
import logging
import os
import secrets
import sys

from collections import OrderedDict
from typing import Iterable
from unittest import mock

# Ugly hack to prevent log file from getting dropped
sys.modules["library.log"] = mock.Mock()

logger = logging.getLogger()

sys.modules["library.log.logger"] = logger

from library.lcd.lcd_comm import Orientation


CACHE_FILE = ".cache"

MAX_NAMES_SHOW = 5
LEFT_PAD = 5
FONT_SIZE = 95
VERTICAL_SIZE = 90
MAX_CHAR_WIDTH = 14
FONT = "roboto-mono/RobotoMono-SemiBold.ttf"

SCREEN_PORT = "AUTO"
SCREEN_MODEL = "LcdCommRevA"
SCREEN_BRIGHTNESS_PERCENTAGE = 100
CURRENTLY_UP_FOREGROUND_COLOR = (0, 9, 148)
CURRENTLY_UP_BACKGROUND_COLOR = (255, 255, 255)
DEFAULT_FOREGROUND_COLOR = (0, 9, 148)
DEFAULT_BACKGROUND_COLOR = (0, 0, 0)
ON_DECK_FOREGROUND_COLOR = (0, 9, 148)
ON_DECK_BACKGROUND_COLOR = (229, 194, 157)


class PatchExit:
    """
    Ugly context patch for sys.exit so we can alert users that the screen was not detected
    upstream library insanely calls sys.exit, then traps errors and calls os._exit which makes
    it impossible to catch the exit normally.
    """

    def __init__(self):
        self._old_exit = sys.exit

    def __enter__(self):
        def _exit(*args, **kwargs):
            logger.error("Unable to find or connect to screen.  Please check connection.")
            self._old_exit(1)

        sys.exit = _exit

    def __exit__(self, *args, **kwargs):
        sys.exit = self._old_exit


class Screen:
    """Dynamically load appropriate library for screen model and manage it"""

    def __init__(self, config):
        self.config = config
        self.lcd_comm = None

        default_display_config = {
            "max_names_show": 5,
            "left_pad": 5,
            "font": "roboto-mono/RobotoMono-SemiBold.ttf",
            "font_size": 95,
            "vertical_size": 90,
            "max_char_width": 14,
        }

        """
        For some reason the simulated font scaling is different than on the RevA.  The following settings
        seem to relatively closely match the RevA results.
        """

        simulated_display_config = default_display_config.copy() | {
            "font_size": 60,
            "vertical_size": 50,
            "max_names_show": 5,
            "max_char_width": 12,
        }

        models = {
            "LcdCommRevA": {"path": "library.lcd.lcd_comm_rev_a", "display_config": default_display_config},
            "LcdCommRevB": {"path": "library.lcd.lcd_comm_rev_b", "display_config": default_display_config},
            "LcdCommRevC": {"path": "library.lcd.lcd_comm_rev_c", "display_config": default_display_config},
            "LcdCommRevD": {"path": "library.lcd.lcd_comm_rev_d", "display_config": default_display_config},
            "LcdSimulated": {"path": "library.lcd.lcd_simulated", "display_config": simulated_display_config}
        }

        library = importlib.import_module(models[self.config["screen_model"]]["path"])
        BaseLCDClass = getattr(library, self.config["screen_model"])

        class ClearScreenMixin:
            def ClearScreen(self):
                self.ScreenOff()
                self.ScreenOn()

            def DrawScreen(self, commands):
                self.ClearScreen()
                for command in commands:
                    self.DisplayText(**command)

        with PatchExit():
            self.lcd_comm = type('LCD', (BaseLCDClass, ClearScreenMixin), {"display_config": models[self.config["screen_model"]]["display_config"]})(com_port=self.config["screen_port"])
        
    def __enter__(self):
        self.lcd_comm.InitializeComm()
        self.lcd_comm.SetOrientation(orientation=Orientation.LANDSCAPE)
        self.lcd_comm.ClearScreen()
        self.lcd_comm.SetBrightness(level=self.config["screen_brightness_percentage"])

        return self.lcd_comm


    def __exit__(self, *args, **kwargs):
        self.lcd_comm.ScreenOff()
        self.lcd_comm.closeSerial()


class InitiativeIterator:
    def __init__(self, iterator: Iterable):
        self.cycle = self.cycle = itertools.cycle(iterator[::-1])
        self.used = []
        self.i = 0
        self.replay = False
    
    def __iter__(self):
        return self

    def burn(self, count):
        if count <= len(self.used):
            self.used = self.used[count:]
        else:
            raise ValueError("Invalid Count")

        self.replay = True
        self.i = 0

    def __next__(self):
        if self.replay:
            if self.i < len(self.used):
                self.i += 1
                return self.used[self.i - 1]
            else:
                self.replay = False
                self.i = 0
        
        item = next(self.cycle)
        self.used.append(item)
        return item


def load_config(config_file: str) -> dict:
    """Loads the configuration file and sets some defaults

    Args:
        config_file (str): path to json configuration file
    Returns:
        dict: Configuration dictionary
    """

    with open(config_file) as f:
        config = json.load(f)
        
        config.setdefault("screen_port", SCREEN_PORT)
        config.setdefault("screen_model", SCREEN_MODEL)
        config.setdefault("screen_brightness_percentage", SCREEN_BRIGHTNESS_PERCENTAGE)
        config.setdefault("on_deck_foreground_color", ON_DECK_FOREGROUND_COLOR)
        config.setdefault("on_deck_background_color", ON_DECK_BACKGROUND_COLOR)
        config.setdefault("currently_up_foreground_color", CURRENTLY_UP_FOREGROUND_COLOR)
        config.setdefault("currently_up_background_color", CURRENTLY_UP_BACKGROUND_COLOR)
        config.setdefault("default_foreground_color", DEFAULT_FOREGROUND_COLOR)
        config.setdefault("default_background_color", DEFAULT_BACKGROUND_COLOR)
        config.setdefault("enemy_foreground_color", None)
        config.setdefault("enemy_background_color", None)

        return config


def get_initiative_order(config: dict, clear_cache: bool=False) -> OrderedDict:
    """Get sorted initiative from the config and cache

    Args:
        config (dict): config file contents as Python dict
        clear_cache (bool): Clear the cache (and don't use it) 

    Returns:
        OrderedDict: Dictionary of initiative in order
    """
    
    initiative_order = config["player_order"].copy()
    initiative_order.update(config["enemy_order"].copy())

    if clear_cache:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
    elif os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                cached_initiative_order = json.load(f)
                for k, v in cached_initiative_order.items():
                    if k in initiative_order and not k.startswith("-") and not isinstance(initiative_order[k], int):
                        initiative_order[k] = v
            
            except json.JSONDecodeError:
                logger.warning("Cache file is corrupted, deleting...")
                os.remove(CACHE_FILE)

    # Any ranges get populated now
    initiative_order = {k:(v if isinstance(v, int) else secrets.choice(range(v[0], v[1] + 1))) for k,v in initiative_order.items() if not k.startswith("-")}

    ordered_initiative = OrderedDict([
        (k, initiative_order[k]) for k, _ in sorted(initiative_order.items(), key=lambda item: item[1] - (1 if item[0] in config["enemy_order"] else 0))
    ])

    with open(CACHE_FILE, "w") as f:
        json.dump(initiative_order, f)

    return ordered_initiative


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog=f"python {sys.argv[0]}", description="TTRPG Initiative Tracker")
    parser.add_argument('-c', '--clear-cache', action="store_true") 
    parser.add_argument("config_file", nargs="?", default="initiative.json")

    args = parser.parse_args()

    config = load_config(args.config_file)
    ordered_initiative = get_initiative_order(config, args.clear_cache)
    ordered_initiative_keys = list(ordered_initiative.keys())
    initiative = InitiativeIterator(ordered_initiative_keys)

    try:
        with Screen(config) as screen:
            max_rows = min(screen.display_config["max_names_show"], len(ordered_initiative_keys))

            if max_rows < 2:
                logger.error("Must be at least two entities configured for initiative")
                exit(1)
            
            while True:
                current_initiative = None
                next_initative = None
                staged_commands = []
                current_up = []
                next_up = []
                
                for row in range(max_rows):
                    key = next(initiative)

                    if row == 0:
                        current_initiative = ordered_initiative[key]

                    if current_initiative == ordered_initiative[key]:
                        current_up.append((key, ordered_initiative[key]))
                    elif next_initative is None:
                        next_initative = ordered_initiative[key]
                
                    if next_initative == ordered_initiative[key]:
                        next_up.append((key, ordered_initiative[key]))

                    background_color = config["default_background_color"]
                    foreground_color = config["default_foreground_color"]

                    if current_initiative == ordered_initiative[key]:
                        background_color = config["currently_up_background_color"]
                        foreground_color = config["currently_up_foreground_color"]
                    elif next_initative == ordered_initiative[key]:
                        background_color = config["on_deck_background_color"]
                        foreground_color = config["on_deck_foreground_color"]
                    
                    if key in config["enemy_order"]:
                        background_color = config.get("enemy_background_color") or background_color
                        foreground_color = config.get("enemy_foreground_color") or foreground_color

                    staged_commands.append({
                        "text": f"{key[:screen.display_config['max_char_width'] - 3].ljust(screen.display_config['max_char_width'] - 3)} {str(ordered_initiative[key]).rjust(2)}", 
                        "x": screen.display_config["left_pad"],
                        "y": row * screen.display_config["vertical_size"], 
                        "font": screen.display_config["font"],
                        "font_size": screen.display_config["font_size"],
                        "font_color": tuple(foreground_color),
                        "background_color": tuple(background_color)
                    })          

                initiative.burn(len(current_up))
                formatted_currently_up = "\n\t".join([f'{x[0]}: {x[1]}' for x in current_up])
                formatted_next_up = "\n\t".join([f'{x[0]}: {x[1]}' for x in next_up])

                print("%s%s%s" % (
                    f"Currently Up:\n\t{formatted_currently_up}\n\n",
                    "================================\n\n" if next_up[0][1] > current_up[0][1] else "",
                    f"On Deck:\n\t{formatted_next_up}\n\n"
                ))
                screen.DrawScreen(staged_commands)
                input("Next?")

    except KeyboardInterrupt:
        pass