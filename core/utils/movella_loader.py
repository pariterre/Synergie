_is_loaded = False

try:
    import movelladot_pc_sdk.movelladot_pc_sdk_py310_64 as movelladot_sdk  # type: ignore

    _is_loaded = True
except ImportError:
    pass

if not _is_loaded:
    try:
        import movelladot_pc_sdk.movelladot_pc_sdk_py9_64 as movelladot_sdk  # type: ignore

        _is_loaded = True
    except ImportError:
        pass

if not _is_loaded:
    try:
        import movelladot_pc_sdk.movelladot_pc_sdk_py8_64 as movelladot_sdk  # type: ignore

        _is_loaded = True
    except ImportError:
        pass

if not _is_loaded:
    raise ImportError("Could not load the movelladot_pc_sdk library")
