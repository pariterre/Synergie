from functools import cache
import copy
import os

import pandas as pd

from ...database.database_manager import DatabaseManager
from ...utils import constants
from ...utils.jump import Jump


def mstostr(ms: float):
    s = round(ms / 1000)
    return "{:02d}:{:02d}".format(s // 60, s % 60)


def preload_resources():
    _get_model_predictor()


@cache
def _get_model_predictor():
    from ...model import model
    from .model_predictor import ModelPredictor

    model_jump_type = model.load_model(constants.filepath_model_type)
    model_is_jump_success = model.load_model(constants.filepath_model_success)
    return ModelPredictor(model_jump_type, model_is_jump_success)


def export(df: pd.DataFrame, sample_time_fine_synchro: int = 0) -> pd.DataFrame:
    from .training_session import trainingSession

    """
    exports the data to a folder, in order to be used by the ML model
    :param folder_name: the folder where to export the data
    :param sampleTimeFineSynchro: the timefinesample of the synchro tap
    :return:
    """
    # get the list of csv files

    all_jumps: list[Jump] = []
    predict_jump = []

    session = trainingSession(df, sample_time_fine_synchro)

    for jump in session.jumps:
        jump_copy = copy.deepcopy(jump)
        # jump_copy.data_type = jump.data_type
        # jump_copy.data_success = jump.data_success
        all_jumps.append(jump_copy)
        predict_jump.append(jump_copy.data)

    if not all_jumps:
        return pd.DataFrame()

    prediction = _get_model_predictor()
    predict_type, predict_success = prediction.predict(predict_jump)

    jumps = []
    for i, jump in enumerate(all_jumps):
        if jump.data is None:
            continue
        if len(jump.data) == constants.frames_before_jump + constants.frames_after_jump:
            # since videoTimeStamp is for user input, I can change it's value to whatever I want
            jumps.append(
                {
                    "videoTimeStamp": mstostr(jump.start_timestamp),
                    "type": predict_type[i],
                    "success": predict_success[i],
                    "rotations": "{:.1f}".format(jump.rotation),
                    "rotation_speed": jump.max_rotation_speed,
                    "length": jump.length,
                }
            )

    return pd.DataFrame(jumps).sort_values(by=["videoTimeStamp"])


def old_export():
    from .training_session import trainingSession

    """
    exports the data to a folder, in order to be used by the ML model
    :param folder_name: the folder where to export the data
    :param sampleTimeFineSynchro: the timefinesample of the synchro tap
    :return:
    """
    all_jumps: dict[str, Jump] = []
    database_manager = DatabaseManager()

    for training in os.listdir("data/new"):
        if os.path.isfile(f"data/new/{training}"):
            synchro, training_id = training.replace(".csv", "").split("_")
            synchro = int(synchro)
            skater_name = database_manager.get_skater_name_from_training_id(training_id)
            df = pd.read_csv(f"data/new/{training}")

            session = trainingSession(df, synchro)

            for jump in session.jumps:
                jump_copy = copy.deepcopy(jump)
                # jump_copy.skater_name = skater_name
                # jump_copy.df = jump.df.copy(deep=True)
                all_jumps[skater_name] = jump_copy

    jumps = []
    for skater_name, jump in all_jumps.items():
        if jump.data is None:
            continue
        jump_id = f"{skater_name}_{jump.start_timestamp}"
        if jump_id != "0":
            filename = os.path.join(f"data/pending{jump_id}.csv")
            jump.data.to_csv(filename)
            # since videoTimeStamp is for user input, I can change it's value to whatever I want
            jumps.append(
                {
                    "path": f"{jump_id}.csv",
                    "videoTimeStamp": mstostr(jump.start_timestamp),
                    "type": jump.type.value,
                    "skater": skater_name,
                    "sucess": 2,
                    "rotations": "{:.1f}".format(jump.rotation),
                }
            )

    jumps_as_df = pd.DataFrame(jumps)
    jumps_as_df = jumps_as_df.sort_values(by=["videoTimeStamp"]).reset_index(drop=True)

    jumps_as_df.to_csv("data/pending/jumplist.csv")
