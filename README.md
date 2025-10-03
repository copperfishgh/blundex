# Blundex - Chess Tactical Analysis Companion

**Blundex** is a real-time chess analysis tool designed to catch blunders and tactical oversights while you focus on strategy. It's not a chess engine opponent or referee - it's your tactical safety net.

## What Blundex Does

Blundex watches your chess games and uses minimal lookahead analysis to:

- ✅ **Warn about blunders** - "That move hangs your queen"
- ✅ **Spot missed opportunities** - "You can win a rook with Rxd7"
- ✅ **Prevent basic mistakes** - "Your king will be in check"
- ✅ **Count material** - "Free pawn on e5"
- ✅ **Catch simple tactics** - Forks, pins, skewers in 1-2 moves

## What Blundex Doesn't Do

- ❌ **Strategic evaluation** - No positional judgment or long-term planning
- ❌ **Deep calculation** - No extensive move tree searching
- ❌ **Play against you** - Not a chess opponent
- ❌ **Opening/endgame theory** - Focus is purely tactical

## The Philosophy

> *"Let me handle the strategy, you handle the blunders."*

Chess has two main components: **tactical accuracy** (not hanging pieces) and **strategic understanding** (planning, position evaluation). Most players want to develop their strategic thinking, but simple tactical oversights ruin games. Blundex handles the tactical bookkeeping so you can focus on the strategic art of chess.

## Current Status

**Fully Functional Chess Interface:**
- Complete chess rule implementation with all special moves
- Visual board with piece movement and highlighting
- Undo/redo system for position exploration
- Pawn promotion, castling, en passant support
- Board flipping and responsive design
- Checkmate/stalemate detection with visual effects

**Latest Features:**
- Pin and skewer detection with visual indicators (white circles with P/S letters)
- X-ray attack detection for comprehensive tactical analysis
- PGN file support (load and save games)
- Performance monitoring display (hover computation metrics)
- Statistics panel with red bold highlighting for hanging pieces
- Material-weighted hanging pieces system with value-based visual indicators
- Exchange evaluation system with hover-based tactical analysis
- Move preview system showing tactical consequences before committing
- Lichess-style last move highlighting for turn indication
- Dynamic keyboard shortcuts help panel with precise auto-sizing
- Persistent settings system for user preferences

**Still Needed for Full Blundex Vision:**
- Additional tactical helpers (forks, discovered attacks)
- Strategic helper system (text analysis under board)
- Real-time position analysis engine

## Running Blundex

```bash
pip install -r requirements.txt
python main.py
```

**Controls:**
- **Mouse** - Drag and drop pieces with square snapping, hover over pieces for tactical analysis
- **F** - Flip board perspective
- **U** - Undo last move
- **R** - Redo move
- **H** - Toggle hanging pieces helper
- **E** - Toggle exchange evaluation helper
- **Ctrl+O** - Open PGN file
- **Ctrl+S** - Save game to PGN file
- **~** - Reset game to starting position
- **/** - Show/hide keyboard shortcuts help panel
- **ESC** - Exit game (or close help panel if open)

**Visual Features:**
- **Drag-and-Drop Movement** - Smooth piece dragging with automatic square snapping
- **Last Move Highlighting** - Green overlay on from/to squares (lichess-style)
- **Pin Indicators** - White circles with 'P' mark pinned pieces (absolute and relative pins)
- **Skewer Indicators** - White circles with 'S' mark skewered pieces
- **Consistent Visual Indicators** - Clear 4px borders for all hanging pieces
- **Exchange Analysis** - Yellow triangles mark capturable pieces, orange highlights show attackers/defenders
- **X-ray Attacks** - Hover detection includes attacks through pieces (queen behind rook, etc.)
- **Move Preview** - Real-time tactical analysis when dragging over legal moves
- **Statistics Display** - Organized panel showing hanging, attacked, developed pieces, pawn stats, and activity
- **Performance Metrics** - Top-left corner shows hover computation time (rolling 30-sample average)
- **Dynamic Help Panel** - Press / for pixel-perfect auto-sized keyboard shortcuts overlay
- **Performance Optimized** - Annotations only compute when entering different legal squares
- **Persistent Settings** - Helper preferences saved between sessions

## Technical Requirements

- **Python 3.x** with Pygame for graphics
- **Optional**: NumPy for enhanced sound generation

For technical architecture and development details, see [CLAUDE.md](CLAUDE.md).

## Analysis System Design

Blundex separates chess analysis into two distinct helper categories with **granular user control**:

### Helper Selection Interface
**Checkbox panel to the right of the chess board:**
- Individual checkboxes for each tactical and strategic helper
- Only checked helpers are active in analysis
- Settings persist across program sessions (saved to config file)
- Allows progressive learning and customized experience

**UI Layout:**
```
┌─────────────────┬─────────────────────┐
│                 │ TACTICAL HELPERS    │
│                 │ ☑ Hanging Pieces    │
│                 │ ☑ Exchange Evaluation│
│   CHESS BOARD   │ ☐ Immediate Threats │
│                 │ ☐ Simple Forks      │
│                 │ ☐ Pins & Skewers    │
│                 │ ☐ Material Wins     │
│                 │                     │
│                 │ STRATEGIC HELPERS   │
│                 │ ☐ Weak Pawns        │
│─────────────────│ ☐ Open Files        │
│ [Flip]    [/?]  │ ☐ Outpost Squares   │
│                 │ ☐ Pawn Breaks       │
│ Strategic Text: │ ☐ Passed Pawns      │
│ • Analysis here │                     │
└─────────────────┴─────────────────────┘
```

### 🔴 Tactical Helpers (Checkbox Controlled)
**Visual annotations directly on the chess board:**

**Hanging Pieces (Implemented):**
- Clear visual indicators with consistent border thickness for all pieces
- Red borders for your hanging pieces (danger), green for opponent's (opportunity)
- Consistent 4px border thickness - piece value is obvious from the piece itself
- Player-perspective colors that work correctly with board flipping

**Exchange Evaluation (Implemented):**
- Yellow triangle indicators mark tactically interesting pieces that can be captured
- Hover investigation shows orange highlighting of all attacking and defending pieces
- Human-evaluated tactical analysis without computer calculation
- High-performance caching system prevents lag during mouse movement
- Integrated with hanging pieces system for complete tactical awareness

**Implemented Tactical Helpers:**
- **Pins** - Detects both absolute pins (to king) and relative pins (to valuable pieces)
- **Skewers** - Identifies high-value pieces attacked with lower-value pieces behind (excludes pawns)
- **X-ray Attacks** - Shows all attackers including those behind other pieces on the same line

**Future Tactical Helpers:**
- **Immediate Threats** - Warning symbols for mate in 1, checks
- **Simple Tactics** - Highlight forks and discovered attacks
- **Material Wins** - Show squares where you can capture for free
- **Blunder Prevention** - Block moves that hang material

**Drag-and-Drop System (Implemented):**
- **Smooth Piece Movement**: Click and drag pieces with automatic square snapping
- **Real-time Preview**: As you drag over legal squares, see tactical consequences instantly
- **Performance Optimized**: Annotations only recalculate when entering different legal destinations
- **Visual Feedback**: Piece centers itself in current square, legal moves highlighted
- **Complete Integration**: Works seamlessly with all helpers and board flipping

**Move Preview System (Implemented):**
- **Preview Board State**: Creates temporary board state with candidate move executed
- **Real-time Helper Updates**: Hanging pieces indicators update to show post-move position
- **Complete Tactical Awareness**: See which pieces would be hanging after your move before committing

*Critical alerts that prevent immediate material loss or checkmate*

### 🔵 Strategic Helpers (Optional Checkbox)
**Text analysis panel under the board:**

**Pawn Structure Analysis:**
- **Weak Pawns** - Isolated, backward, doubled pawns
- **Pawn Breaks** - Suggest pawn advances like c5 to challenge center
- **Passed Pawns** - Identify advancement opportunities

**Positional Features:**
- **Open Files** - Available files for rook placement
- **Outpost Squares** - Strong squares protected by pawns, unreachable by enemy pawns
- **Piece Coordination** - Suggestions for better piece placement

**Example Strategic Output:**
```
Strategic Analysis:
• Backward pawn on d6 needs attention - consider c5 break
• Open g-file available for your rook
• Knight outpost available on e5 square
• Weak kingside pawn structure after h6
```

## Vision: The Perfect Chess Assistant

**Tactical Layer:** *"STOP! That hangs your queen!"* (Red board annotation)
**Strategic Layer:** *"Consider: Open d-file available"* (Blue text suggestion)

You make the strategic decisions. Blundex prevents the tactical oversights and suggests positional improvements.


---

*A tool for chess players who want to improve their strategic thinking without worrying about hanging pieces.*