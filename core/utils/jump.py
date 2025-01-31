import numpy as np
import pandas as pd
import math

import constants
from constants import JumpType, jumpSuccess


class Jump:
    """
    Represents a single jump event within a skating session.

    This class encapsulates all relevant data and computations related to a jump,
    including its start and end frames, type, success status, duration, rotation,
    and associated sensor data. It provides methods to calculate rotation, resize
    the data frame for analysis, and export jump data to a CSV file.

    Attributes:
        start (int): The frame index where the jump starts.
        end (int): The frame index where the jump ends.
        type (jumpType): The type of the jump (e.g., Axel, Lutz). Defaults to jumpType.NONE.
        success (jumpSuccess): The success status of the jump. Defaults to jumpSuccess.NONE.
        combinate (bool): Indicates whether the jump is part of a combination.
        startTimestamp (float): The timestamp (in seconds) when the jump starts relative to the session start.
        endTimestamp (float): The timestamp (in seconds) when the jump ends relative to the session start.
        length (float): The duration of the jump in seconds.
        rotation (float): The absolute value of rotation in degrees around the vertical axis during the jump.
        df (pd.DataFrame): The resized dataframe containing sensor data for the jump.
        df_success (pd.DataFrame): Subset of `df` starting from frame index 120, potentially used for success analysis.
        df_type (pd.DataFrame): Subset of `df` up to frame index 240, potentially used for type analysis.
        max_rotation_speed (float): The maximum rotation speed recorded during the jump.
    """

    def __init__(
        self,
        start: int,
        end: int,
        df: pd.DataFrame,
        combinate: bool,
        jump_type: JumpType = JumpType.NONE,
        jump_success: jumpSuccess = jumpSuccess.NONE,
    ) -> None:
        """
        Initialize a Jump instance with specific parameters.

        Args:
            start (int): The frame index where the jump starts.
            end (int): The frame index where the jump ends.
            df (pd.DataFrame): The dataframe containing the session data where the jump occurs.
            combinate (bool): Indicates whether the jump is part of a combination.
            jump_type (jumpType, optional): The type of the jump. Defaults to jumpType.NONE.
            jump_success (jumpSuccess, optional): The success status of the jump. Defaults to jumpSuccess.NONE.

        Raises:
            ValueError: If `start` or `end` indices are out of bounds of the dataframe.
        """
        self.start = start
        self.end = end
        self.type = jump_type
        self.success = jump_success
        self.combinate = combinate

        self.startTimestamp = (df['SampleTimeFine'][start] - df['SampleTimeFine'][0]) / 1000
        self.endTimestamp = (df['SampleTimeFine'][end] - df['SampleTimeFine'][0]) / 1000

        # timestamps are in microseconds, I want to have the lenghs in seconds
        self.length = round(np.longlong(df['ms'][end] - df['ms'][start]) / 1000,3)

        self.rotation = self.calculate_rotation(df[self.start:self.end].copy().reset_index())

        self.df = self.dynamic_resize(df) # The dataframe containing the jump
        self.df["Combination"] = [int(self.combinate)]*len(self.df)
        self.df_success = self.df[120:] 
        self.df_type = self.df[:240]
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(subset=["Gyr_X_unfiltered"], how="all", inplace=True)
        self.max_rotation_speed = round(df['Gyr_X_unfiltered'][start:end].abs().max()/360,1)

    def calculate_rotation(self, df):
        """
        calculates the rotation in degrees around the vertical axis, the initial frame is a frame where the skater is
        standing still
        :param df: the dataframe containing the jump
        :return: the absolute value of the rotation in degrees
        """
        # initial frame is the reference frame, I want to compute rotations around the "Euler_X" axis
        df_rots = df[["SampleTimeFine", "Gyr_X"]]
        def check(s):
            return math.isinf(s["Gyr_X"]) or np.abs(s["Gyr_X"]) > 1e6

        df_rots = df_rots.drop(df_rots[df_rots.apply(check,axis=1)].index)
        n = len(df_rots)

        tps = df_rots['SampleTimeFine'].to_numpy().reshape(1,n)[0]
        tps = tps - tps[0]
        difftps = np.diff(tps)/1e6
        vit = df_rots['Gyr_X'].to_numpy().reshape(1,n)[0][:-1]
        pos = np.nansum(np.array(vit)*np.array(difftps))
        total_rotation_x = np.abs(pos/360)
        return total_rotation_x

    def dynamic_resize(self, df: pd.DataFrame = None):
        """
        Normalize the jump data to a specific time frame by selecting frames around the jump.

        The method ensures that there are at least 120 frames (2 seconds) before the takeoff
        and 180 frames (3 seconds) after the landing to provide sufficient context for analysis.

        Args:
            df (pd.DataFrame, optional): The original dataframe containing session data.

        Returns:
            pd.DataFrame: A resized dataframe focused on the jump period with additional frames.
        """
        resampled_df = df[self.start - 120:self.start + 180].copy(deep=True)

        return resampled_df

    def generate_csv(self, path: str):
        """
        exports the jump to a csv file
        :param path:
        :return:
        """
        self.df.to_csv(path, index=False)
