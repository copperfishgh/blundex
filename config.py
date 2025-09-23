"""
Configuration module for the Chess Game

This module contains all constants, settings, and configuration values
used throughout the application.
"""

class GameConfig:
    """Main game configuration settings"""

    # Window and display settings
    SCREEN_SIZE_PERCENTAGE = 0.75  # 75% of screen dimensions
    WINDOW_ASPECT_RATIO = 1.4      # Wider to accommodate help panel
    BOARD_SIZE_PERCENTAGE = 0.85   # 85% of smaller window dimension
    BOARD_MARGIN_PERCENTAGE = 0.07 # 7% margin from edges

    # Button settings
    BUTTON_WIDTH_PERCENTAGE = 0.35  # 35% of window width
    BUTTON_HEIGHT_PERCENTAGE = 0.08 # 8% of window height
    BUTTON_Y_PERCENTAGE = 0.9       # 90% down from top

    # Help checkbox settings
    HELP_PANEL_WIDTH_PERCENTAGE = 0.35  # 35% of window width for help panel
    HELP_PANEL_MARGIN_PERCENTAGE = 0.02 # 2% margin between board and help panel
    CHECKBOX_SIZE_PERCENTAGE = 0.025    # 2.5% of window width for checkbox size
    CHECKBOX_SPACING_PERCENTAGE = 0.05  # 5% of window height between checkboxes

    # Font sizes (as percentage of board size)
    FONT_LARGE_PERCENTAGE = 0.09   # 9% of board size
    FONT_MEDIUM_PERCENTAGE = 0.06  # 6% of board size
    FONT_SMALL_PERCENTAGE = 0.045  # 4.5% of board size
    FONT_BUTTON_PERCENTAGE = 0.035  # 3.5% of window width (smaller button font)

class Colors:
    """Color constants for the game"""

    # Basic RGB colors
    RGB_WHITE = (255, 255, 255)
    RGB_BLACK = (0, 0, 0)

    # Chess board colors
    LIGHT_SQUARE = (240, 217, 181)  # Light brown
    DARK_SQUARE = (181, 136, 99)    # Dark brown

    # Last move highlighting colors (lichess-style)
    LIGHT_SQUARE_LAST_MOVE = (205, 210, 106)  # Light green overlay on light squares
    DARK_SQUARE_LAST_MOVE = (170, 162, 58)    # Dark green overlay on dark squares

    # UI highlight colors
    HIGHLIGHT = (255, 255, 0)       # Yellow for highlights
    SELECTED = (160, 160, 160)      # Neutral grey for selected square

    # Button colors
    BUTTON_BACKGROUND_COLOR = (100, 100, 100)
    BUTTON_HOVER_COLOR = (150, 150, 150)
    BUTTON_TEXT_COLOR = (255, 255, 255)

    # Text colors
    BLACK_TEXT = (0, 0, 0)

    # Board annotation colors (neutral, warning, caution, positive)
    ANNOTATION_NEUTRAL = (128, 128, 128)     # Light grey for neutral/informational
    ANNOTATION_WARNING = (255, 0, 0)        # Red for strong warnings
    ANNOTATION_CAUTION = (255, 255, 0)      # Yellow for awareness/caution
    ANNOTATION_POSITIVE = (0, 255, 0)       # Green for good/positive

    # UI Panel colors
    HELP_PANEL_BACKGROUND = (250, 250, 250) # Light grey panel background
    CHECKBOX_SHADOW = (200, 200, 200)       # Checkbox shadow
    CHECKBOX_UNCHECKED_BG = (248, 248, 248) # Checkbox unchecked background
    CHECKBOX_BORDER_UNCHECKED = (180, 180, 180) # Border when unchecked
    LABEL_TEXT_COLOR = (60, 60, 60)         # Dark grey for labels

    # Table colors for statistics
    TABLE_BORDER = (220, 220, 220)          # Faint gray for cell borders
    TABLE_FAVORABLE_BG = (230, 255, 230)    # More pronounced green background
    TABLE_UNFAVORABLE_BG = (255, 230, 230)  # More pronounced red background
    TABLE_NEUTRAL_BG = (250, 250, 250)      # Light gray for neutral rows

    # Game status colors
    STATUS_CHECK = (255, 0, 0)              # Red for check
    STATUS_CHECKMATE = (255, 0, 0)          # Red for checkmate
    STATUS_NORMAL = (0, 128, 0)             # Green for normal moves
    STALEMATE_TEXT = (255, 0, 0)            # Red for stalemate text
    STALEMATE_OUTLINE = (0, 0, 0)           # Black outline for stalemate

    # Piece placeholder colors
    PIECE_BORDER = (100, 100, 100)          # Grey border for piece placeholders

class AudioConfig:
    """Audio system configuration"""

    # Pygame mixer settings
    FREQUENCY = 22050
    SIZE = -16
    CHANNELS = 2
    BUFFER = 512

    # Error beep settings
    BEEP_FREQUENCY = 800   # 800Hz beep
    BEEP_DURATION = 300    # 300ms duration

    # Animation settings
    FADE_DURATION = 0.01   # 10ms fade in/out

class AnimationConfig:
    """Animation timing and settings"""

    # Move animation
    MOVE_INDICATOR_RADIUS_FACTOR = 0.25  # Radius as factor of square size

class GameConstants:
    """Chess game constants"""

    BOARD_SIZE = 8
    UNDO_HISTORY_LIMIT = 50  # Maximum moves to keep for undo

    # File paths
    PIECE_IMAGE_DIRECTORY = "pngs/2x/"

    # Piece size factors
    PAWN_SIZE_FACTOR = 0.65     # Pawns are 65% of square size
    PIECE_SIZE_FACTOR = 0.75    # Other pieces are 75% of square size

    # Standard chess piece values for material evaluation
    PIECE_VALUES = {
        'P': 1,    # Pawn
        'N': 3,    # Knight
        'B': 3,    # Bishop
        'R': 5,    # Rook
        'Q': 9,    # Queen
        'K': 0     # King (invaluable/special case)
    }