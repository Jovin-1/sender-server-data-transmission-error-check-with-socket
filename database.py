# database.py
"""
In‑memory 2‑D array "database" with block‑level reservation.
"""
import math
from typing import List, Optional

from config import BLOCK_SIZE, TOTAL_BLOCKS


class Database:
    """Simple block‑based storage model.

    Each block is represented as a list: [block_id, stored_data_or_None].
    """

    def __init__(self):
        # Initialise blocks: BLOCK-01 … BLOCK-10, all FREE (None)
        self.blocks: List[List[Optional[str]]] = [
            [f"BLOCK-{i+1:02d}", None] for i in range(TOTAL_BLOCKS)
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _free_indices(self) -> List[int]:
        """Return list of indices whose data slot is None (free)."""
        return [i for i, (_, data) in enumerate(self.blocks) if data is None]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def check_storage(self, required_blocks: int) -> bool:
        """True if *required_blocks* free blocks are available."""
        return len(self._free_indices()) >= required_blocks

    def reserve_storage(self, required_blocks: int) -> List[int]:
        """Reserve free blocks and mark them as "RESERVED".

        Returns a list of the reserved block indices.
        Raises RuntimeError if not enough free blocks.
        """
        free = self._free_indices()
        if len(free) < required_blocks:
            raise RuntimeError("Insufficient free blocks for reservation")
        reserved = free[:required_blocks]
        for idx in reserved:
            self.blocks[idx][1] = "RESERVED"
        return reserved

    def release_reservation(self, reserved_indices: List[int]) -> None:
        """Turn all RESERVED blocks back to FREE (None)."""
        for idx in reserved_indices:
            if self.blocks[idx][1] == "RESERVED":
                self.blocks[idx][1] = None

    def store_data(self, data: str, reserved_indices: List[int]) -> None:
        """Store *data* across the previously reserved blocks.

        The data is split into chunks of size ``BLOCK_SIZE``. The number of
        chunks must match the number of reserved blocks.
        """
        # Split data into BLOCK_SIZE‑sized pieces
        chunks = [data[i : i + BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]
        if len(chunks) != len(reserved_indices):
            raise RuntimeError("Chunk count does not match reserved blocks")
        for idx, chunk in zip(reserved_indices, chunks):
            self.blocks[idx][1] = chunk

    def display(self) -> None:
        """Pretty‑print the current database state."""
        print("\n=== DATABASE STATUS ===")
        print(f"{'Block ID':<10} | Data")
        print("-" * 30)
        for block_id, content in self.blocks:
            status = content if content is not None else "FREE"
            if status == "RESERVED":
                status = "RESERVED"
            print(f"{block_id:<10} | {status}")
        print("-" * 30)
