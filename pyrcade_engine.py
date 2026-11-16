import sys, pynput, random, datetime, os, tkinter, time
from typing import Literal, Tuple
from copy import deepcopy
from tcolors import TrueColor, BgTrueColor, Mod
from PIL import Image, ImageTk
from pathlib import Path

DEBUG = True

class Logger:

    logfile = None

    def __init__(self): # Initialize logger so we can log stuff
        logger_path = Path(__file__).parent / 'logs'
        logger_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H-%M-%S")
        self.logfile = open(logger_path / f'{timestamp}.log', 'a', encoding = 'utf-8')

    def log(self, type: Literal['ENGINE', 'INFO', 'WARN', 'ERROR'], message = 'undefined log message'):
        timestamp = datetime.datetime.now().strftime(f'[%d-%m-%Y %H:%M:%S]')
        if not DEBUG and type == 'ENGINE':
            return
        self.logfile.write(f"{timestamp} [{type}] {message}\n")
        self.logfile.flush()

EngineLogger = Logger()
EngineLogger.log("ENGINE", "Engine logger initialized")

sprites = [] # Internal list that holds a reference to all the sprites that are created, used to update animations via the rendering pipeline

class Sprite:
    '''
    Base graphical class, used to create sprites and animated sprites for the game engine
    '''
    sprite_data_file = None #Reference to a file containing all the data of the sprite
    dimensions: Tuple[int, int] = (0, 0) #Width and height of the sprite
    animations: dict = {} #Dictionary containing all the animation data of the sprite
    current_animation: str = None #The name of the current animation being played
    current_frame: int = -1 #The index of the current frame being displayed
    loop: bool = False #Whether the animation should loop or not
    color_palette: int = 0 #Index in the color palette list of the game
    sprite_data: list = [] #List containing the raw "pixel" data of the sprite, each pixel is a number from 0 - 8, 0 is transparent and the other are an index in the color pallete
    sprite_index: int = 0 #The index of the current sprite being displayed, used for internal engiine shenanigans, do not touch this unless you know what you are doing
    
    def __init__(self, sprite_data_file: str):
        '''
        Base graphical class, used to create sprites and animated sprites for the game engine
        '''
        self.sprite_data_file = sprite_data_file
        global sprites
        sprites.append(self)
        self.sprite_index = len(sprites) - 1
        self._load_data()

    def _load_data(self):
        '''
        INTERNAL METHOD - DO NOT CALL DIRECTLY\n
        Loads the sprite data from the sprite_data_file and fills the class attributes with the corresponding data
        
        ---
        Pending: 
        - Make sprite editor gui program to make sprite editing easier, and make sprite data consistent and easy to read/write
        '''
        with open(self.sprite_data_file, 'r') as f:
            reading_block = False
            block_type = ''
            frame = []
            frame_line = 0
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    reading_block = True
                    block_type = line[1:-1]
                elif reading_block:
                    if line == '[block_end]':
                        reading_block = False
                        block_type = ''
                    elif block_type == 'dimensions':
                        self.dimensions = tuple(line.split(','))
                    elif block_type == 'animations':
                        anim_name, anim_data = line.split(':')
                        self.animations[anim_name] = list(anim_data.split(','))
                    elif block_type == 'sprite_data':
                        frame.append(line)
                        frame_line += 1
                        if frame_line == self.dimensions[1]:
                            self.sprite_data.append(frame)
                            frame = []
                            frame_line = 0
                    else:
                        EngineLogger.log("ERROR", f"Unknown block type in sprite data: {block_type}")
                        reading_block = False
                        block_type = ''

    def set_frame(self, frame_index: int):
        '''
        Sets the current frame of the sprite to the specified index
        '''
        if frame_index < 0 or frame_index >= len(self.sprite_data):
            EngineLogger.log("ERROR", f"Frame index {frame_index} out of bounds for sprite {self.sprite_data_file}")
            return
        self.current_frame = frame_index
        self.current_animation = None
        self.loop = False

    def play_animation(self, animation_name: str, loop: bool = False):
        '''
        Plays the specified animation by name, if it exists in the animations dictionary
        '''
        if animation_name not in self.animations:
            EngineLogger.log("ERROR", f"Animation {animation_name} not found in sprite {self.sprite_data_file}")
            return
        self.current_animation = animation_name
        self.current_frame = self.animations[animation_name][0]
        self.loop = loop

    def _update_animation(self):
        '''
        INTERNAL METHOD - DO NOT CALL DIRECTLY\n
        Updates the current frame of the animation if an animation is playing, only called by the rendering pipeline of the internal engine itself.
        '''
        if self.current_animation is None:
            return
        anim_frames = self.animations[self.current_animation]
        self.current_frame += 1
        if self.current_frame >= anim_frames[-1]:
            if self.loop:
                self.current_frame = anim_frames[0]
            else:
                self.current_frame = anim_frames[-1]

class GridMap:
    '''
    Class used to draw tiles to the screen in a grid mannner. The tilemap is a 2D array of tiles, each tile is part of a file that contains the tile data and usable color pallettes for the tile map.
    '''

    tileset_file = None #Reference to a file containing all the data of the tilemap
    tile_size: Tuple[int, int] = (0, 0) #Width and height of each tile in the tilemap
    tileset_data: list = [] #List containing the raw "pixel" data of the tilemap, each pixel is a number from 0 - 8, 0 is transparent and the other are an index in the color pallete
    x_offset: int = 0 #The x offset in pixels of the tilemap, used to offset the tilemap when drawing to the screen for scrolling effects
    y_offset: int = 0 #The y offset in pixels of the tilemap, used to offset the tilemap when drawing to the screen for scrolling effects
    gridmap: list = [] #The grid of the map, composed by a list of strings, where each character is a tile index in the tilemap_data list, used to draw the mapgrid to the screen, the mapgrid size can be grater then the screen tile capacity, in which case the mapgrid will be clipped to the screen size when drawing to the screen, and the x_offset and y_offset will be used to scroll the mapgrid around the screen

    def __init__(self, tileset_file: str):
        '''
        Class used to draw tiles to the screen in a grid mannner. The tilemap is a 2D array of tiles, each tile is part of a file that contains the tile data and usable color pallettes for the tile map.
        Each tile is conformed by a "hex byte" string, first character is the tile index (0 - 15 / #0 - #F), and the second is the color pallette index (0 - 15 / #0 - #F), all these are put togheter to make the rows of the gridmap.
        Each tile is a 2d pixel array, where each pixel is a number from 0 - 8, 0 is transparent and the other are an index in the color pallete, the color pallete is a list of 3 value tuples, where each value goes from 0 to 255, being RGB values for colors.
        '''
        self.tileset_file = tileset_file
        self._load_data()

    def _load_data(self):
        '''
        INTERNAL METHOD - DO NOT CALL DIRECTLY\n
        Loads the tilemap data from the tileset_file and fills the class attributes with the corresponding data
        
        ---
        Pending: 
        - Make tilemap editor gui program to make tilemap editing easier, and make tilemap data consistent and easy to read/write
        '''
        with open(self.tileset_file, 'r') as f:
            reading_block = False
            block_type = ''
            tile = []
            tile_line = 0
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    reading_block = True
                    block_type = line[1:-1]
                elif reading_block:
                    if line == '[block_end]':
                        reading_block = False
                        block_type = ''
                    elif block_type == 'dimensions':
                        self.dimensions = tuple(line.split(','))
                    elif block_type == 'tile_data':
                        tile.append(line)
                        tile_line += 1
                        if tile_line == self.dimensions[1]:
                            self.tileset_data.append(tile)
                            tile = []
                            tile_line = 0
                    else:
                        EngineLogger.log("ERROR", f"Unknown block type on tile data: {block_type}")
                        reading_block = False
                        block_type = ''

    def change_tileset(self, tileset_file: str):
        '''
        Changes the tileset of the tilemap to the specified tileset file, and reloads the tilemap data from the new tileset file.
        '''
        self.tileset_file = tileset_file
        self._load_data()

    def setup_gridmap(self, layer: int, size: Tuple[int, int], default_tile: str = '0', default_color_palette: str = '0'):
        '''
        Sets up the gridmap of the tilemap, creating a 2D array of tiles with the specified size, in tiles, and filling it with the default tile and default color palette. The gridmap is a list of strings, where each character is a tile index in the tilemap_data list, used to draw the mapgrid to the screen, the mapgrid size can be grater then the screen tile capacity, in which case the mapgrid will be clipped to the screen size when drawing to the screen, and the x_offset and y_offset will be used to scroll the mapgrid around the screen.
        '''
        self.gridmap = []
        for y in range(size[1]):
            row = ''
            for x in range(size[0]):
                row += default_tile + default_color_palette
            self.gridmap.append(row)
        self.layer = layer
        self.x_offset = 0
        self.y_offset = 0

    def set_tile(self, x: int, y: int, tile_index: str, color_palette_index: str):
        '''
        Sets the tile at the specified position in the gridmap to the specified tile index and color palette index.
        '''
        if y < 0 or y >= len(self.gridmap):
            EngineLogger.log("ERROR", f"Y position {y} out of bounds for gridmap")
            return
        if x < 0 or x >= len(self.gridmap[y]) / 2:
            EngineLogger.log("ERROR", f"X position {x} out of bounds for gridmap")
            return
        row = self.gridmap[y]
        self.gridmap[y] = row[:x] + tile_index + color_palette_index + row[x+2:]

class Screen:
    '''
    Class that manages the graphics rendering of the game engine. Handles basic drawing of different graphic types, as well as prosessing the layers and putting everythin togheter to output the images.
    '''

    dimensions: Tuple[int, int] = (0, 0) #The dimensions of the screen, used for internal engine rendering, modify to change the size of the screen
    layer_count: int = 0 #The number of layers the screen has, used for internal engine rendering, modify to change the number of layers
    video_memory: list = [] #The video memory of the screen, used for internal engine rendering. Do not modify this directly, use the provided methods to draw on the screen
    color_palettes: list = [] #The list of the color palettes of the game, each palette is a list of 3 value tuples, where each value goes from 0 to 255, being RGB values for colors
    loaded_color_palette: list = [] #The color palette currently in use by the screen, gets updated by itself when anything is drawn to the screen. Do not modify on it's own unless aware of what you doing
    final_frame: Image = None #The final frame that is outputted to the screen, used for internal engine rendering. Do not modify this directly, use the provided methods to draw on the screen
    final_frame_preprocess: list = [] #The final frame that is outputted to the screen, used for internal engine rendering. Do not modify this directly, use the provided methods to draw on the screen

    def __init__(self, dimensions: Tuple[int, int], layer_count: int):
        '''
        Class that manages the graphics rendering of the game engine. Handles basic drawing of different graphic types, as well as prosessing the layers and putting everythin togheter to output the images.
        '''
        self.dimensions = dimensions
        self.layer_count = layer_count
        self.video_memory = []
        for layer in range(self.layer_count):
            self.video_memory.append([])
            for y in range(self.dimensions[1]):
                self.video_memory[layer].append([])
                self.final_frame_preprocess[layer].append([])
                for x in range(self.dimensions[0]):
                    self.video_memory[layer][y].append((0, 0, 0, 0)) #Initialize the video memory with empty pixels
                    self.final_frame_preprocess[layer][y].append((0, 0, 0, 0)) #Initialize the final frame preprocess with empty pixels

    def clear_layer(self, layer: int):
        '''
        Clears the specified layer of the video memory, setting all pixels to transparent.
        '''
        if layer < 0 or layer >= self.layer_count:
            EngineLogger.log('ERROR', f'Layer {layer} out of bounds for screen with {self.layer_count} layers')
            return
        for y in range(self.dimensions[1]):
            for x in range(self.dimensions[0]):
                self.video_memory[layer][y][x] = (0, 0, 0, 0) #Set pixel to transparent

    def clear_screen(self):
        '''
        Clears all layers of the video memory, setting all pixels to transparent.
        '''
        for layer in range(self.layer_count):
            self.clear_layer(layer)

    def set_pixel(self, x: int, y: int, layer: int, color: Tuple[int, int, int, int]):
        '''
        Sets the pixel at the specified position in the specified layer to the specified color.
        '''
        if layer < 0 or layer >= self.layer_count:
            EngineLogger.log('ERROR', f'Layer {layer} out of bounds for screen with {self.layer_count} layers')
            return
        if x < 0 or x >= self.dimensions[0] or y < 0 or y >= self.dimensions[1]:
            EngineLogger.log('ERROR', f'Pixel position ({x}, {y}) out of bounds for screen with dimensions {self.dimensions}')
            return
        self.video_memory[layer][y][x] = color

    def draw_shape(self, shape: Literal['rectangle', 'circle'], x: int, y: int, layer: int, size: Tuple[int, int], color: Tuple[int, int, int, int]):
        '''
        Draws a shape on the specified layer of the video memory.
        '''
        if shape == 'rectangle':
            for dy in range(size[1]):
                for dx in range(size[0]):
                    self.set_pixel(x + dx, y + dy, layer, color)
        elif shape == 'circle':
            radius = size[0] // 2
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= radius * radius:
                        self.set_pixel(x + dx + radius, y + dy + radius, layer, color)
        else:
            EngineLogger.log('ERROR', f'Unknown shape type: {shape}')

    def draw_sprite(self, x: int, y: int, layer: int, sprite: Sprite):
        '''
        Draws a sprite on the specified layer of the video memory.
        '''
        if sprite.current_frame < 0 or sprite.current_frame >= len(sprite.sprite_data):
            EngineLogger.log('ERROR', f'Sprite {sprite.sprite_data_file} has no valid current frame to draw')
            return
        frame_data = sprite.sprite_data[sprite.current_frame]
        for row in range(sprite.dimensions[1]):
            for col in range(sprite.dimensions[0]):
                pixel_value = frame_data[row][col]
                if pixel_value != '0': # Assuming '0' is transparent
                    color_index = pixel_value #Indices start from 0
                    if color_index < 0 or color_index >= len(self.color_palettes[sprite.color_palette]):
                        EngineLogger.log('ERROR', f'Color index {color_index} out of bounds for sprite {sprite.sprite_data_file}')
                        continue
                    color = self.color_palettes[sprite.color_palette][color_index]
                    self.set_pixel(x + col, y + row, layer, (*color, 255)) # Assuming full opacity

    def draw_gridmap(self, x_offset: int, y_offset: int, layer: int, gridmap: GridMap):
        '''
        Draws a gridmap on the specified layer of the video memory.
        '''
        for y in range(len(gridmap.gridmap)):
            for x in range(len(gridmap.gridmap[y]) // 2):
                tile_index = gridmap.gridmap[y][x * 2]
                color_palette_index = gridmap.gridmap[y][x * 2 + 1]
                if tile_index < 0 or tile_index >= len(gridmap.tileset_data):
                    EngineLogger.log('ERROR', f'Tile index {tile_index} out of bounds for gridmap {gridmap.tileset_file}')
                    continue
                if color_palette_index < 0 or color_palette_index >= len(self.color_palettes):
                    EngineLogger.log('ERROR', f'Color palette index {color_palette_index} out of bounds for gridmap {gridmap.tileset_file}')
                    continue
                tile_data = gridmap.tileset_data[tile_index]
                color_palette = self.color_palettes[color_palette_index]
                for row in range(gridmap.tile_size[1]):
                    for col in range(gridmap.tile_size[0]):
                        pixel_value = tile_data[row][col]
                        if pixel_value != '0': # Assuming '0' is transparent
                            color_index = pixel_value #Indices start from 0
                            if color_index < 0 or color_index >= len(color_palette):
                                EngineLogger.log('ERROR', f'Color index {color_index} out of bounds for tile {tile_index} in gridmap {gridmap.tileset_file}')
                                continue
                            color = color_palette[color_index]
                            self.set_pixel(x_offset + x * gridmap.tile_size[0] + col, y_offset + y * gridmap.tile_size[1] + row, layer, (*color, 255)) # Assuming full opacity

    def render(self):
        '''
        Renders the final frame by compositing all layers in the video memory.
        '''
        self.final_frame = Image.new('RGBA', self.dimensions, (0, 0, 0, 0))
        for layer in range(self.layer_count):
            for y in range(self.dimensions[1]):
                for x in range(self.dimensions[0]):
                    pixel = self.video_memory[layer][y][x]
                    if pixel[3] > 0: # If alpha > 0
                        self.final_frame_preprocess[y][x] = pixel
        for y in range(self.dimensions[1]):
            for x in range(self.dimensions[0]):
                self.final_frame.putpixel((x, y), self.final_frame_preprocess[y][x])

class GameWindow:
    def __init__(self, game_name: str = 'Pyrcade Game'):
        self.root = tkinter.Tk()
        self.game_mainloop: callable #The game's mainloop as a callable to urn it when needed
        self.screen: Screen #The game's screen object, so it can be controlled inside the ui mainloop
        self.frame_wait: int
        self.last_time = time.perf_counter() #Time refence to check framerate and frametimes
        self.held_keys = set() #set of held keys at the moment

        self.canvas = tkinter.Canvas(self.root, highlightthickness = 0)
        self.canvas.pack(fill = 'both', expand = True)
        self.image_id = self.canvas.create_image(0, 0)

        self.root.bind('<KeyPress>', self._key_down)
        self.root.bind('<KeyRealease>', self._key_up)
        self.root.bind('<FocusOut>', self._clear_keys)
        self.root.protocol('WN_DELETE_WINDOW', self.root.destroy)
        self.game_name = game_name

        self.fps_frames = 0
        self.fps_started = time.perf_counter()

    def _key_down(self, event):
        self.held_keys.add(event.keysym)

    def _key_up(self, event):
        self.held_keys.discard(event.keysym)

    def _clear_keys(self, event):
        self.held_keys.clear()

    def _frame(self):
        self.fps_frames += 1
        now = time.perf_counter()
        elapsed = now - self.fps_started

        if elapsed >= 1.0:
            fps = self.fps_frames / elapsed
            self.root.title(f"My Game | {fps:.1f} FPS")
            self.fps_frames = 0
            self.fps_started = now

        now = time.perf_counter()
        delta = min(now - self.last_time, 0.1)
        self.last_time = now

        self.game_mainloop(delta, self.held_keys)

        self.screen.render()
        self.photo = ImageTk.PhotoImage(self.screen.final_frame)
        self.canvas.itemconfigure(self.image_id, image = self.photo)

        self.root.after(self.frame_wait, self._frame)

    def start(self):
        self.root.after(0, self._frame)
        self.root.mainloop()