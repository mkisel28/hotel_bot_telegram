import datetime
from typing import List, Dict, Union, Optional
import configparser

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from hotel_api import HotelsAPI
from keyboard_utils import calendar_markup, city_confirmation_markup
from history_utils import save_history, load_history


config = configparser.ConfigParser()
config.read('config.cfg')

TOKEN = config['TELEGRAM']['TOKEN']
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

hotels_api = HotelsAPI()


class HotelSearchStates(StatesGroup):
    command = State()
    city = State()
    check_in_date = State()
    check_out_date = State()
    send_message = State()


def parse_callback_data(data: str) -> Union[str, List[str]]:
    return data.split('_')


async def update_date(year: int, month: int, action: str) -> tuple:
    if action == "nextmonth":
        month += 1
        if month > 12:
            month = 1
            year += 1
    elif action == "prevmonth":
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    return year, month


async def send_updated_calendar(callback_query: types.CallbackQuery, year: int, month: int, prompt: str):
    markup = await calendar_markup(year, month)
    await bot.edit_message_text(prompt,
                                callback_query.from_user.id,
                                callback_query.message.message_id,
                                reply_markup=markup
                                )


@dp.callback_query_handler(lambda c: c.data.startswith(("prevmonth_", "nextmonth_")), state=[HotelSearchStates.check_in_date, HotelSearchStates.check_out_date])
async def process_month_navigation(callback_query: types.CallbackQuery, state: FSMContext):
    action, year, month = parse_callback_data(callback_query.data)
    year, month = await update_date(int(year), int(month), action)
    current_state = await state.get_state()
    prompt = "Выберите дату заезда:" if current_state == 'HotelSearchStates:check_in_date' else "Выберите дату выезда:"
    await send_updated_calendar(callback_query, year, month, prompt)


async def handle_date_selection(callback_query: types.CallbackQuery, state: FSMContext, date_state: str):
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
    _, _, year, month, day = parse_callback_data(callback_query.data)
    selected_date = f"{int(year)}-{int(month):02}-{int(day):02}"

    await state.update_data({date_state: selected_date})
    await bot.send_message(callback_query.from_user.id, f"Выбрана дата {date_state.split('_')[-1]}: {selected_date}")
    if date_state == 'check_in_date':
        await bot.send_message(callback_query.from_user.id, "Выберите дату выезда:", reply_markup=await calendar_markup(int(year), int(month)))
        await HotelSearchStates.check_out_date.set()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот для поиска отелей. Выберите одну из команд: /lowprice, /guest_rating, /bestdeal, /history")


@dp.message_handler(commands=['lowprice', 'guest_rating', 'bestdeal'])
async def hotel_search(message: types.Message, state: FSMContext):
    command = message.text[1:]
    await state.update_data(command=command)
    await message.answer("Введите город:")
    await HotelSearchStates.city.set()


@dp.message_handler(state=HotelSearchStates.city)
async def process_city(message: types.Message, state: FSMContext):
    tmp_message = await message.answer("Поиск...")
    cities = await hotels_api.get_city_id(message.text)
    await state.update_data(cities=cities)

    if not cities:
        await tmp_message.delete()
        await message.answer("Не удалось найти город. Попробуйте еще раз.")
        return

    await tmp_message.delete()
    await message.answer("Уточните, пожалуйста:", reply_markup=city_confirmation_markup(cities))


@dp.callback_query_handler(lambda c: c.data.startswith('city_id_'), state=HotelSearchStates.city)
async def confirm_city(callback_query: types.CallbackQuery, state: FSMContext):
    city_id = callback_query.data.split("_")[-1]
    data = await state.get_data()
    cities = data.get("cities")
    city_name = next((city['name']
                     for city in cities if city['id'] == city_id), None)

    await state.update_data(city_id=city_id)
    await state.update_data(city_name=city_name)

    current_date = datetime.datetime.now()
    await bot.send_message(callback_query.from_user.id,
                           "Выберите дату заезда:",
                           reply_markup=await calendar_markup(current_date.year, current_date.month)
                           )
    await HotelSearchStates.check_in_date.set()


@dp.callback_query_handler(lambda c: c.data.startswith('calendar_day_'), state=HotelSearchStates.check_in_date)
async def process_check_in_date(callback_query: types.CallbackQuery, state: FSMContext):
    await handle_date_selection(callback_query, state, 'check_in_date')


@dp.callback_query_handler(lambda c: c.data.startswith('calendar_day_'), state=HotelSearchStates.check_out_date)
async def process_check_out_date(callback_query: types.CallbackQuery, state: FSMContext):
    await handle_date_selection(callback_query, state, 'check_out_date')
    await send_message(callback_query, state)


async def send_message(callback_query: types.CallbackQuery, state):
    user_data = await state.get_data()
    city_id = user_data.get("city_id")
    check_in_date = user_data.get("check_in_date")
    check_out_date = user_data.get("check_out_date")
    command = user_data.get("command")

    save_history(callback_query.from_user.id, city_id,
                 user_data["city_name"], check_in_date, check_out_date, command)

    await send_hotels_info(callback_query, command, city_id, check_in_date, check_out_date)
    await state.finish()

    continuation_prompt = "Повторный поиск: /lowprice, /guest_rating, /bestdeal, /history"
    await bot.send_message(callback_query.from_user.id, continuation_prompt)


async def send_hotels_info(callback_query: types.CallbackQuery, command: str, city_id: str, check_in_date: str, check_out_date: str):
    if command == 'lowprice':
        hotels = await hotels_api.search_by_lowprice(city_id, check_in_date, check_out_date)
    elif command == 'guest_rating':
        hotels = await hotels_api.search_by_guest_rating(city_id, check_in_date, check_out_date)
    elif command == 'bestdeal':
        hotels = await hotels_api.search_by_bestdeal(city_id, check_in_date, check_out_date)
    else:
        return

    for hotel in hotels['data']['propertySearch']['properties']:
        name = hotel['name']
        price = hotel['price']['lead']['formatted']
        review_score = hotel.get('reviews', {}).get('score', 'N/A')
        total_reviews = hotel.get('reviews', {}).get('total', 'N/A')

        message_content = f"Название: {name}\nЦена: {price}\nРейтинг: {review_score} (на основе {total_reviews} отзывов)"

        try:
            image_url = hotel['propertyImage']['image']['url']
            await bot.send_photo(chat_id=callback_query.from_user.id, photo=image_url, caption=message_content)
        except KeyError:
            await bot.send_message(callback_query.from_user.id, message_content)


@dp.message_handler(commands=['history'])
async def history(message: types.Message):
    user_history = load_history(message.from_user.id)
    if not user_history:
        await message.answer("Ваша история пуста.")
        return
    else:
        user_history = user_history[::-1]

    response = "История вашего поиска:\n"
    for entry in user_history[:2]:
        response += f"📍Локация: {entry['city_name']}, 📅Дата заезда: {entry['check_in_date']}, 📅Дата выезда: {entry['check_out_date']}, Тип поиска: {entry['search_type']}\n"

    await message.answer(response)

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
