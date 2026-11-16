"""Conservative screen-number validation, not process optimization."""
import re
from decimal import Decimal, InvalidOperation


def screen_number(text):
    value=str(text).strip().replace(',', '.')
    # A bare 00/000 is commonly the detached fractional suffix of e.g. 130.00.
    # Never repair missing punctuation/digits or OCR letters by guessing.
    if not re.fullmatch(r'-?(?:0|[1-9]\d*)(?:\.\d+)?',value):return None
    return value


def safe_scalar(field, value):
    number=screen_number(value)
    if number is None:return False
    try:
        numeric=Decimal(number)
        if not numeric.is_finite() or abs(numeric)>Decimal('1e9'):return False
        # This is an active dosing setting, not an inactive SC-return field.
        if field=='dosing_position' and numeric<=0:return False
        if field in ('back_pressure','injection_pressure','screw_speed','dosing_delay','cooling_time','holding_speed') and numeric<0:return False
        return True
    except InvalidOperation:return False


def equivalent(left,right):
    a,b=screen_number(left),screen_number(right)
    return a is not None and b is not None and Decimal(a)==Decimal(b)
