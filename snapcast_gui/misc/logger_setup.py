import logging


class LoggerSetup:
    @staticmethod
    def setup_logging(log_file_path: str, log_level: int):
        """
        Sets up the logging handlers for both file and stream.

        Args:
            log_file_path (str): The path to the log file.
            log_level (int): The logging level.
        """
        # Check if handlers are already added to avoid duplicate logs
        if not logging.getLogger().hasHandlers():
            file_handler = logging.FileHandler(log_file_path)
            stdout_handler = logging.StreamHandler()

            file_handler.setLevel(log_level)
            stdout_handler.setLevel(log_level)

            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )

            file_handler.setFormatter(formatter)
            stdout_handler.setFormatter(formatter)

            logging.getLogger().addHandler(file_handler)
            logging.getLogger().addHandler(stdout_handler)

        logging.getLogger().setLevel(log_level)

    @staticmethod
    def get_logger(logger_name: str) -> logging.Logger:
        """
        Gets a logger with the specified name.

        Args:
            logger_name (str): The name of the logger.

        Returns:
            logging.Logger: The logger with the specified name.
        """
        return logging.getLogger(logger_name)
