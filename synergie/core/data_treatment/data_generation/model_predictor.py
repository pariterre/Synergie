import os
import keras

import numpy as np
import pandas as pd


class ModelPredictor:
    def __init__(self, model_type: keras.models.Model, model_success: keras.models.Model) -> None:
        self._model_type = model_type
        self._model_success = model_success

    def predict(self, data: list[pd.DataFrame]):
        predict_jump_type = []
        predict_jump_success = []
        predict_type = np.zeros(len(data))
        predict_success = np.zeros(len(data))

        for index, df in enumerate(data):
            df_predictjump = df
            if len(df_predictjump) == 300:
                predict_jump_type.append(df_predictjump[:240])
                predict_jump_success.append(df_predictjump[120:])
            else:
                predict_type[index] = 8
                predict_success[index] == 2

        prediction_type = self._model_type.predict(np.array(predict_jump_type))
        prediction_success = self._model_success.predict(np.array(predict_jump_success))

        for i in range(len(prediction_success)):
            if predict_type[i] != 8:
                predict_type[i] = np.argmax(prediction_type[i])
            if predict_success[i] != 2:
                predict_success[i] = np.argmax(prediction_success[i])

        return (predict_type, predict_success)
