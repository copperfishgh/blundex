# RESTRUCTURE PLAN - Mega-Loop Board Analysis
## Draft 2 (Bitboard-Optimized) - FINAL

This document outlines the plan to consolidate all board analysis into a single-pass mega-loop that eliminates redundant square iterations **AND** leverages python-chess bitboard operations for maximum performance.

### Changes from Draft 1 → Draft 2
1. **Iterate `board.occupied`** instead of `chess.SQUARES` (25 vs 64 iterations)
2. **Keep SquareSet objects** instead of converting to Python `set()` for O(1) operations
3. **Use FILE_MASKS** for instant pawn file queries via bitboard AND operations
4. **Bitboard rank masks** for passed pawn detection (single mask check vs nested loops)
5. **Removed `by_file` dictionary** - use bitboard operations directly
6. **Simplified pin detection** - use `board.is_pinned()` only (no relative pins)
7. **Use bitboard `~self.board.pawns`** to exclude pawns from pin checks

**See BITBOARD_ANALYSIS.md for detailed rationale**

### Python-Chess Caching Behavior
**Important:** Python-chess does NOT cache results for expensive operations like `attackers()` or `is_pinned()`. They are computed fresh each time. This validates our mega-loop caching strategy as highly valuable.

---

## Current Problem

Multiple methods iterate over all 64 squares independently:
- `get_hanging_pieces()` - iterates squares, checks attackers/defenders
- `count_attacked_pieces()` - iterates squares, checks attackers
- `get_pinned_pieces()` - iterates squares, checks attackers + ray-casting
- `count_pawns()` - iterates squares
- `count_backward_pawns()` - iterates squares, checks adjacent files
- `count_isolated_pawns()` - iterates squares, checks adjacent files
- `count_doubled_pawns()` - iterates squares, checks same file
- `count_passed_pawns()` - iterates squares, checks files -1,0,+1

**Estimated redundancy: 60-75%**

Additionally, Draft 1 identified these bitboard optimization opportunities:
- Iterating all 64 squares instead of only occupied squares (~25 pieces)
- Converting SquareSet to Python `set()`, losing O(1) bitboard operations
- Manual dictionary tracking for pawn files instead of bitboard FILE_MASKS

---

## Proposed Solution: Bitboard-Optimized Mega-Loop

### High-Level Structure

```python
class BoardState:
    def __init__(self):
        # Analysis cache - computed once per position
        self._analysis = None

    def _invalidate_analysis(self):
        """Called after any move to invalidate cached analysis"""
        self._analysis = None

    def _compute_board_analysis(self):
        """
        BITBOARD-OPTIMIZED MEGA-LOOP: Single pass through occupied squares using
        python-chess bitboard operations for maximum performance.

        KEY OPTIMIZATIONS:
        1. Iterate board.occupied (~25 pieces) instead of chess.SQUARES (64)
        2. Keep SquareSet objects for O(1) bitboard operations
        3. Use FILE_MASKS for instant pawn file-based queries

        Returns a dictionary containing all computed board metrics.
        """

        # ============================================================
        # SECTION 1: INITIALIZATION
        # Initialize all result containers that will be populated
        # ============================================================

        analysis = {
            # Attack information (used by: hanging, attacked, pins)
            # BITBOARD NOTE: Store SquareSet directly, not Python set()
            'attack_map': {},  # square -> (attackers_SquareSet, defenders_SquareSet)

            # Piece lists by color (used by: all statistics)
            'white_pieces': [],
            'black_pieces': [],

            # Hanging pieces (used by: get_hanging_pieces, hanging statistic)
            'white_hanging': [],
            'black_hanging': [],

            # Attacked pieces (used by: count_attacked_pieces, attacked statistic)
            'white_attacked': [],
            'black_attacked': [],

            # Pinned pieces (used by: get_pinned_pieces, pin indicator display)
            'white_pinned': [],
            'black_pinned': [],

            # Skewered pieces (used by: get_skewered_pieces, skewer indicator display)
            'white_skewered': [],
            'black_skewered': [],

            # Pawn structure (used by: all pawn statistics)
            # BITBOARD NOTE: Will use bitboard SquareSets for pawn analysis
            'pawn_structure': {
                chess.WHITE: {
                    'all': [],        # All pawn squares
                    'backward': [],
                    'isolated': [],
                    'doubled': [],
                    'passed': []
                },
                chess.BLACK: {
                    'all': [],
                    'backward': [],
                    'isolated': [],
                    'doubled': [],
                    'passed': []
                }
            },

            # Development tracking (used by: count_developed_pieces)
            'white_developed': [],
            'black_developed': []
        }

        # ============================================================
        # SECTION 2: FIRST PASS - BASIC PIECE INFORMATION
        # Iterate ONLY occupied squares using bitboard operations
        #
        # BITBOARD OPTIMIZATION: board.occupied is a SquareSet (~25 pieces)
        # This eliminates ~40 wasted iterations on empty squares!
        # ============================================================

        for square in self.board.occupied:  # BITBOARD: Only ~25 iterations, not 64!
            piece = self.board.piece_at(square)

            # No need for empty square check - board.occupied only has pieces!

            # --- Store piece location ---
            if piece.color == chess.WHITE:
                analysis['white_pieces'].append(square)
            else:
                analysis['black_pieces'].append(square)

            # --- Compute attack information (EXPENSIVE - do once!) ---
            # This is used by: hanging pieces, attacked pieces, pin detection
            enemy_color = not piece.color

            # BITBOARD OPTIMIZATION: Keep as SquareSet, don't convert to set()!
            # SquareSet provides O(1) len() via popcount on bitboard
            attackers = self.board.attackers(enemy_color, square)  # Returns SquareSet
            defenders = self.board.attackers(piece.color, square)   # Returns SquareSet

            # Store SquareSet directly (not set()!) for fast bitboard operations
            analysis['attack_map'][square] = (attackers, defenders)

            # --- Check if piece is hanging (IMMEDIATE USE of attack info) ---
            # A piece is hanging if: attacked AND (undefended OR defenders < attackers)
            # BITBOARD OPTIMIZATION: len() on SquareSet is O(1) popcount!
            if len(attackers) > 0:
                if len(defenders) == 0 or len(attackers) > len(defenders):
                    if piece.color == chess.WHITE:
                        analysis['white_hanging'].append(square)
                    else:
                        analysis['black_hanging'].append(square)

            # --- Check if piece is attacked (IMMEDIATE USE of attack info) ---
            # A piece is attacked if enemy pieces attack it (even if defended)
            if len(attackers) > 0:
                if piece.color == chess.WHITE:
                    analysis['white_attacked'].append(square)
                else:
                    analysis['black_attacked'].append(square)

            # --- Check development (only for initial position pieces) ---
            # Knights on b1/g1 (white) or b8/g8 (black) are undeveloped
            # Bishops on c1/f1 (white) or c8/f8 (black) are undeveloped
            rank = chess.square_rank(square)

            if piece.piece_type == chess.KNIGHT:
                if piece.color == chess.WHITE:
                    if rank != 0:  # Not on first rank = developed
                        analysis['white_developed'].append(square)
                else:  # BLACK
                    if rank != 7:  # Not on eighth rank = developed
                        analysis['black_developed'].append(square)

            elif piece.piece_type == chess.BISHOP:
                if piece.color == chess.WHITE:
                    if rank != 0:  # Not on first rank = developed
                        analysis['white_developed'].append(square)
                else:  # BLACK
                    if rank != 7:  # Not on eighth rank = developed
                        analysis['black_developed'].append(square)

        # ============================================================
        # SECTION 3: PIN AND SKEWER DETECTION
        # Pins: Use python-chess's optimized is_pinned() function
        # Skewers: Detect using ray-tracing with piece value comparison
        #
        # BITBOARD OPTIMIZATION: Use BB_RAYS and between() for O(1) ray ops
        # ============================================================

        for color in [chess.WHITE, chess.BLACK]:
            enemy_color = not color

            # BITBOARD: Get all non-pawn pieces for this color using bitboard operations
            color_pieces = self.board.occupied_co[color]
            non_pawn_pieces = color_pieces & ~self.board.pawns  # Exclude pawns

            # --- PIN DETECTION (use built-in method) ---
            for square in non_pawn_pieces:
                # Use python-chess's optimized pin detection (uses bitboards internally)
                if self.board.is_pinned(color, square):
                    if color == chess.WHITE:
                        analysis['white_pinned'].append(square)
                    else:
                        analysis['black_pinned'].append(square)

            # --- SKEWER DETECTION (custom implementation) ---
            # Skewers are "reverse pins": valuable piece in front, less valuable behind
            # Only sliding pieces (B/R/Q) can create skewers

            enemy_sliding_pieces = (
                self.board.occupied_co[enemy_color] &
                (self.board.bishops | self.board.rooks | self.board.queens)
            )

            for attacker_square in enemy_sliding_pieces:
                # Get all squares this sliding piece attacks
                attacked_squares = self.board.attacks(attacker_square)

                # Check each attacked piece of our color
                for attacked_square in (attacked_squares & color_pieces):
                    attacked_piece = self.board.piece_at(attacked_square)

                    # Skip pawns (not considered skewerable)
                    if attacked_piece.piece_type == chess.PAWN:
                        continue

                    # BITBOARD: Get full ray between attacker and attacked piece (O(1))
                    ray = chess.BB_RAYS[attacker_square][attacked_square]

                    # Look for pieces behind the attacked piece on the same ray
                    # Iterate squares beyond the attacked piece
                    for behind_square in chess.SquareSet(ray):
                        # Skip the attacker and attacked squares
                        if behind_square in (attacker_square, attacked_square):
                            continue

                        # Only check squares beyond the attacked piece
                        # (Further from attacker than attacked piece)
                        if chess.square_distance(attacker_square, behind_square) <= \
                           chess.square_distance(attacker_square, attacked_square):
                            continue

                        behind_piece = self.board.piece_at(behind_square)

                        # Found a piece behind?
                        if behind_piece and behind_piece.color == color:
                            # Check if it's a valid skewer (front >= back in value)
                            # OR if front piece is king (absolute skewer)
                            front_value = GameConstants.PIECE_VALUES[attacked_piece.piece_type]
                            back_value = GameConstants.PIECE_VALUES[behind_piece.piece_type]

                            is_skewer = (front_value >= back_value or
                                       attacked_piece.piece_type == chess.KING)

                            if is_skewer:
                                # BITBOARD: Verify no pieces between front and back (O(1))
                                between_squares = chess.between(attacked_square, behind_square)
                                if not any(self.board.piece_at(sq) for sq in between_squares):
                                    # Valid skewer detected!
                                    if color == chess.WHITE:
                                        analysis['white_skewered'].append(attacked_square)
                                    else:
                                        analysis['black_skewered'].append(attacked_square)
                                    break  # Only need first skewer on this ray

        # ============================================================
        # SECTION 4: PAWN STRUCTURE ANALYSIS
        # Analyze all pawns using BITBOARD operations for maximum speed
        #
        # BITBOARD OPTIMIZATION: Use board.pawns bitboard and FILE_MASKS
        # for instant file-based queries instead of manual dictionary tracking
        # ============================================================

        # BITBOARD: Get all pawns as bitboard SquareSets (instant!)
        white_pawns = self.board.pawns & self.board.occupied_co[chess.WHITE]
        black_pawns = self.board.pawns & self.board.occupied_co[chess.BLACK]

        # BITBOARD: Pre-compute file masks for instant file-based queries
        # FILE_MASKS[i] = bitboard with all squares on file i set
        FILE_MASKS = [chess.BB_FILES[i] for i in range(8)]

        # --- Process each color's pawns ---
        for color in [chess.WHITE, chess.BLACK]:
            enemy_color = not color
            promotion_direction = 1 if color == chess.WHITE else -1

            # BITBOARD: Get pawn bitboard for this color
            pawn_bitboard = white_pawns if color == chess.WHITE else black_pawns
            enemy_pawn_bitboard = black_pawns if color == chess.WHITE else white_pawns

            # Iterate only the pawns (not all 64 squares!)
            for square in pawn_bitboard:
                rank = chess.square_rank(square)
                file = chess.square_file(square)

                # Store in 'all' list
                analysis['pawn_structure'][color]['all'].append(square)

                # --- Check DOUBLED (multiple pawns on same file) ---
                # BITBOARD OPTIMIZATION: Instant check using bitwise AND + popcount
                pawns_on_this_file = pawn_bitboard & FILE_MASKS[file]
                if chess.popcount(pawns_on_this_file) > 1:
                    analysis['pawn_structure'][color]['doubled'].append(square)

                # --- Check ISOLATED (no friendly pawns on adjacent files) ---
                # BITBOARD OPTIMIZATION: Check adjacent files with bitwise OR + AND
                left_file_mask = FILE_MASKS[file - 1] if file > 0 else 0
                right_file_mask = FILE_MASKS[file + 1] if file < 7 else 0
                adjacent_files_mask = left_file_mask | right_file_mask

                # Instant check: any friendly pawns on adjacent files?
                if not (pawn_bitboard & adjacent_files_mask):
                    analysis['pawn_structure'][color]['isolated'].append(square)

                # --- Check BACKWARD (can't advance safely, no support) ---
                # A pawn is backward if:
                # 1. Has adjacent pawns (not isolated)
                # 2. All adjacent friendly pawns are ahead (can't provide support)
                # 3. Can't safely advance

                # Only check if pawn has adjacent pawns (not isolated)
                if pawn_bitboard & adjacent_files_mask:
                    can_be_supported = False
                    all_adjacent_ahead = True

                    # Check pawns on adjacent files using bitboards
                    for adj_file in [file - 1, file + 1]:
                        if not (0 <= adj_file < 8):
                            continue

                        # BITBOARD: Get adjacent file pawns instantly
                        adj_file_pawns = pawn_bitboard & FILE_MASKS[adj_file]

                        for adj_square in adj_file_pawns:
                            adj_rank = chess.square_rank(adj_square)

                            # Check if adjacent pawn is behind (can provide support)
                            if color == chess.WHITE:
                                if adj_rank <= rank:
                                    can_be_supported = True
                                if adj_rank >= rank:
                                    all_adjacent_ahead = False
                            else:  # BLACK
                                if adj_rank >= rank:
                                    can_be_supported = True
                                if adj_rank <= rank:
                                    all_adjacent_ahead = False

                    # Backward if all adjacent pawns ahead and can't be supported
                    if all_adjacent_ahead and not can_be_supported:
                        analysis['pawn_structure'][color]['backward'].append(square)

                # --- Check PASSED (no enemy pawns blocking promotion path) ---
                # BITBOARD OPTIMIZATION: Build mask of squares that block this pawn
                # and check if any enemy pawns occupy those squares

                # Build mask for "passed pawn check zone" (3 files, ranks ahead)
                check_files_mask = adjacent_files_mask | FILE_MASKS[file]

                # Build rank mask for all squares ahead of this pawn
                if color == chess.WHITE:
                    # Mask all ranks above current rank
                    ahead_mask = 0
                    for r in range(rank + 1, 8):
                        ahead_mask |= chess.BB_RANKS[r]
                else:  # BLACK
                    # Mask all ranks below current rank
                    ahead_mask = 0
                    for r in range(0, rank):
                        ahead_mask |= chess.BB_RANKS[r]

                # Combine: check zone is intersection of file mask and ahead mask
                check_zone_mask = check_files_mask & ahead_mask

                # BITBOARD: Instant check - any enemy pawns in check zone?
                if not (enemy_pawn_bitboard & check_zone_mask):
                    analysis['pawn_structure'][color]['passed'].append(square)

        # ============================================================
        # SECTION 5: RETURN COMPLETED ANALYSIS
        # ============================================================

        return analysis

    # ============================================================
    # PUBLIC API METHODS
    # These methods provide the same interface as before,
    # but now just return pre-computed results
    # ============================================================

    def _ensure_analysis(self):
        """Lazy computation: only compute analysis when first needed"""
        if self._analysis is None:
            self._analysis = self._compute_board_analysis()

    def get_hanging_pieces(self, color: bool) -> List[int]:
        """Return pre-computed hanging pieces for given color"""
        self._ensure_analysis()
        return self._analysis['white_hanging' if color == chess.WHITE else 'black_hanging']

    def count_hanging_pieces(self, color: bool) -> int:
        """Return count of hanging pieces"""
        return len(self.get_hanging_pieces(color))

    def count_attacked_pieces(self, color: bool) -> int:
        """Return count of attacked pieces"""
        self._ensure_analysis()
        attacked = self._analysis['white_attacked' if color == chess.WHITE else 'black_attacked']
        return len(attacked)

    def get_pinned_pieces(self, color: bool) -> List[int]:
        """Return pre-computed pinned pieces for given color"""
        self._ensure_analysis()
        return self._analysis['white_pinned' if color == chess.WHITE else 'black_pinned']

    def get_skewered_pieces(self, color: bool) -> List[int]:
        """Return pre-computed skewered pieces for given color"""
        self._ensure_analysis()
        return self._analysis['white_skewered' if color == chess.WHITE else 'black_skewered']

    def count_pawns(self, color: bool) -> int:
        """Return count of pawns"""
        self._ensure_analysis()
        return len(self._analysis['pawn_structure'][color]['all'])

    def count_backward_pawns(self, color: bool) -> int:
        """Return count of backward pawns"""
        self._ensure_analysis()
        return len(self._analysis['pawn_structure'][color]['backward'])

    def count_isolated_pawns(self, color: bool) -> int:
        """Return count of isolated pawns"""
        self._ensure_analysis()
        return len(self._analysis['pawn_structure'][color]['isolated'])

    def count_doubled_pawns(self, color: bool) -> int:
        """Return count of doubled pawns"""
        self._ensure_analysis()
        return len(self._analysis['pawn_structure'][color]['doubled'])

    def count_passed_pawns(self, color: bool) -> int:
        """Return count of passed pawns"""
        self._ensure_analysis()
        return len(self._analysis['pawn_structure'][color]['passed'])

    def count_developed_pieces(self, color: bool) -> int:
        """Return count of developed pieces"""
        self._ensure_analysis()
        developed = self._analysis['white_developed' if color == chess.WHITE else 'black_developed']
        return len(developed)

    # ============================================================
    # MOVE METHODS - Must invalidate analysis
    # ============================================================

    def make_move(self, from_square, to_square) -> bool:
        """Make a move and invalidate analysis cache"""
        # ... existing move logic ...
        success = # ... move execution ...
        if success:
            self._invalidate_analysis()  # CRITICAL: invalidate after move
        return success

    def undo_move(self) -> bool:
        """Undo a move and invalidate analysis cache"""
        # ... existing undo logic ...
        success = # ... undo execution ...
        if success:
            self._invalidate_analysis()  # CRITICAL: invalidate after undo
        return success
```

---

## Expected Performance Improvements

### Mega-Loop Benefits (Draft 1)
1. **Eliminated redundant iterations**: From ~10 separate loops to 1 mega-loop
2. **Attack computation**: From N calls to `board.attackers()` to 1 pass
3. **Pawn analysis**: From 4 separate passes to 1 pass with file-based organization
4. **Pin detection**: Uses cached attack data instead of recomputing

**Mega-loop speedup: 3-5x**

### Bitboard Optimizations (Draft 2)
1. **Iterate board.occupied**: ~25 piece iterations instead of 64 square iterations (2.5x fewer)
2. **SquareSet operations**: O(1) popcount instead of O(n) Python len() on sets
3. **FILE_MASKS for pawns**: Instant bitwise AND for file queries instead of dictionary lookups
4. **Passed pawn detection**: Single bitboard mask check instead of nested loops
5. **No set() conversions**: Keep SquareSet throughout for bitboard performance

**Additional bitboard speedup: 3-4x**

**Combined estimated speedup: 10-15x for full board analysis**

---

## Migration Strategy

1. Add `_compute_board_analysis()` mega-loop method
2. Add `_ensure_analysis()` lazy computation wrapper
3. Modify existing public methods to use cached results
4. Add `_invalidate_analysis()` calls to all move methods
5. Test thoroughly to ensure behavioral equivalence
6. Remove old implementation once verified

---

## Implementation Checklist

- [ ] Implement `_compute_board_analysis()` mega-loop in chess_board.py
- [ ] Add `_ensure_analysis()` lazy computation wrapper
- [ ] Modify existing public methods to use cached results
- [ ] Add `_invalidate_analysis()` calls to all move methods (make_move, undo_move, redo_move)
- [ ] Test thoroughly to ensure behavioral equivalence with current code
- [ ] Profile performance to measure actual speedup
- [ ] Verify all edge cases (endgames with few pieces, pawn-heavy positions)

## Tactical Pattern Detection: Performance Analysis

### ✅ **X-ray Attacks: USE OFFICIAL IMPLEMENTATION**

**Python-chess ships production-ready X-ray detection** in `examples/xray_attacks.py` using **magic bitboard lookup tables**.

**Key insight**: Uses `BB_RANK_ATTACKS`, `BB_FILE_ATTACKS`, `BB_DIAG_ATTACKS` for O(1) performance:

```python
# Official approach - O(1) magic bitboard lookups:
chess.BB_RANK_ATTACKS[square][occupied_bitboard]
chess.BB_FILE_ATTACKS[square][occupied_bitboard]
chess.BB_DIAG_ATTACKS[square][occupied_bitboard]
```

**Implementation strategy**: Adapt official code from python-chess examples directory. X-rays can be computed OUTSIDE the mega-loop as a separate pass since they require modified occupancy bitboards.

**Performance**: O(1) per sliding piece using pre-calculated lookup tables.

### ⚠️ **Skewers: Adaptable from Pin Detection**

Skewers are "reverse pins" - valuable piece in front, less valuable behind. Similar algorithm to pins but with opposite value ordering.

**Implementation strategy**:
- Use same ray-tracing logic as pin detection
- Check piece values: `front_value >= back_value`
- Use `chess.BB_RAYS[from][to]` for full ray
- Use `chess.between(sq1, sq2)` to verify no blockers

**Performance**: Similar to pin detection - O(n) where n = number of sliding pieces. Could be added to SECTION 3 of mega-loop.

### ❌ **Forks: EXPENSIVE - Requires Legal Move Generation**

**Fork detection requires making/unmaking EVERY legal move** to check attacks:

```python
for move in board.legal_moves:  # ~30-40 moves per position
    board.push(move)              # Make move
    attacked = board.attacks(move.to_square)  # Check attacks
    board.pop()                   # Unmake move
```

**Performance cost**: ~30-40x more expensive than mega-loop because:
1. Legal move generation itself is expensive
2. Must make/unmake each move (full position state change)
3. Must compute attacks for each candidate move

**Recommendation**: Implement forks ONLY if needed for UI display. Consider engine integration (Stockfish) for tactical evaluation instead.

### Performance Comparison Table

| Pattern | Complexity | Can Integrate in Mega-Loop? | Performance Impact |
|---------|-----------|------------------------------|-------------------|
| Hanging pieces | O(n) pieces | ✅ Yes (SECTION 2) | Baseline |
| Attacked pieces | O(n) pieces | ✅ Yes (SECTION 2) | Baseline |
| Pins | O(n) pieces | ✅ Yes (SECTION 3) | ~1.2x baseline |
| **Skewers** | O(n) sliding pieces | ✅ Yes (SECTION 3) | ~1.3x baseline |
| Pawns (all types) | O(n) pawns | ✅ Yes (SECTION 4) | ~1.5x baseline |
| **X-rays** | O(1) per piece | ⚠️ Separate method | ~1.2x baseline |
| ~~Forks~~ | ~~O(m) legal moves~~ | ❌ NOT IMPLEMENTED | ~~30-40x baseline~~ |

**Mega-loop with pins + skewers + pawns**: ~2-3x slower than baseline (still fast!)
**Fork detection**: Abandoned due to 30-40x cost - too expensive for real-time use

### Recommended Implementation Order

1. **Phase 1**: Implement mega-loop with hanging, attacked, pins, skewers, pawns (CURRENT PLAN)
2. **Phase 2**: Add X-ray detection as separate method using official implementation
3. **Phase 3**: ~~Fork detection~~ - ABANDONED (too expensive for real-time use)

### Critical Bitboard Primitives Discovered

The tactical pattern research revealed these efficient operations:

```python
# Magic bitboard lookup tables (O(1) - FAST!)
chess.BB_RANK_ATTACKS[square][occupied]
chess.BB_FILE_ATTACKS[square][occupied]
chess.BB_DIAG_ATTACKS[square][occupied]

# Ray operations (O(1) - FAST!)
chess.BB_RAYS[from_square][to_square]  # Full ray between squares
chess.between(square1, square2)         # Squares between (excludes endpoints)

# Bitboard masks (O(1) - already using these)
chess.BB_RANK_MASKS[square]
chess.BB_FILE_MASKS[square]
chess.BB_DIAG_MASKS[square]
```

These should be preferred over manual ray-casting in all implementations.
