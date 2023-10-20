import calendar

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def calendar_markup(year, month):
    markup = InlineKeyboardMarkup()
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    row = [InlineKeyboardButton(day, callback_data="ignore")
           for day in week_days]
    markup.row(*row)

    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(
                    str(day), callback_data=f"calendar_day_{year}_{month}_{day}"))

        markup.row(*row)

    row = [
        InlineKeyboardButton("<", callback_data=f"prevmonth_{year}_{month}"),
        InlineKeyboardButton(f"{month}/{year}", callback_data="ignore"),
        InlineKeyboardButton(">", callback_data=f"nextmonth_{year}_{month}")
    ]
    markup.row(*row)
    return markup


def city_confirmation_markup(cities):
    markup = InlineKeyboardMarkup()
    for city in cities:
        markup.add(InlineKeyboardButton(
            text=city['name'], callback_data=f"city_id_{city['id']}"))
    return markup
