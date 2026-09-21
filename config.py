# config.py
"""
Configuration constants for the Reliable Data Transmission simulation.
"""

HOST = "127.0.0.1"
PORT = 5000

# Storage model
BLOCK_SIZE = 100          # bytes per block
TOTAL_BLOCKS = 10         # total number of blocks in the database

# CRC error simulation – set to True to corrupt payload after CRC calculation
SIMULATE_ERROR = False
