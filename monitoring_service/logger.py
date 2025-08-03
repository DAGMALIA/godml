# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import logging
import sys
import os
import warnings

def setup_clean_logging():
    """Configurar logging limpio sin warnings molestos"""
    # Suprimir warnings de TensorFlow y otros
    #os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    #os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    
    # Suprimir warnings específicos
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    # Configurar loggers de terceros
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("sagemaker").setLevel(logging.ERROR)
    logging.getLogger("mlflow").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.ERROR)

def get_logger(name: str = "GODML") -> logging.Logger:
    # Configurar logging limpio al crear el logger
    setup_clean_logging()
    
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(message)s"  # Solo el mensaje, sin timestamp para output más limpio
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Evitar duplicados
        logger.propagate = False

    return logger

# Logger global para usar en toda la aplicación
godml_logger = get_logger()