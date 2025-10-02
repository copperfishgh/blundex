# Python-Chess Bitboard Performance Analysis

## Key Python-Chess Functions (Bitboard-Based)

### **Attack/Defense Functions** (What we're currently using)
```python
board.attackers(color, square) -> SquareSet  # Returns bitboard as SquareSet
board.is_attacked_by(color, square) -> bool  # Fast bitboard operation
board.is_pinned(color, square) -> bool       # Fast bitboard operation
```

### **Piece Location Functions** (Bitboard-based)
```python
board.pieces(piece_type, color) -> SquareSet  # All pieces of type/color (BITBOARD!)
board.pawns                                    # Bitboard of all pawns
board.knights                                  # Bitboard of all knights
board.bishops                                  # Bitboard of all bishops
board.rooks                                    # Bitboard of all rooks
board.queens                                   # Bitboard of all queens
board.kings                                    # Bitboard of all kings

# Color-specific bitboards
board.occupied_co[chess.WHITE]  # Bitboard of all white pieces
board.occupied_co[chess.BLACK]  # Bitboard of all black pieces
```

### **SquareSet Operations** (Bitboard wrapper)
```python
# SquareSet is python-chess's bitboard wrapper - VERY FAST!
square_set = board.pieces(chess.PAWN, chess.WHITE)

# Iteration (still fast - iterates set bits only)
for square in square_set:
    # Iterates only occupied squares, not all 64!

# Bitwise operations (FASTEST)
white_pawns = board.pawns & board.occupied_co[chess.WHITE]
black_pawns = board.pawns & board.occupied_co[chess.BLACK]

# Count (instant - counts set bits)
num_pawns = len(square_set)  # O(1) operation!

# Membership test (instant)
if square in square_set:  # O(1) bitboard operation
```

---

## Current Pseudo-Code Issues

### ❌ **Problem 1: Iterating All Squares**
```python
# SLOW - iterates all 64 squares
for square in chess.SQUARES:
    piece = self.board.piece_at(square)
    if not piece:
        continue  # Wasted iteration on 40+ empty squares!
```

### ✅ **Better: Use Bitboards**
```python
# FAST - only iterates occupied squares (typically 20-32 pieces)
for square in board.occupied:  # SquareSet of all pieces
    piece = board.piece_at(square)
    # No empty square checks needed!
```

---

### ❌ **Problem 2: Manual Pawn File Tracking**
```python
# SLOW - building dictionaries manually
pawn_structure = {
    'by_file': {}
}
for square in chess.SQUARES:
    piece = self.board.piece_at(square)
    if piece and piece.piece_type == chess.PAWN:
        file = chess.square_file(square)
        # Manual dictionary management...
```

### ✅ **Better: Use Bitboard Masks**
```python
# FAST - direct bitboard operations
white_pawns = board.pawns & board.occupied_co[chess.WHITE]

# Check file instantly with bitboard mask
FILE_MASKS = [chess.BB_FILES[i] for i in range(8)]

for file_idx in range(8):
    pawns_on_file = white_pawns & FILE_MASKS[file_idx]
    if chess.popcount(pawns_on_file) > 1:
        # Doubled pawns - found instantly!
```

---

### ❌ **Problem 3: Converting to Lists/Sets**
```python
attackers = self.board.attackers(enemy_color, square)  # Returns SquareSet
attackers_set = set(attackers)  # Converting to Python set - SLOW!
defenders_set = set(defenders)

# Later: len(attackers_set)
```

### ✅ **Better: Keep as SquareSet**
```python
attackers = self.board.attackers(enemy_color, square)  # SquareSet (bitboard)
defenders = self.board.attackers(piece.color, square)   # SquareSet (bitboard)

# Direct operations on SquareSet - uses bitboard operations internally
if len(attackers) > len(defenders):  # O(1) popcount
    # Hanging!
```

---

## Recommended Rewrite Strategy

### **Use Bitboard-First Approach**

```python
def _compute_board_analysis(self):
    """Bitboard-optimized mega-loop"""

    analysis = {
        # Store bitboards where possible, convert to lists only when needed
        'white_hanging': [],
        'black_hanging': [],
        'white_pinned': [],
        'black_pinned': [],
        # ... etc
    }

    # ===== SECTION 1: Iterate occupied squares only =====
    # FAST: Only iterates 20-32 pieces, not 64 squares
    for square in self.board.occupied:
        piece = self.board.piece_at(square)

        # Attack computation (already returns bitboard SquareSet)
        attackers = self.board.attackers(not piece.color, square)
        defenders = self.board.attackers(piece.color, square)

        # Fast bitboard operations
        if len(attackers) > 0 and len(attackers) > len(defenders):
            if piece.color == chess.WHITE:
                analysis['white_hanging'].append(square)
            else:
                analysis['black_hanging'].append(square)

    # ===== SECTION 2: Pawn analysis with bitboards =====
    # Get all pawns as bitboards
    white_pawns = self.board.pawns & self.board.occupied_co[chess.WHITE]
    black_pawns = self.board.pawns & self.board.occupied_co[chess.BLACK]

    # File masks for instant file-based queries
    FILE_MASKS = [chess.BB_FILES[i] for i in range(8)]

    # Check each file for doubled pawns (8 iterations, not 64!)
    for file_idx in range(8):
        white_on_file = white_pawns & FILE_MASKS[file_idx]
        if chess.popcount(white_on_file) > 1:
            # Doubled! Add all pawns on this file
            for square in white_on_file:
                analysis['white_doubled'].append(square)

    # Isolated pawns - check adjacent files with bitboard operations
    for square in white_pawns:
        file = chess.square_file(square)

        # Check adjacent files with bitboard operations
        left_file = FILE_MASKS[file-1] if file > 0 else 0
        right_file = FILE_MASKS[file+1] if file < 7 else 0
        adjacent_mask = left_file | right_file

        # Instant check: are there any white pawns on adjacent files?
        if not (white_pawns & adjacent_mask):
            analysis['white_isolated'].append(square)

    return analysis
```

---

## Performance Comparison

### **Current Approach (Lists/Sets)**
```python
# Iterate all 64 squares
for square in chess.SQUARES:  # 64 iterations
    piece = self.board.piece_at(square)
    if not piece: continue  # ~40 wasted checks

    attackers = set(self.board.attackers(...))  # Convert to Python set
    # len(attackers) - O(n) in Python
```
**Cost**: 64 iterations × (piece check + potential set conversion)

### **Bitboard Approach**
```python
# Iterate only occupied squares
for square in self.board.occupied:  # ~25 iterations
    piece = self.board.piece_at(square)

    attackers = self.board.attackers(...)  # Keep as SquareSet
    # len(attackers) - O(1) popcount on bitboard
```
**Cost**: ~25 iterations × bitboard operations

**Speedup: ~3-4x** just from iteration reduction + bitboard ops

---

## Bitboard Operations Reference

```python
# Bitwise AND - intersection
white_pawns = board.pawns & board.occupied_co[chess.WHITE]

# Bitwise OR - union
adjacent_files = FILE_MASKS[3] | FILE_MASKS[4]

# Bitwise NOT - complement
empty_squares = ~board.occupied

# Population count - number of set bits
num_pieces = chess.popcount(board.occupied)  # O(1)!

# Check if any bits set
if white_pawns & FILE_MASKS[4]:  # Any pawns on file E?

# Shift operations (for pawn advancement checks)
one_square_ahead = chess.shift_up(white_pawns)  # All pawns pushed forward
```

---

## Recommendation for Draft 2

1. **Replace `for square in chess.SQUARES`** → **`for square in board.occupied`**
2. **Keep attack results as SquareSet** instead of converting to `set()`
3. **Use bitboard file masks** for pawn analysis instead of dictionaries
4. **Use `board.pieces(type, color)`** instead of manual filtering
5. **Add bitboard operation comments** to explain the speed benefit

This will give us the mega-loop benefits PLUS bitboard performance!

---

## Example: Fully Optimized Hanging Piece Detection

```python
# OLD (current pseudo-code)
for square in chess.SQUARES:  # 64 iterations
    piece = self.board.piece_at(square)
    if not piece:
        continue
    attackers = set(self.board.attackers(not piece.color, square))
    defenders = set(self.board.attackers(piece.color, square))
    if len(attackers) > len(defenders):
        ...

# NEW (bitboard-optimized)
for square in self.board.occupied:  # ~25 iterations
    piece = self.board.piece_at(square)
    attackers = self.board.attackers(not piece.color, square)  # SquareSet
    defenders = self.board.attackers(piece.color, square)       # SquareSet
    if len(attackers) > len(defenders):  # O(1) popcount
        ...
```

**Result: ~3x faster** from this one change alone!
