import datetime, tkinter, time
from typing import Literal, Callable
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

    def _close(self):
        self.log('ENGINE', 'logger closed...')
        self.logfile.close()

EngineLogger = Logger()
EngineLogger.log("ENGINE", "Engine logger initialized")

sprites: list = [] # Internal list that holds a reference to all the sprites that are created, used to update animations via the rendering pipeline

class Sprite:
    '''
    Base graphical class, used to create sprites and animated sprites for the game engine
    '''
    sprite_data_file: str
    dimensions: tuple[int, int]
    animations: dict
    current_animation: str
    current_frame: int
    loop: bool
    color_palette: int
    sprite_data: list
    sprite_index: int
    anim_step: int
    
    def __init__(self, sprite_data_file: str):
        '''
        Base graphical class, used to create sprites and animated sprites for the game engine
        '''
        self.sprite_data_file = sprite_data_file #Reference to a file containing all the data of the sprite
        self.dimensions = (0, 0) #Width and height of the sprite
        self.animations = {} #Dictionary containing all the animation data of the sprite
        self.current_animation = None #The name of the current animation being played
        self.current_frame = -1 #The index of the current frame being displayed
        self.loop = False #Whether the animation should loop or not
        self.color_palette = 0 #Index in the color palette list of the game
        self.sprite_data = [] #List containing the raw "pixel" data of the sprite, each pixel is a number from 0 - 8, 0 is transparent and the other are an index in the color pallete
        self.anim_step = 0

        global sprites
        sprites.append(self)
        self.sprite_index = len(sprites) - 1 #The index of the current sprite being displayed, used for internal engiine shenanigans, do not touch this unless you know what you are doing
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
                line: str = line.strip()
                if line.startswith('[') and line.endswith(']') and not reading_block:
                    block_type = line[1:-1]
                    reading_block = True
                elif reading_block:
                    if line == '[end]':
                        reading_block = False
                        block_type = ''
                    elif block_type == 'size':
                        self.dimensions = tuple(int(i) for i in line.split(','))
                    elif block_type == 'animation':
                        anim_name, anim_data = line.split(':')
                        self.animations[anim_name] = [int(i) for i in anim_data.split(',')]
                    elif block_type == 'data':
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
        self.anim_step = 0
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
        self.anim_step += 1
        if self.anim_step >= len(anim_frames):
            if self.loop:
                self.anim_step = 0
            else:
                self.anim_step = len(anim_frames) - 1
        self.current_frame = anim_frames[self.anim_step]

class GridMap:
    '''
    Class used to draw tiles to the screen in a grid mannner. The tilemap is a 2D array of tiles, each tile is part of a file that contains the tile data and usable color pallettes for the tile map.
    '''

    tileset_file: str
    dimensions: tuple[int, int]
    tileset_data: list[list[str]]
    x_offset: int
    y_offset: int
    gridmap: list[str]
    map_size: tuple[int, int]

    def __init__(self, tileset_file: str, map_size: tuple[int, int]):
        '''
        Class used to draw tiles to the screen in a grid mannner. The tilemap is a 2D array of tiles, each tile is part of a file that contains the tile data and usable color pallettes for the tile map.
        Each tile is conformed by a "hex byte" string, first character is the tile index (0 - 15 / #0 - #F), and the second is the color pallette index (0 - 15 / #0 - #F), all these are put togheter to make the rows of the gridmap.
        Each tile is a 2d pixel array, where each pixel is a number from 0 - 8, 0 is transparent and the other are an index in the color pallete, the color pallete is a list of 3 value tuples, where each value goes from 0 to 255, being RGB values for colors.
        '''
        self.tileset_file = tileset_file #Reference to a file containing all the data of the tilemap
        self.dimensions = (0, 0) #Width and height of each tile in the tilemap
        self.tileset_data = [] #List containing the raw "pixel" data of the tilemap, each pixel is a number from 0 - 8, 0 is transparent and the other are an index in the color pallete
        self.x_offset = 0 #The x offset in pixels of the tilemap, used to offset the tilemap when drawing to the screen for scrolling effects
        self.y_offset = 0 #The y offset in pixels of the tilemap, used to offset the tilemap when drawing to the screen for scrolling effects
        self.gridmap = [] #The grid of the map, composed by a list of strings, where each character is a tile index in the tilemap_data list, used to draw the mapgrid to the screen, the mapgrid size can be grater then the screen tile capacity, in which case the mapgrid will be clipped to the screen size when drawing to the screen, and the x_offset and y_offset will be used to scroll the mapgrid around the screen
        self.map_size = map_size
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
                if line.startswith('[') and line.endswith(']') and not reading_block:
                    reading_block = True
                    block_type = line[1:-1]
                elif reading_block:
                    if line == '[end]':
                        reading_block = False
                        block_type = ''
                    elif block_type == 'size':
                        self.dimensions = tuple(int(i) for i in line.split(','))
                    elif block_type == 'data':
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
        self.tileset_data = []
        self._load_data()

    def setup_gridmap(self, layer: int, default_tile: str = '0', default_color_palette: str = '0'):
        '''
        Sets up the gridmap of the tilemap, creating a 2D array of tiles with the specified size, in tiles, and filling it with the default tile and default color palette. The gridmap is a list of strings, where each character is a tile index in the tilemap_data list, used to draw the mapgrid to the screen, the mapgrid size can be grater then the screen tile capacity, in which case the mapgrid will be clipped to the screen size when drawing to the screen, and the x_offset and y_offset will be used to scroll the mapgrid around the screen.
        '''
        self.gridmap = []
        for y in range(self.map_size[1]):
            row = ''
            for x in range(self.map_size[0]):
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
        self.gridmap[y] = row[:(x*2)] + tile_index + color_palette_index + row[(x*2)+2:]

class Screen:
    '''
    Class that manages the graphics rendering of the game engine. Handles basic drawing of different graphic types, as well as prosessing the layers and putting everythin togheter to output the images.
    '''
    dimensions: tuple[int, int]
    layer_count: int
    video_memory: list[list[list[tuple[int, int, int, int]]]]
    color_palettes: list[list[tuple[int, int, int]]]
    loaded_color_palette: list[tuple[int, int, int]]
    final_frame: Image.Image
    
    def __init__(self, dimensions: tuple[int, int], layer_count: int, color_palettes_file: str = None):
        '''
        Class that manages the graphics rendering of the game engine. Handles basic drawing of different graphic types, as well as prosessing the layers and putting everythin togheter to output the images.
        '''
        self.dimensions = dimensions #The dimensions of the screen, used for internal engine rendering, modify to change the size of the screen
        self.layer_count = layer_count #The number of layers the screen has, used for internal engine rendering, modify to change the number of layers
        self.video_memory = [] #The video memory of the screen, used for internal engine rendering. Do not modify this directly, use the provided methods to draw on the screen
        self.color_palettes = [] #The list of the color palettes of the game, each palette is a list of 3 value tuples, where each value goes from 0 to 255, being RGB values for colors
        self.loaded_color_palette = [] #The color palette currently in use by the screen, gets updated by itself when anything is drawn to the screen. Do not modify on it's own unless aware of what you doing
        
        for layer in range(self.layer_count):
            self.video_memory.append([])
            for y in range(self.dimensions[1]):
                self.video_memory[layer].append([])
                for x in range(self.dimensions[0]):
                    self.video_memory[layer][y].append((0, 0, 0, 0)) #Initialize the video memory with empty pixels

        if color_palettes_file is None:
            EngineLogger.log('ENGINE', 'no color palettes file set up on the screen object, exiting...')
            err = ValueError('No color palettes file path provided when one was expected')
            err.add_note('No color palettes file path provided when one was expected')
            raise err

        self._load_color_palettes(color_palettes_file)
            
    def _load_color_palettes(self, path):
        '''
        INTERNAL METHOD - DO NOT CALL DIRECTLY
        Loads the color palettes for the game from a file.
        '''
        with open(path, 'r') as file:
            palettes = []
            for line in file:
                line = line.strip()
                if not line:
                    continue
                palette = []
                for color in line.split(';'):
                    if not color.strip():
                        continue
                    color_values = tuple(int(value) for value in color.split(','))
                    palette.append(color_values)
                palettes.append(palette)
            self.color_palettes = palettes

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

    def set_pixel(self, x: int, y: int, layer: int, color: tuple[int, int, int, int]):
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

    def draw_shape(self, shape: Literal['rectangle', 'circle'], x: int, y: int, layer: int, size: tuple[int, int], color: tuple[int, int, int, int]):
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
        if sprite.color_palette < 0 or sprite.color_palette >= len(self.color_palettes):
            EngineLogger.log('ERROR', f'Color palette index {sprite.color_palette} out of bounds for sprite {sprite.sprite_data_file}')
            return
        frame_data = sprite.sprite_data[sprite.current_frame]
        for row in range(sprite.dimensions[1]):
            for col in range(sprite.dimensions[0]):
                pixel_value = frame_data[row][col]
                if pixel_value != '0': # Assuming '0' is transparent
                    color_index = int(pixel_value) #Indices start from 0
                    if color_index < 0 or color_index >= len(self.color_palettes[sprite.color_palette]):
                        EngineLogger.log('ERROR', f'Color index {color_index} out of bounds for sprite {sprite.sprite_data_file}')
                        continue
                    color = self.color_palettes[sprite.color_palette][color_index]
                    self.set_pixel(x + col, y + row, layer, (*color[:3], 255)) # Assuming full opacity

    def draw_gridmap(self, x_offset: int, y_offset: int, layer: int, gridmap: GridMap):
        '''
        Draws a gridmap on the specified layer of the video memory.
        '''
        for y in range(len(gridmap.gridmap)):
            for x in range(len(gridmap.gridmap[y]) // 2):
                tile_index = int(gridmap.gridmap[y][x * 2], 16)
                color_palette_index = int(gridmap.gridmap[y][x * 2 + 1], 16)
                if tile_index < 0 or tile_index >= len(gridmap.tileset_data):
                    EngineLogger.log('ERROR', f'Tile index {tile_index} out of bounds for gridmap {gridmap.tileset_file}')
                    continue
                if color_palette_index < 0 or color_palette_index >= len(self.color_palettes):
                    EngineLogger.log('ERROR', f'Color palette index {color_palette_index} out of bounds for gridmap {gridmap.tileset_file}')
                    continue
                tile_data = gridmap.tileset_data[tile_index]
                color_palette = self.color_palettes[color_palette_index]
                for row in range(gridmap.dimensions[1]):
                    for col in range(gridmap.dimensions[0]):
                        pixel_value = tile_data[row][col]
                        if pixel_value != '0': # Assuming '0' is transparent
                            color_index = int(pixel_value) #Indices start from 0
                            if color_index < 0 or color_index >= len(color_palette):
                                EngineLogger.log('ERROR', f'Color index {color_index} out of bounds for tile {tile_index} in gridmap {gridmap.tileset_file}')
                                continue
                            color = color_palette[color_index]
                            self.set_pixel(x_offset + x * gridmap.dimensions[0] + col, y_offset + y * gridmap.dimensions[1] + row, layer, (*color[:3], 255)) # Assuming full opacity

    def render(self):
        '''
        Renders the final frame by compositing all layers in the video memory.
        '''
        width, height = self.dimensions
        preprocess = [(0, 0, 0, 0)] * (width * height)
        self.final_frame = Image.new('RGBA', self.dimensions, (0, 0, 0, 0))
        for layer in range(self.layer_count):
            for y in range(height):
                for x in range(width):
                    if self.video_memory[layer][y][x][3] != 0:
                        preprocess[(width * y) + x] = self.video_memory[layer][y][x]
        self.final_frame.putdata(preprocess)

class GameWindow:
    def __init__(self, game_name: str = 'Pyrcade Game', framerate: int = 60, gameloop: Callable = None, screen: Screen = None):
        self.succesfulsetup = False
        if gameloop is None or screen is None:
            EngineLogger.log('ENGINE', 'tryed to create game instance with no mainloop or screen assigned, setup failed')
            return
        self.root = tkinter.Tk()
        self.game_mainloop = gameloop #The game's mainloop as a callable to urn it when needed
        self.screen: Screen = screen #The game's screen object, so it can be controlled inside the ui mainloop
        self.frame_wait: int = 1000 // framerate
        self.last_time = time.perf_counter() #Time refence to check framerate and frametimes
        self.held_keys = set() #set of held keys at the moment

        self.canvas = tkinter.Canvas(self.root, highlightthickness = 0)
        self.canvas.pack(fill = 'both', expand = True)
        self.image_id = self.canvas.create_image(0, 0, anchor = 'nw')

        self.root.bind('<KeyPress>', self._key_down)
        self.root.bind('<KeyRelease>', self._key_up)
        self.root.bind('<FocusOut>', self._clear_keys)
        self.root.protocol('WM_DELETE_WINDOW', self._end)
        self.game_name = game_name

        self.fps_frames = 0
        self.fps_started = time.perf_counter()
        self.succesfulsetup = True

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
            self.root.title(f"{self.game_name} | {fps:.1f} FPS")
            self.fps_frames = 0
            self.fps_started = now

        delta = min(now - self.last_time, 0.1)
        self.last_time = now

        self.game_mainloop(delta, self.held_keys)

        self.screen.render()
        self.photo = ImageTk.PhotoImage(self.screen.final_frame)
        self.canvas.itemconfigure(self.image_id, image = self.photo)

        global sprites
        for sprite in sprites:
            sprite._update_animation()
        
        self.root.after(self.frame_wait, self._frame)

    def start(self):
        EngineLogger.log('ENGINE', 'initializing game instance startup')
        if not self.succesfulsetup:
            EngineLogger.log('ENGINE', 'game instance was not correctly setup, canceling startup')
            return
        self.root.after(0, self._frame)
        self.root.mainloop()

    def _end(self):
        self.root.destroy()
        EngineLogger._close()