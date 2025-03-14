import numpy as np
import pandas as pd
import scipy as sp

from ...utils import constants
from ...utils import plot
from ...utils.jump import Jump


def _load_and_preprocess_data(df: pd.DataFrame, sample_time_fine_synchro: int = 0) -> pd.DataFrame:
    """
    loads a dataframe from a csv, and preprocess data
    :return: the dataframe with preprocessed fields
    """
    df = df.astype(
        {
            "PacketCounter": "int64",
            "SampleTimeFine": "ulonglong",
            "Euler_X": "float64",
            "Euler_Y": "float64",
            "Euler_Z": "float64",
            "Acc_X": "float64",
            "Acc_Y": "float64",
            "Acc_Z": "float64",
            "Gyr_X": "float64",
            "Gyr_Y": "float64",
            "Gyr_Z": "float64",
        }
    )

    if sample_time_fine_synchro != 0:
        # slice the list from sampleTimefineSynchro
        synchroIndex = df[df["SampleTimeFine"] >= sample_time_fine_synchro].index[0]
        df = df[synchroIndex:].reset_index(drop=True)
    df = df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    # adding the ms field, indicating how much ms has past since the beginning of the recording
    # we are using the SampleTimeFine field, which is a timestamp in microsecond

    # add 2^32 to the SampleTimeFine field when it is smaller than the previous one, because it means that the counter has overflowed
    initial_timeStamp = df["SampleTimeFine"][0]
    df.loc[df["SampleTimeFine"] < initial_timeStamp, "SampleTimeFine"] += 4294967296

    initialSampleTimeFine = df["SampleTimeFine"][0]
    df["ms"] = (df["SampleTimeFine"] - initialSampleTimeFine) / 1000
    df["X_acc_derivative"] = df["Acc_X"].diff()
    df["Y_acc_derivative"] = df["Acc_Y"].diff()
    df["Z_acc_derivative"] = df["Acc_Z"].diff()
    df["Gyr_X_unfiltered"] = df["Gyr_X"].copy(deep=True)
    df["Gyr_X_smoothed"] = sp.ndimage.gaussian_filter1d(df["Gyr_X"], sigma=30)
    df["X_gyr_derivative"] = df["Gyr_X_smoothed"].diff()
    df["Y_gyr_derivative"] = df["Gyr_Y"].diff()
    df["Z_gyr_derivative"] = df["Gyr_Z"].diff()
    df["X_gyr_second_derivative"] = df["X_gyr_derivative"].diff()

    # add markers when the value is crossing -0.2
    df["X_gyr_second_derivative_crossing"] = [x <= constants.treshold for x in df["X_gyr_second_derivative"]]
    return df


def _gather_jumps(df: pd.DataFrame) -> list[Jump]:
    """
    detects and gathers all the jumps in a dataframe
    :param df: the dataframe containing the session data
    :return: list of jumps done
    """
    jumps = []
    # Find indices where 'X_gyr_second_derivative_crossing' transitions from False to True
    begin = np.where(np.diff(df["X_gyr_second_derivative_crossing"].astype(int)) == 1)[0]
    # Find indices where 'X_gyr_second_derivative_crossing' transitions from True to False
    end = np.where(np.diff(df["X_gyr_second_derivative_crossing"].astype(int)) == -1)[0]

    if len(begin) > 0 and len(end) > 0:
        for i in range(len(end)):
            # remove the first end marks that happens before the first begin mark
            if end[i] < begin[0]:
                end = np.delete(end, i)
                break

        for i in range(len(begin)):
            combinate = False
            if i > 0:
                combinate = (begin[i] - begin[i - 1]) < constants.frames_after_jump
            jumps.append(Jump(begin[i], end[i], df, combinate))

    return jumps


class trainingSession:
    """
    This class is meant to describe a training session in a sport context. Not to be confused with a training session in a machine learning context (class training)
    contains the preprocessed dataframe and the jumps
    """

    def __init__(self, df: pd.DataFrame, sample_time_fine_synchro: int = 0):
        """
        :param path: path of the CSV
        :param synchroFrame: the frame where the synchro tap is
        """
        df = _load_and_preprocess_data(df, sample_time_fine_synchro)
        self._init_from_dataframe(df)

    def _init_from_dataframe(self, df: pd.DataFrame):
        """
        can be called as a constructor, provided that the dataframe correctly been preprocessed
        this function was meant to be a constructor overload. Things would be simpler if python was a decent programming language
        :param df: the dataframe containing the whole session
        """
        self.df = df
        self.jumps = _gather_jumps(df)

    def plot(self):
        timestamps = [jump.start_timestamp for jump in self.jumps] + [jump.end_timestamp for jump in self.jumps]
        plot.plot_data(self.df, timestamps, str(self))
