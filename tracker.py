import importlib
import json
import logging
import secrets
import sys

from unittest import mock

# Ugly hack to prevent log file from getting dropped
sys.modules["library.log"] = mock.Mock()
sys.modules["library.log.logger"] = logging.getLogger()

from library.lcd.lcd_comm import Orientation


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


def get_lcd_instance(model_name, port):
    """Dynamically load appropriate library for screen model"""

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

    library = importlib.import_module(models[model_name]["path"])
    BaseLCDClass = getattr(library, model_name)

    class ClearScreenMixin:
        def ClearScreen(self):
            self.ScreenOff()
            self.ScreenOn()

    return type('LCD', (BaseLCDClass, ClearScreenMixin), {"display_config": models[model_name]["display_config"]})(com_port=port)


def draw_screen(commands):
    lcd_comm.ClearScreen()
    for command in commands:
        lcd_comm.DisplayText(**command)

def load_config():
    config_file = None

    if len(sys.argv) == 1:
        config_file = "initiative.json"
    else:
        if sys.argv[1] in ["-h", "--help"] or len(sys.argv) != 2:
            print(f"Usage:\n\tpython {sys.argv[0]} <path/to/configuration.json>")
            sys.exit(1)
        else:
            config_file = sys.argv[1]

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


if __name__ == "__main__":
    config = load_config()

    lcd_comm = get_lcd_instance(config["screen_model"], config["screen_port"])
    lcd_comm.InitializeComm()
    lcd_comm.SetOrientation(orientation=Orientation.LANDSCAPE)
    lcd_comm.ClearScreen()
    lcd_comm.SetBrightness(level=config["screen_brightness_percentage"])

    initiative_order = config["player_order"].copy()
    initiative_order.update(config["enemy_order"].copy())
    initiative_order = {k:(v if isinstance(v, int) else secrets.choice(range(v[0], v[1] + 1))) for k,v in initiative_order.items() if not k.startswith("-")}

    ordered = [k for k, _ in sorted(initiative_order.items(), key=lambda item: item[1] - (1 if item[0] in config["enemy_order"] else 0))]

    try:
        while len(initiative_order):
            current_initiative = None
            next_initative = None

            current_up = []
            next_up = []

            staged_commands = []

            for row, key in enumerate((ordered[::-1][0: min(lcd_comm.display_config["max_names_show"], len(ordered))])):
                
                if row == 0:
                    current_initiative = initiative_order[key]

                if current_initiative == initiative_order[key]:
                    current_up.append((key, initiative_order[key]))
                elif next_initative is None:
                    next_initative = initiative_order[key]
            
                if next_initative == initiative_order[key]:
                    next_up.append((key, initiative_order[key]))

                background_color = config["default_background_color"]
                foreground_color = config["default_foreground_color"]

                if current_initiative == initiative_order[key]:
                    background_color = config["currently_up_background_color"]
                    foreground_color = config["currently_up_foreground_color"]
                elif next_initative == initiative_order[key]:
                    background_color = config["on_deck_background_color"]
                    foreground_color = config["on_deck_foreground_color"]
                
                if key in config["enemy_order"]:
                    background_color = config.get("enemy_background_color") or background_color
                    foreground_color = config.get("enemy_foreground_color") or foreground_color

                staged_commands.append({
                    "text": f"{key[:lcd_comm.display_config['max_char_width'] - 3].ljust(lcd_comm.display_config['max_char_width'] - 3)} {str(initiative_order[key]).rjust(2)}", 
                    "x": lcd_comm.display_config["left_pad"],
                    "y": row * lcd_comm.display_config["vertical_size"], 
                    "font": lcd_comm.display_config["font"],
                    "font_size": lcd_comm.display_config["font_size"],
                    "font_color": tuple(foreground_color),
                    "background_color": tuple(background_color)
                })          

            print("%s%s%s" % (
                f"Currently Up:\n\t{"\n\t".join([f'{x[0]}: {x[1]}' for x in current_up])}\n\n",
                "================================\n\n" if next_up[0][1] > current_up[0][1] else "",
                f"On Deck:\n\t{"\n\t".join([f'{x[0]}: {x[1]}' for x in next_up])}\n\n"
            ))
            draw_screen(staged_commands)
            input("Next?")

            for i in range(len(current_up)):
                name = ordered.pop()
                ordered.insert(0, name)

    except KeyboardInterrupt:
        lcd_comm.ScreenOff()
        lcd_comm.closeSerial()