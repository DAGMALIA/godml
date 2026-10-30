# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.train.models.model_registry.lstm_forecast_model``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.model_service.model_registry.lstm_forecast_model",
    "godml.train.models.model_registry.lstm_forecast_model",
)
