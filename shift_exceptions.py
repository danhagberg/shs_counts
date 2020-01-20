import pandas as pd


def apply_exceptions(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply a hard coded group of exceptions to the schedule attributes
    Example: Remove from schedule persistent no-shows
    :param schedule_df: Current schedule
    :return: updated schedule dataframe with exceptions applied
    """
    return schedule_df
