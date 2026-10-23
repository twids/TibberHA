"""Bounded retry for read-only discovery; never used for mutations."""
from tibberlib import TibberError


async def read_with_reauthentication(read, authenticate):
    """Recover once in this poll rather than waiting another fifteen minutes."""
    try:
        return await read()
    except TibberError:
        await authenticate()
        return await read()
