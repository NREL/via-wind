# -*- coding: utf-8 -*-
"""
log module
"""
import io
import logging
import os
import sys
from pathlib import Path

from rex.utilities import init_logger as rex_init_logger, LOGGERS

LOG_FORMAT = "%(levelname)s - %(asctime)s [%(filename)s:%(lineno)d] : %(message)s"


def init_logger(name, log_directory, module, verbose=False, node=False, stream=False):
    """
    Initialize logger

    Parameters
    ----------
    name : str
        Job name; name of log file.
    log_directory : str
        Target directory to save .log files.
    module : str
        Name of module for which to initialize logger.
    verbose : bool
        Option to turn on debug logging.
    node : bool
        Flag for whether this is a node-level logger. If this is a node logger,
        and the log level is info, the log_file will be None (sent to stdout).
    stream : bool
        Flag for whether to include a StreamHandler for output to stdout. Default
        is False, which will only add a FileHandler.

    Returns
    -------
    logger : logging.Logger
        Logger instance that was initialized
    """

    if verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"

    if log_directory is not None:
        log_directory_path = Path(log_directory)
        log_directory_path.mkdir(exist_ok=True)
        log_path = log_directory_path.joinpath(f"{name}.log")
    else:
        log_path = None

    # clear rex cached attributes for logs to avoid pointing to non-existent
    # filehandlers on multiple runs of the same module
    LOGGERS.clear()

    if node and log_level == "INFO":
        # Node level info loggers only go to STDOUT/STDERR files
        logger = rex_init_logger(module, log_level=log_level, log_file=None)
    else:
        logger = rex_init_logger(
            module, log_level=log_level, log_file=log_path, stream=stream
        )

    return logger


class CSilencer:
    """
    A context manager that blocks stdout from C programs. Useful for silencing
    messages called from the blender render command.
    Derived from https://stackoverflow.com/a/76381451.
    """

    def __init__(self):
        sys.stdout.flush()
        self._origstdout = sys.stdout
        # special handling for io redirector from pydev
        try:
            self._oldstdout_fno = os.dup(sys.stdout.fileno())
        except io.UnsupportedOperation:
            self._oldstdout_fno = None
        self._devnull = os.open(os.devnull, os.O_WRONLY)
        self._newstdout = None

    def __enter__(self):
        self._newstdout = os.dup(1)
        os.dup2(self._devnull, 1)
        os.close(self._devnull)
        sys.stdout = os.fdopen(self._newstdout, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._origstdout
        sys.stdout.flush()
        # special handling for io redirector from pydev
        if self._oldstdout_fno is not None:
            os.dup2(self._oldstdout_fno, 1)
            os.close(self._oldstdout_fno)  # Additional close to not leak fd


def remove_streamhandlers(logger):
    """
    Remove StreamHandlers from a logger to stop output to stdout.

    Parameters
    ----------
    logger : logging.Logger
        Logger with StreamHandlers removed
    """

    stream_handlers = [
        h
        for h in logger.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
    ]
    for stream_handler in stream_handlers:
        logger.removeHandler(stream_handler)
