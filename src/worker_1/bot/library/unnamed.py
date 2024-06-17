import hashlib as hx

def toChunk(string: str, nChunk: int = 4) -> list:
    """
    Split string into nChunk parts according to `nChunk`.
    
    Returns:
    ------------------------------------------------------------------------
    - list[str]: The list of parts.
    
    Raises:
    ------------------------------------------------------------------------
    - Exception: When the `seed_str` < `n_chunk` or `len(seed_str) is not completely devided by `n_chunk`.
    """
    stringLength = len(string)
    if stringLength < nChunk or stringLength % nChunk != 0:
        raise Exception("Invalid")
    if nChunk == 1: 
        return [string]
    parts = []
    step = stringLength // nChunk
    for i in range(0, len(string), step):
        parts.append(string[i : i + step])
    return parts


def encode(seed, n_chunk: int = 4) -> str:
    """
    Get the corresponding encoding string through hashing the input seed.
    ------------------------------------------------------------------------
    Hash input seed into deterministic encoding string, irreversible.
    
    Parameters:
    ------------------------------------------------------------------------
    - seed (Any): The input seed.
    - n_chunk (int): The number of parts to split the input seed into.
    
    Returns:
    ------------------------------------------------------------------------
    - str: The corresponding encoding string.
    
    Raises:
    ------------------------------------------------------------------------
    - ValueError: When `n_chunk` is out of range.
    - Exception: When the `str(seed)` fail.
    - Exception: When the `seed_str` < `n_chunk` or `len(seed_str) is not completely devided by `n_chunk`.
    
    Notes:
    ------------------------------------------------------------------------
    Reduce nChunk to reduce collision rate.
    """
    prime_number = 271
    seed_str = seed
    if type(seed) is not str:
        seed_str = str(seed)

    if n_chunk < 1 or n_chunk > len(seed_str):
        raise ValueError("Invalid input")

    hash_str = hx.md5(seed_str[:].encode()).hexdigest()
    chunks = toChunk(hash_str, 4)  # str
    chunks = list(map(lambda x: int(x, 16), chunks))  # int
    y = sum(chunks) // prime_number
    return str(y)
