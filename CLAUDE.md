# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
python main.py    # Run the application
```

**Dependencies**: Python 3.x + Pygame (required), NumPy (optional for sound)

## Architecture

### Core Module Structure

**main.py** - Application entry point and main game loop
- Initializes Pygame and creates the main window
- Handles all user input (keyboard shortcuts, mouse events)
- Manages drag-and-drop piece movement system
- Controls animation timing and rendering optimization

**chess_board.py** - Complete chess game logic and state management
- `BoardState` class: Comprehensive chess position tracking
- Full chess rules implementation including castling, en passant, pawn promotion
- Legal move generation with check validation
- Undo/redo system with 50-move history limit
- Bitboard-optimized mega-loop for tactical analysis (pins, skewers, pawn patterns)
- X-ray attack detection for comprehensive attacker/defender analysis
- Caching system for hanging pieces and exchange evaluation
- FEN and PGN support for position representation and game import/export

**display.py** - Visual rendering and user interface
- `ChessDisplay` class: All graphical output and UI components
- Board rendering with coordinate system and piece positioning
- Pin and skewer indicators (white circles with P/S letters)
- Statistics display panel with organized tactical metrics
- Performance monitoring display (hover computation timing)
- Helper panel with configurable tactical assistance options
- Drag-and-drop visual feedback and move preview system
- Animation system for checkmate/stalemate effects
- Settings persistence using JSON configuration files

**config.py** - Configuration constants and settings
- `GameConfig`: Window sizing and layout percentages
- `Colors`: Complete color scheme for board and UI elements
- `AudioConfig`: Sound system configuration
- `GameConstants`: Chess piece values and game constants

**sound_manager.py** - Audio system management
- Sound generation using NumPy or system fallbacks
- Error sound feedback for invalid moves
- Cross-platform audio support with graceful degradation

### Key Design Patterns

**Modular Architecture**: Clear separation between game logic, display, and configuration
**Caching System**: Performance optimization for tactical analysis (hanging pieces, exchange evaluation)
**Event-Driven Input**: Comprehensive keyboard shortcuts and mouse interaction system
**Settings Persistence**: User preferences saved to `.blundex` configuration file
**Graceful Degradation**: Fallbacks for missing dependencies (NumPy, audio system)

### Asset Management

The `pngs/2x/` directory contains chess piece images in the format `{color}{piece}.png`:
- Colors: `w` (white), `b` (black)
- Pieces: `P` (pawn), `R` (rook), `N` (knight), `B` (bishop), `Q` (queen), `K` (king)
- Example: `wK.png` (white king), `bQ.png` (black queen)

### Helper System Implementation

**Settings Persistence**: User preferences saved to `.blundex` JSON file
**Performance**: Helpers use cached computation for tactical analysis
**UI Integration**: Checkbox-based controls in right panel (`display.py:draw_help_panel`)

### Development Notes

- Dependencies managed via requirements.txt (Pygame + python-chess)
- Direct Python execution with standard library + Pygame
- Cross-platform Windows/Linux/macOS compatibility
- Memory-efficient with move history limits and caching systems
- Optimized rendering with smart redraw detection
- Performance monitoring for tactical computation optimization

### Important Implementation Details

**Tactical Analysis**: Bitboard-optimized mega-loop in `_compute_board_analysis()` detects pins, skewers, and pawn patterns
**X-ray Detection**: `_get_attackers()` temporarily removes pieces to reveal attacks through blocking pieces
**Pin Detection**: Custom implementation detects both absolute pins (to king) and relative pins (to valuable pieces)
**Skewer Detection**: Identifies high-value pieces with lower-value pieces behind (excludes pawns as targets)
**Caching Systems**: `BoardState._update_hanging_pieces_cache()` and `_update_exchange_cache()` for performance
**PGN Support**: Uses python-chess library for game import/export functionality
**Coordinate Systems**: Display coordinates vs board coordinates, with flipping logic in `display.py`
**Event Handling**: Main game loop in `main.py` handles all input with smart redraw detection
**State Management**: Comprehensive undo/redo system with deep copying in `chess_board.py`
**Performance Tracking**: `display.py` monitors hover computation time with rolling average display

For user features and application overview, see [README.md](README.md).