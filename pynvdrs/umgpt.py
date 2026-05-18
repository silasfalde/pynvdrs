import os
import time
import json
from typing import Any, Optional, Dict, Tuple


def generate_response(
    client: Any,
    context: str,
    prompt: str,
    narrative: str,
    model: Optional[str] = None,
    type_string: str = "json_object",
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> str | None:
    """Prompt a chat-style client and return the response string.

    `client` should provide a `chat.completions.create` or similar API. `model`
    can be provided explicitly or will be read from `MODEL` env var if available.
    """
    model = model or os.environ.get("MODEL")
    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": prompt + "\n" + narrative},
    ]

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=0,
                response_format={"type": type_string},  # type: ignore
                stop=None,
                timeout=timeout_seconds,
            )
            return str(response.choices[0].message.content)
        except TimeoutError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None


def parse_response(
    txt: str | None,
    expected_codes: list[str] | dict[str, type | str],
) -> Tuple[dict[str, Any | None] | None, bool]:
    """Parse the response text into a dict of expected codes with optional coercion.

    Returns (response_dict_or_none, error_flag).
    """
    response_dict: dict[str, Any | None] = {}

    error_occurred = False

    expected_types: dict[str, type | str] | None

    if isinstance(expected_codes, dict):
        expected_types = expected_codes
        expected_code_list = list(expected_codes.keys())
    else:
        expected_types = None
        expected_code_list = expected_codes

    def _resolve_expected_type(expected_type: type | str) -> type:
        if isinstance(expected_type, str):
            normalized_type = expected_type.strip().lower()
            string_type_map: dict[str, type] = {
                "bool": bool,
                "boolean": bool,
                "int": int,
                "int32": int,
                "int64": int,
                "float": float,
                "float32": float,
                "float64": float,
                "str": str,
                "string": str,
            }

            if normalized_type not in string_type_map:
                raise ValueError(f"Unsupported expected type '{expected_type}'")

            return string_type_map[normalized_type]

        return expected_type

    def _coerce_value(value: Any, expected_type: type) -> Any:
        if value is None:
            return None

        if isinstance(value, expected_type):
            return value

        if expected_type is bool:
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "1", "yes", "y"}:
                    return True
                if normalized in {"false", "0", "no", "n"}:
                    return False
                raise ValueError(f"Cannot convert '{value}' to bool")

            if isinstance(value, (int, float)) and value in {0, 1}:
                return bool(value)

            raise ValueError(f"Cannot convert '{value}' to bool")

        if expected_type is str:
            return str(value)

        return expected_type(value)

    try:
        if txt is not None:
            txt_dict: dict = json.loads(txt)

            if not isinstance(txt_dict, dict):
                raise ValueError("Parsed response is not a JSON object")

            for feature in expected_code_list:
                if feature in txt_dict:
                    value = txt_dict[feature]

                    if expected_types is not None and feature in expected_types:
                        try:
                            value = _coerce_value(
                                value, _resolve_expected_type(expected_types[feature])
                            )
                        except (TypeError, ValueError):
                            value = None
                            error_occurred = True

                    response_dict[feature] = value
                else:
                    response_dict[feature] = None
                    error_occurred = True

            return response_dict, error_occurred

        else:
            return None, False

    except Exception:
        return None, True
