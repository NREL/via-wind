# -*- coding: utf-8 -*-
"""
Helper functions
"""
import datetime
import time
from pathlib import Path


def hms(seconds):
    """
    Converts a time duration in seconds to a more human-readable string of the format
    H:MM:SS. If the duration exceeds 24 hours, the format will be "D days, H:MM:SS".

    Parameters
    ----------
    seconds : [int, float]
        Duration of elapsed time in seconds

    Returns
    -------
    str
        Formatted time duration
    """
    return str(datetime.timedelta(seconds=seconds))


class ProgressTracker:
    """
    Class that can be used as context manager to track and report on progress over
    a number of iterations. Similar to  using tqdm as a context manager but without
    the progress bar, only the messages.

    Example:

    total = 10
    with ProgressTracker(total=total, desc="Running iteration ") as p:
        for i in range(0, total):
            print(p.message)
            p.update(1)
    """

    def __init__(self, total, desc=""):
        """
        Initialize a ProgressTracker object

        Parameters
        ----------
        total : int
            Total number of iterations to be tracked
        desc : str, optional
            Optional message that will be prepended to progress messages. By default "".
        """
        self.desc = f"{desc} "
        self.total = total
        self.t_start = time.time()
        self.run_time = 0
        self.time_remaining = 0
        self.iter_time = 0
        self.i = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        return

    def update(self, n):
        """
        Increments the progress based on n number of additional completed iterations.

        Parameters
        ----------
        n : int
            Number of additional iterations completed.
        """

        self.i += n
        self.run_time = round(time.time() - self.t_start)
        self.iter_time = round(self.run_time / (self.i))
        self.time_remaining = round(self.iter_time * (self.total - self.i))

    @property
    def message(self):
        """
        Formats and returns a message indicating the progress relative to the total
        number of iterations, the time elapsed, the estimated time remaining, and the
        average time per iteration."
        """
        msg = (
            f"{self.desc}{self.i}/{self.total} "
            f"[{hms(self.run_time)}<{hms(self.time_remaining)}, "
            f"{hms(self.iter_time)}/it]"
        )
        return msg


def verify_directory(directory):
    """
    Check that the input directory path exists and is a folder.

    Parameters
    ----------
    directory : str
        Path to directory.

    Raises
    ------
    FileNotFoundError
        A FileNotFoundError will be raised if the input path does not exist.
    TypeError
        A TypeError will be raised if the input path is not a folder.
    """
    if Path(directory).exists() is False:
        raise FileNotFoundError(f"Input directory {directory} could not be found.")
    if Path(directory).is_dir() is False:
        raise TypeError(f"Input directory {directory} is not a folder.")


def verify_file(fpath):
    """
    Check that the input file path exists and is a file.

    Parameters
    ----------
    fpath : str
        Path to file.

    Raises
    ------
    FileNotFoundError
        A FileNotFoundError will be raised if the input path does not exist.
    TypeError
        A TypeError will be raised if the input path is not a file.
    """
    if Path(fpath).exists() is False:
        raise FileNotFoundError(f"Input fpath {fpath} could not be found.")
    if Path(fpath).is_dir() is True:
        raise TypeError(f"Input fpath {fpath} is not a file.")
