import time, sys, pynput, random, datetime, threading, os, string
from typing import Literal, Tuple
from copy import deepcopy
from tcolors import TrueColor, BgTrueColor, Mod

DEBUG = True
log_filename = ""

class Logger:

    logfile = None

    def __init__(self): # Initialize logger so we can log stuff
        if self.logfile_path == '':
            if not os.path.exists('/logs'):
                os.makedirs('/logs')
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H-%M")
            self.logfile = open(f'/logs/{timestamp}.log', 'a', encoding = 'utf-8')

    def log(self, type: Literal['ENGINE', 'INFO', 'WARN', 'ERROR'], message = 'undefined log message'):
        timestamp = datetime.datetime.now().strftime(f'[%d-%m-%Y] [%H:%M:%S]')
        self.logfile.write(f"{timestamp} [{type}] {message}\n")

class Sprite:
    """
    Main sprite class for handling sprite graphic data.
    Arguments:
        name:           The name of the sprite.
        width:          The width of the sprite in pixels.
        height:         The height of the sprite in pixels.
        sprite_data:    A list of strings representing the pixel data of the sprite.
        color_mode:     The color mode of the sprite ("single", "pixel", "single_custom", "pixel_custom").
        color_data:     A list of strings representing the color data of the sprite.
        sprite_mode:    The sprite mode ("single" for single-frame sprites, "multi" for multi-frame sprites).
        sprite_cuantity:The number of frames in the sprite (only for multi-frame sprites).
    """
    def __init__(self, name: str, width: int, height: int, sprite_data: list[str], color_mode: Literal["single", "pixel", "single_custom", "pixel_custom"] = "single", color_data: list[str] = None, sprite_mode: Literal["single", "multi"] = "single", sprite_cuantity: int = 1, extra_val_1 = None, extra_val_2 = None, extra_val_3 = None):
        """
        Main sprite class for handling sprite graphic data.
        Arguments:
            name:           The name of the sprite.
            width:          The width of the sprite in pixels.
            height:         The height of the sprite in pixels.
            sprite_data:    A list of strings representing the pixel data of the sprite.
            color_mode:     The color mode of the sprite ("single", "pixel", "single_custom", "pixel_custom").
            color_data:     A list of strings representing the color data of the sprite.
            sprite_mode:    The sprite mode ("single" for single-frame sprites, "multi" for multi-frame sprites).
            sprite_cuantity:The number of frames in the sprite (only for multi-frame sprites).
        """
        self.width = width
        self.height = height
        self._color_mode = color_mode
        self._valid_data = True
        self.name = name
        self.sprite_mode = sprite_mode
        self._sprite_cuantity = sprite_cuantity
        self.extra1 = extra_val_1
        self.extra2 = extra_val_2
        self.extra3 = extra_val_3

        # data type validator
        if type(color_data) != list and color_mode == "pixel":
            color_data = []
            for px in range(len(sprite_data)):
                color_data.append(" ")
        elif type(color_data) != str and color_mode == "single":
            color_data = " "

        # data size validator
        if  (len(sprite_data) != self.width * self.height) and self.sprite_mode == "single":
            self._valid_data = False
        elif (len(sprite_data) != self.width * self.height * sprite_cuantity) and self.sprite_mode == "multi":
            self._valid_data = False
        elif len(sprite_data) != len(color_data) and color_mode == "pixel":
            self._valid_data = False

        self.readable_data = (sprite_data, color_data)

    def load_raw(self, frame = 0):
        """
        Loads the raw pixel and color data for the specified frame.\n
        Returns a tuple containing two lists: pixel_raw_data and color_raw_data.
        Arguments:
            frame:  The frame number to load (for multi-frame sprites).
        """
        pixel_data = self.readable_data[0]                                                 
        color_data = self.readable_data[1]                                                 
        pixel_raw_data = []
        color_raw_data = []
        offset = self.height * self.width * frame                                                    
        for row in range(self.height):                                                                                                                                        
            for pixel in range(self.width):
                index = (row * self.width) + pixel + offset
                if self._color_mode == "pixel":
                    if pixel_data[index] != "nop":
                        if color_data[index] == " ":
                            pixel_raw_data.append(str(pixel_data[index]))
                            color_raw_data.append("")
                        else:
                            pixel_raw_data.append(str(pixel_data[index]))
                            color_raw_data.append(str(preset_color_codes.get(color_data[index], "")))
                    else:
                        pixel_raw_data.append("nop")
                        color_raw_data.append("")
                elif self._color_mode == "single":
                    if pixel_data[index] != "nop":
                        pixel_raw_data.append(pixel_data[index])
                        color_raw_data.append(preset_color_codes.get(color_data, ""))
                    else:
                        pixel_raw_data.append("nop")
                        color_raw_data.append("")
                elif self._color_mode == "single_custom":
                    if pixel_data[index] != "nop":
                        pixel_raw_data.append(pixel_data[index])
                        color_raw_data.append(color_data)
                    else:
                        pixel_raw_data.append("nop")
                        color_raw_data.append("")
                elif self._color_mode == "pixel_custom":
                    if pixel_data[index] != "nop":
                        if color_data[index] == " ":
                            pixel_raw_data.append(str(pixel_data[index]))
                            color_raw_data.append("")
                        else:
                            pixel_raw_data.append(str(pixel_data[index]))
                            color_raw_data.append(color_data[index])
                    else:
                        pixel_raw_data.append("nop")
                        color_raw_data.append("")
        return (pixel_raw_data, color_raw_data)   

class Screen:
    """
    Class that manages everything related to graphic rendering
    Arguments:
        height:     The height of the screen in characters.
        width:      The width of the screen in characters.
    """
    def __init__(self, height: int, width: int):
        """
        Class that manages everything related to graphic rendering
        Arguments:
            height:     The height of the screen in characters.
            width:      The width of the screen in characters.
        """
        self.height = height
        self.width = width
        self._screen = []
        self.pixel_layers = []
        self.color_layers = []
        self.pixel_blank = []
        self.color_blank = []

    def create_text(self, x: int, y: int, layer: int, text_data: Tuple[str, str, str]):
        """
        Creates a text element on the screen.
        Arguments:
            x:          The x position to start drawing the text.
            y:          The y position to start drawing the text.
            layer:      The layer to draw the text on.
            text_data:  A tuple containing the text string, foreground color code, and background color code.
        """
        text, fg, bg = text_data
        workvar = ""
        text_pixel_data = []
        for character in text:
            workvar += character
            if len(workvar) == 3:
                text_pixel_data.append(workvar)
                workvar = ""
        for pixel in text_pixel_data:
            if layer != 0:
                if (0 <= x < self.width) and (0 <= y < self.height) and bg != "":
                    self.pixel_layers[y][x][layer] = f"{pixel}"
                    self.color_layers[y][x][layer] = f"{bg}{fg}"
                elif (0 <= x < self.width) and (0 <= y < self.height) and bg == "":
                    self.pixel_layers[y][x][layer] = f"{pixel}"
                    self.color_layers[y][x][layer] = f"{fg}"
                else:
                    continue
            x += 1

    def create_sprite(self, x: int, y: int, layer: int, sprite_data_raw: tuple, sprite_num: int = 0, Sprite: Sprite = None):
        """
        Creates a sprite element on the screen.
        Arguments:
            x:                  The x position to start drawing the sprite.
            y:                  The y position to start drawing the sprite.
            layer:              The layer to draw the sprite on.
            sprite_data_raw:    A tuple containing the raw pixel and color data of the sprite.
            sprite_num:         The frame number of the sprite to draw (for multi-frame sprites).
            Sprite:             The Sprite object containing the sprite's properties.
        """
        sprite_data = sprite_data_raw
        offset = (Sprite.height * Sprite.width) * sprite_num
        if sprite_data == None or Sprite == None:
            return
        pixel_write_data, color_write_data = sprite_data
        for row in range(Sprite.height):
            for column in range(Sprite.width):
                if (layer != 0) and ((0 <= x + column < self.width) and (0 <= y + row < self.height)):
                    if pixel_write_data[offset + (row * Sprite.width) + column] != "nop":
                        self.pixel_layers[y + row][x + column][layer] = pixel_write_data[offset + (row * Sprite.width) + column]
                        self.color_layers[y + row][x + column][layer] = color_write_data[offset + (row * Sprite.width) + column]
                    elif self.pixel_layers[y + row][x + column][layer] == "nop":
                        self.pixel_layers[y + row][x + column][layer] = "nop"
                        self.color_layers[y + row][x + column][layer] = "nop"

    def create_pixel(self, x: int, y: int, layer: int, pixel_data: Tuple[str, str, str]):
        """
        Creates a pixel element on the screen.
        Arguments:
            x:          The x position to draw the pixel.
            y:          The y position to draw the pixel.
            layer:      The layer to draw the pixel on.
            pixel_data: A tuple containing the pixel string, foreground color code, and background color code.
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        px, fg, bg = pixel_data
        if layer != 0:
            if bg != "":
                self.pixel_layers[y][x][layer] = f"{px}"
                self.color_layers[y][x][layer] = f"{bg}{fg}"
            else:
                self.pixel_layers[y][x][layer] = f"{px}"
                self.color_layers[y][x][layer] = f"{fg}"
    
    def set_bg(self, initx: int, inity: int, finx: int, finy: int, color: str):
        """
        Sets the background color for a specified area of the screen.
        Arguments:
            initx:  The initial x position of the area.
            inity:  The initial y position of the area.
            finx:   The final x position of the area.
            finy:   The final y position of the area.
            color:  The background color code to set.
        """
        sizex = finx - initx
        sizey = finy - inity
        for row in range(sizey):
            for column in range(sizex):
                if not(column + initx < 0 or column + initx >= self.width or row + inity < 0 or row + inity >= self.height):
                    self.color_layers[row + inity][column + initx][0] = f"{color}"

    def initialize(self, layers: int, bg_color: str):
        """
        Initializes the screen with the specified number of layers and background color.
        Arguments:
            layers:    The number of layers to create.
            bg_color:  The background color code to use.
        """
        self._layers = layers
        self._bg_color = bg_color
        worklist = []
        for height_line in range(self.height):
            worklist.append([])
            for width_line in range(self.width):
                worklist[height_line].append([])
                for layer in range(self._layers):
                    worklist[height_line][width_line].append("nop")
        self.pixel_blank = worklist 
        worklist = []
        for height_line in range(self.height):
            worklist.append([])
            for width_line in range(self.width):
                worklist[height_line].append([])
                for layer in range(self._layers):
                    if layer == 0:
                        worklist[height_line][width_line].append(self._bg_color)
                    else:
                        worklist[height_line][width_line].append("")
        self.color_blank = worklist 

    def memory_reset(self):
        """
        Resets the screen memory to the blank state.
        """
        self.pixel_layers = deepcopy(self.pixel_blank)
        self.color_layers = deepcopy(self.color_blank)

    def bake_screen(self):
        """
        Bakes the current screen state into a final renderable format.
        """
        final_bake = []
        for height_line in range(self.height):
            final_bake.append([])
            pixel_bake = []
            color_bake = []
            layered_pixel = ""
            layered_color = ""
            for width_line in range(self.width):
                bg = False
                pixel = "   "
                fgcolor = "nop"
                bgcolor = self.color_layers[height_line][width_line][0]
                layered_pixel = self.pixel_layers[height_line][width_line]
                layered_color = self.color_layers[height_line][width_line]
                reversed_pixel_layers = reversed(layered_pixel)
                reversed_color_layers = reversed(layered_color)
                for pixel_layer, color_layer in zip(reversed_pixel_layers, reversed_color_layers):
                    if not bg:
                        if pixel_layer != "nop":
                            pixel = pixel_layer
                            fgcolor = color_layer
                            bg = True
                        else:
                            pixel = "   "
                            fgcolor = ""
                    else:
                        if pixel_layer != "nop":
                            bgcolor = color_layer
                            break
                        else:
                            bgcolor = ""
                pixel_bake.append(pixel)
                color_bake.append(bgcolor + fgcolor)
            #log("debug", f"color bake: {color_bake}\n pixel bake: {pixel_bake}")
            for item in range(len(pixel_bake)):
                final_bake[height_line].append(color_bake[item] + pixel_bake[item] + "\033[0m")
        self._screen = final_bake
    
    def print_screen(self):
        """
        Prints the baked screen to the terminal.
        """
        screen_print = ""
        for height_line in self._screen:
            for width_line in height_line:
                screen_print += width_line
            screen_print += "\n\033[0m"
        sys.stdout.write("\033[2J\033[H\n" + screen_print)
        sys.stdout.flush()

default_keymap = {"up"          : pynput.keyboard.Key.up, 
                  "down"        : pynput.keyboard.Key.down,
                  "left"        : pynput.keyboard.Key.left,
                  "right"       : pynput.keyboard.Key.right,
                  "space"       : pynput.keyboard.Key.space,
                  "esc"         : pynput.keyboard.Key.esc,
                  "enter"       : pynput.keyboard.Key.enter,
                  "backspace"   : pynput.keyboard.Key.backspace}

class Game:
    def __init__(self, Screen: Screen, key_map: dict = default_keymap):
        """
        Class that represents an arcade machine.
        Arguments:
            arcade_name:    The name of the arcade machine.
            Screen:         The Screen object to use for rendering.
            type:           The type of arcade machine ("python_game" or "pyrcade_script_game").
            mode:           The mode of the arcade machine ("Terminal" or "Windowed").
            key_map:       A dictionary mapping input keys to pynput keyboard keys.
        """
        self._screen = Screen
        self.input = ""
        self._key_map = key_map
        self._engine_ver = "1.0.2"

    def start_game(self, game_code = None):
        """
        Starts the arcade machine with the provided game code function.
        Arguments:
            game_code: The game code function to run. MUST BE A FUNCTION THAT TAKES NO ARGUMENTS.
        """
        game_code()
        
    def start_input(self, keys: list = ["up", "down", "left", "right", "space", "esc"]):
        """
        MUST RUN BEFORE STARTING THE ARCADE MACHINE!\n
        Starts the input listener for the arcade machine.
        Arguments:
            keys: A list of keys to listen for.
        """
        self._actual_inputs = set()
        self._keys = keys
        def input_listener_press(keypressed):
            for key in self._keys:
                if self._key_map[key] == keypressed:
                    self._actual_inputs.add(key)
        def input_listener_release(keyrelease):
            for key in self._keys:
                if self._key_map[key] == keyrelease:
                    self._actual_inputs.discard(key)
        listener = pynput.keyboard.Listener(on_press = input_listener_press, on_release = input_listener_release)
        listener.start()