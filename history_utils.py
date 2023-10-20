import json


def save_history(user_id: int, city_id: int, city_name: str, check_in_date, check_out_date, search_type):
    search_data = {
        "city_id": city_id,
        "city_name": city_name,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "search_type": search_type
    }
    with open('history.json', 'r+', encoding='utf-8') as file:
        try:
            history = json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            history = {}

        if str(user_id) not in history:
            history[str(user_id)] = []

        history[str(user_id)].append(search_data)

        file.seek(0)
        json.dump(history, file, ensure_ascii=False, indent=4)


def load_history(user_id: int):
    with open('history.json', 'r', encoding='utf-8') as file:
        try:
            history = json.load(file)
            return history.get(str(user_id), [])
        except (json.JSONDecodeError, FileNotFoundError):
            return []
