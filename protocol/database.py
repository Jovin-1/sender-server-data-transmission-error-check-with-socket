"""
database.py
===========
Database Component
Simulates persistent storage as a 2D array (grid of fixed-size blocks).

Architecture:
  - Storage is modelled as a ROWS × COLS grid of bytes.
  - Each cell = one storage "block" (default 16 bytes).
  - Blocks are allocated row-by-row, left-to-right (sequential allocation).
  - A free-block bitmap tracks which cells are occupied.

Public API (called by Middleman):
  check_space(size_bytes)  → (bool, free_blocks_needed)
  write_data(data)         → (bool, list_of_allocated_cell_addresses)
  get_usage_report()       → dict with capacity stats
  display_grid()           → prints a visual map of the storage grid
"""

from __future__ import annotations
import math
from protocol.protocol_states import DatabaseState, Signal
from protocol import logger as L


class Database:
    """
    2D array storage simulation.

    Parameters
    ----------
    rows       : int  – Number of rows in the storage grid
    cols       : int  – Number of columns (blocks per row)
    block_size : int  – Bytes per block (default 16)
    name       : str  – Friendly label for log messages
    """

    def __init__(
        self,
        rows: int = 8,
        cols: int = 8,
        block_size: int = 16,
        name: str = "DATABASE",
    ) -> None:
        self.rows        = rows
        self.cols        = cols
        self.block_size  = block_size
        self.name        = name
        self.state       = DatabaseState.IDLE

        # 2D storage grid: grid[row][col] = bytearray(block_size)
        # None means the block is free.
        self.grid: list[list[bytearray | None]] = [
            [None] * cols for _ in range(rows)
        ]

        # Allocation bitmap: True = block is occupied
        self.occupied: list[list[bool]] = [
            [False] * cols for _ in range(rows)
        ]

        L.log(self.name, f"Initialized  {rows}×{cols} grid "
              f"| block_size={block_size}B "
              f"| total_capacity={rows * cols * block_size}B")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(self, new_state: DatabaseState) -> None:
        old = self.state
        self.state = new_state
        L.log(self.name, f"State  {old.name} → {new_state.name}", "STATE")

    @property
    def total_blocks(self) -> int:
        return self.rows * self.cols

    @property
    def free_blocks(self) -> int:
        return sum(
            1 for r in range(self.rows) for c in range(self.cols)
            if not self.occupied[r][c]
        )

    @property
    def used_blocks(self) -> int:
        return self.total_blocks - self.free_blocks

    def _blocks_needed(self, size_bytes: int) -> int:
        """Ceiling-divide bytes by block_size."""
        return math.ceil(size_bytes / self.block_size)

    def _find_free_blocks(self, n: int) -> list[tuple[int, int]]:
        """
        Return addresses [(row, col), …] of n consecutive free blocks
        (row-major order). Returns empty list if insufficient space.
        """
        found: list[tuple[int, int]] = []
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.occupied[r][c]:
                    found.append((r, c))
                    if len(found) == n:
                        return found
        return []   # not enough free blocks

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_space(self, size_bytes: int) -> tuple[Signal, int]:
        """
        Query whether the DB can hold `size_bytes` of data.

        Called by Middleman in response to a DB_QUERY signal.

        Returns
        -------
        (Signal.DB_OK,   blocks_needed)  if space is sufficient
        (Signal.DB_FULL, blocks_needed)  if space is insufficient
        """
        self._transition(DatabaseState.QUERIED)
        blocks_needed = self._blocks_needed(size_bytes)

        L.log(self.name,
              f"Storage query received  | need={blocks_needed} blocks "
              f"| free={self.free_blocks}/{self.total_blocks} blocks "
              f"| data_size={size_bytes}B")

        self._transition(DatabaseState.RESPONDING)

        if self.free_blocks >= blocks_needed:
            L.log(self.name,
                  f"Space available ✔  ({self.free_blocks} free ≥ {blocks_needed} needed)",
                  "SUCCESS")
            self._transition(DatabaseState.IDLE)
            return Signal.DB_OK, blocks_needed
        else:
            L.log(self.name,
                  f"Insufficient space ✘  "
                  f"({self.free_blocks} free < {blocks_needed} needed)",
                  "ERROR")
            self._transition(DatabaseState.ERROR)
            return Signal.DB_FULL, blocks_needed

    def write_data(self, data: bytes) -> tuple[Signal, list[tuple[int, int]]]:
        """
        Write `data` into the 2D storage grid block-by-block.

        Called by Middleman after EDC validation passes.

        Returns
        -------
        (Signal.DB_WRITE_OK, [(row,col), …])  on success
        (Signal.DB_FULL,     [])              on failure
        """
        self._transition(DatabaseState.WRITING)
        blocks_needed = self._blocks_needed(len(data))
        addresses     = self._find_free_blocks(blocks_needed)

        if not addresses:
            L.log(self.name, "Write failed: no free blocks!", "ERROR")
            self._transition(DatabaseState.ERROR)
            return Signal.DB_FULL, []

        # Write data chunks into each allocated block
        for idx, (r, c) in enumerate(addresses):
            chunk_start = idx * self.block_size
            chunk_end   = chunk_start + self.block_size
            chunk       = data[chunk_start:chunk_end]

            # Pad last block with zeros if shorter than block_size
            block_data              = bytearray(self.block_size)
            block_data[:len(chunk)] = chunk

            self.grid[r][c]      = block_data
            self.occupied[r][c]  = True

        L.log(self.name,
              f"Data written successfully  | {len(data)}B across "
              f"{blocks_needed} block(s)  | addresses={addresses}",
              "SUCCESS")
        self._transition(DatabaseState.DONE)
        return Signal.DB_WRITE_OK, addresses

    def get_usage_report(self) -> dict:
        """Return a dict summarising current storage utilisation."""
        return {
            "total_blocks"     : self.total_blocks,
            "used_blocks"      : self.used_blocks,
            "free_blocks"      : self.free_blocks,
            "total_capacity_B" : self.total_blocks  * self.block_size,
            "used_capacity_B"  : self.used_blocks   * self.block_size,
            "free_capacity_B"  : self.free_blocks   * self.block_size,
            "utilisation_pct"  : round(self.used_blocks / self.total_blocks * 100, 1),
        }

    def display_grid(self) -> None:
        """
        Print a visual ASCII map of the storage grid.
        '░░' = free block,  '██' = occupied block.
        """
        print()
        header = "  " + "  ".join(f"C{c}" for c in range(self.cols))
        print(f"  {L.BOLD}Storage Grid [{self.rows}×{self.cols}]  "
              f"block_size={self.block_size}B{L.RESET}")
        print(f"  {header}")
        for r in range(self.rows):
            row_label = f"R{r}"
            cells = "  ".join(
                f"{L.MAGENTA}██{L.RESET}" if self.occupied[r][c]
                else f"{L.GREY}░░{L.RESET}"
                for c in range(self.cols)
            )
            print(f"  {row_label}  {cells}")
        report = self.get_usage_report()
        print(f"\n  Used: {report['used_capacity_B']}B / "
              f"{report['total_capacity_B']}B  "
              f"({report['utilisation_pct']}%)\n")
