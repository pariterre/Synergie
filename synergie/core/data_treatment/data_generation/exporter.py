import copy

import pandas as pd

from ...utils import constants
from ...utils.jump import Jump


def mstostr(ms: float):

    s = round(ms / 1000)
    return "{:02d}:{:02d}".format(s // 60, s % 60)


def export(df: pd.DataFrame, sample_time_fine_synchro: int = 0) -> pd.DataFrame:
    from .model_predictor import ModelPredictor
    from .training_session import trainingSession
    from ...model import model

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

    # TODO: load once the model, not for each jump
    model_test_type = model.load_model(constants.filepath_model_type)
    model_test_success = model.load_model(constants.filepath_model_success)
    prediction = ModelPredictor(model_test_type, model_test_success)
    predict_type, predict_success = prediction.predict(predict_jump)

    jumps = []
    for i, jump in enumerate(all_jumps):
        if jump.data is None:
            continue
        if len(jump.data) == 400:
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

    jumps_as_df = pd.DataFrame(jumps)
    jumps_as_df = jumps_as_df.sort_values(by=["videoTimeStamp"])

    return jumps_as_df
