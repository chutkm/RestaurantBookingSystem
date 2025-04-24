import locale
from lib2to3.fixes.fix_input import context
from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, InputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import timedelta
import re
from sqlalchemy import types, select, Update
from datetime import datetime
import asyncio
import io
import logging
from aiogram import types
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from aiogram.types import BufferedInputFile

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_TIME, 'russian')
import app.keyboards as kb
import app.database.requests_bot as rq_b
from app.database.models import async_session, Clients, Menu, Reservations, Tables, Restaurants, Preorder

router = Router()

# Состояния для FSM
class Register_number(StatesGroup):
    phone = State()  # Состояние для ввода телефона

# Состояния для обработки бронирования
class Register(StatesGroup):
    reservation_id = State()
    rest_id = State()  # Для restaurant_id
    rest_address = State()  # Для restaurant_name
    date = State()
    time = State()
    hours = State()
    number_of_guests = State()
    table_choice = State()

    preorder = State()
    name = State()
    confirm = State()


class CancelReservation(StatesGroup):
    name = State()
    date = State()
    time = State()
    number_of_guests = State()
    confirm_cancel = State()


class Edit(StatesGroup):
    date = State()
    time = State()
    number_of_guests = State()
    name = State()
    number = State()
    confirm = State()




@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Обрабатывает команду /start. Заполняет данные пользователя и запрашивает телефон при необходимости.
    """
    try:
        # Добавляем пользователя в базу без номера телефона
        await rq_b.set_user(
            tg_id=message.from_user.id,
            tg_user_name=message.from_user.username
        )

        # Приветственное сообщение
        photo = 'https://i.pinimg.com/736x/b3/ad/16/b3ad16e9679d8b929b16ab7970c5cb64.jpg'
        await message.answer_photo(photo)
        await message.answer(
            "Приветствуем вас в сервисе бронирования столиков сети ресторанов Mari! 🤩"
        )

        # Проверяем, указан ли номер телефона
        phone_missing = await rq_b.check_number(message.from_user.id)
        if phone_missing:
            await message.answer(
                "Для дальнейшей работы с нами отправьте свой номер телефона или введите его вручную:",
                reply_markup=kb.get_number
            )
            await state.set_state(Register_number.phone)
        else:
            await message.answer( "Мы уже тебя ждем!",reply_markup=kb.main)

    except Exception as e:
        print(f"Ошибка в обработке команды /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()


@router.message(Register_number.phone)
async def register_number(message: Message, state: FSMContext):
    """
    Обрабатывает ввод номера телефона и завершает регистрацию.
    """
    try:
        # Получаем номер телефона из контакта или текста
        phone = message.contact.phone_number if message.contact else message.text.strip()

        # Проверка формата номера
        if not re.match(r"^\+7\d{10}$", phone):
            await message.answer(
                "Пожалуйста, введите номер в формате +7XXXXXXXXXX."
            )
            return

        # Обновляем номер телефона в базе данных
        async with async_session() as session:
            from sqlalchemy import update
            await session.execute(
                update(Clients)
                .where(Clients.tg_id == message.from_user.id)
                .values(phone_number=phone)
            )
            await session.commit()

        # Сообщение об успешной регистрации
        await message.answer(
            "Регистрация успешно завершена! 🤩",
            reply_markup=kb.main
        )
        await state.clear()

    except Exception as e:
        print(f"Ошибка при регистрации номера телефона: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()




@router.callback_query(F.data.startswith("cancel_history:"))
async def cancel_booking(callback: CallbackQuery):
    """
    Обрабатывает отмену бронирования.
    """
    booking_id = int(callback.data.split(":")[1])
    try:
        async with async_session() as session:
            from sqlalchemy import update
            # Обновляем статус бронирования на "отменено"
            await session.execute(
                update(Reservations)
                .where(Reservations.reservation_id == booking_id)
                .values(reservation_status='отменено')
            )
            await session.commit()
        await callback.message.edit_text("Бронирование успешно отменено.")
        await callback.answer("Бронирование отменено.")
    except Exception as e:
        print(f"Ошибка при отмене бронирования: {e}")
        await callback.answer("Произошла ошибка при отмене.")



@router.callback_query(lambda c: c.data == 'back')
async def process_back_button(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    await callback_query.message.answer(
        'Вы вернулись в главное меню.',
        reply_markup=kb.main
    )

@router.message(F.text == 'Мои бронирования')
async def my_bookings(message: Message):
    """
    Обрабатывает кнопку "Мои бронирования".
    """
    try:
        user_id = message.from_user.id
        async with async_session() as session:
            # Запрос для получения всех бронирований пользователя
            query = (
                select(
                    Reservations,  # Данные из таблицы бронирований
                    Tables.table_number,  # Номер столика
                    Restaurants.address  # Адрес ресторана
                )
                .join(Clients, Reservations.client_id == Clients.client_id)
                .join(Tables, Reservations.table_id == Tables.table_id)
                .join(Restaurants, Tables.restaurant_id == Restaurants.restaurant_id)
                .where(
                    Clients.tg_id == user_id,
                    Reservations.reservation_date_time >= datetime.now() ,Reservations.reservation_status == 'подтверждено'
                )
            )
            result = await session.execute(query)
            bookings = result.all()

            if not bookings:
                await message.answer("У вас нет активных бронирований.")
                return

            # Сортировка актуальных бронирований по дате
            bookings.sort(key=lambda x: x[0].reservation_date_time)

            # Генерация сообщений для актуальных бронирований
            await message.answer("📌 Актуальные бронирования:")
            for booking, table_number, address in bookings:
                text = (
                    f"📍 Ресторан по адресу: {address}\n\n"
                    f"📅 Дата и время: {booking.reservation_date_time.strftime('%d-%m-%Y %H:%M')}\n"
                    f"⏳ Часы бронирования: {booking.reservation_hours}\n"
                    f"👥 Количество гостей: {booking.guest_count}\n"
                    f"💺 Столик: {table_number}\n"
                    f"📌 Состояние бронирования: {booking.reservation_status}\n"
                )
                await message.answer(
                    text,
                    reply_markup=kb.booking_keyboard(booking.reservation_id, True)
                )
    except Exception as e:
        logging.exception("Ошибка при обработке бронирований.")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("preorder_history:"))
async def view_preorder(callback: CallbackQuery):
    """
    Обрабатывает запрос на просмотр предзаказов.
    """
    try:
        # Проверяем формат данных и извлекаем ID бронирования
        data_parts = callback.data.split(":")
        if len(data_parts) < 2 or not data_parts[1].isdigit():
            await callback.answer("Неверный формат данных. Попробуйте еще раз.")
            return

        booking_id = int(data_parts[1])

        async with async_session() as session:
            # Запрос для получения информации о предзаказах по ID бронирования
            query = (
                select(
                    Menu.name_dish,  # Название блюда
                    Preorder.quantity  # Количество
                )
                .join(Menu, Preorder.menu_id == Menu.menu_id)  # Джоин с меню
                .where(Preorder.reservation_id == booking_id)  # Условие по ID бронирования
            )
            result = await session.execute(query)
            preorders = result.all()

            if not preorders:
                await callback.message.edit_text("Нет предзаказов для этого бронирования.")
                return

            # Формирование текста для вывода
            text = "📋 Ваши предзаказы:\n\n"
            for name_dish, quantity in preorders:
                text += f"🍽 {name_dish}: {quantity} шт.\n"

            await callback.message.edit_text(text)
            await callback.answer("Предзаказы отображены.")
    except Exception as e:
        print(f"Ошибка при просмотре предзаказов: {e}")
        await callback.answer("Произошла ошибка при просмотре предзаказов.")



@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Вы нажали на кнопку помощи. Выберите интересующий вас раздел из меню.")


@router.message(F.text == "Контакты")
async def process_contacts(message: Message):
    contact_info = (
        "📞 Телефон: +1234567890\n"
        "✉️ Email: example@example.com\n"
        "🌐 Вебсайт: www.example.com\n"
        "🏠 Адрес: ул. Примерная, дом 1"
    )
    await message.answer(contact_info)


async def generate_pdf(promotions):
    """Асинхронная генерация PDF в памяти."""
    return await asyncio.to_thread(_generate_pdf_sync, promotions)


def _generate_pdf_sync(promotions):
    """Синхронная генерация PDF в памяти с акциями и скидками."""

    # Создание буфера для хранения PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    elements = []

    # Регистрация шрифта с поддержкой кириллицы
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

    # Определение стилей
    title_style = ParagraphStyle(
        name='Title',
        fontName='DejaVuSans',
        fontSize=20,
        alignment=1,
        spaceAfter=16,
        textColor='#2C3E50',
        fontWeight='bold'
    )

    header_style = ParagraphStyle(
        name='Header',
        fontName='DejaVuSans',
        fontSize=14,
        alignment=1,
        spaceAfter=12,
        textColor='#2980B9',
        fontStyle='italic'
    )

    normal_style = ParagraphStyle(
        name='Normal',
        fontName='DejaVuSans',
        fontSize=12,
        alignment=0,
        spaceAfter=8,
        textColor='#34495E'
    )

    # Форматирование текущей даты
    from datetime import datetime
    current_date = datetime.now().strftime("%d. %m. %Y")

    # Заголовок документа
    elements.append(Paragraph(" Скидки и Акции", title_style))
    elements.append(Spacer(1, 0.05 * letter[1]))

    # Введение
    elements.append(Paragraph(
        f"В нашем ресторане на {current_date} действуют скидки и специальные предложения. "
        "Не упустите возможность воспользоваться ими!", header_style))
    elements.append(Spacer(1, 0.15 * letter[1]))

    # Добавление информации об акциях
    for promo in promotions:
        promo_text = (
            f"<b>Акция:</b> {promo.description}<br/>"
            f"<b>Скидка:</b> {promo.discount_percentage}%<br/>"
            f"<b>Период действия:</b> с {promo.start_date.strftime('%d. %m. %Y')} по {promo.end_date.strftime('%d. %m. %Y')}<br/>"
        )
        elements.append(Paragraph(promo_text, normal_style))
        elements.append(Spacer(1, 0.05 * letter[1]))  # Уменьшено расстояние между акциями

    # Завершение и создание PDF
    doc.build(elements)
    pdf_buffer.seek(0)  # Возвращаем курсор в начало
    return pdf_buffer



@router.message(lambda message: message.text == "Акции")
async def process_contacts(message: types.Message):
    try:
        # Логирование начала работы
        logger.info(f"Получен запрос на акции от пользователя: {message.from_user.id}")

        # Получаем список активных акций
        promotions = await rq_b.find_promotion()

        if promotions:
            # Логирование перед генерацией PDF
            logger.info(f"Генерация PDF для {len(promotions)} акций...")

            # Генерация PDF в памяти
            pdf_buffer = await generate_pdf(promotions)

            # Логирование после генерации PDF
            logger.info("PDF файл с акциями сгенерирован в памяти.")

            # Отправка PDF-файла напрямую из памяти
            await message.answer("🎉 Вот ваш файл с актуальными акциями!")
            await message.answer_document(
                BufferedInputFile(pdf_buffer.read(), filename="promotions.pdf"),
                caption="Акции и скидки!"
            )

            # Логирование успешной отправки
            logger.info(f"PDF файл отправлен пользователю {message.from_user.id}.")

        else:
            # Логирование случая, если акций нет
            logger.warning(f"Пользователь {message.from_user.id} запросил акции, но их нет.")
            await message.answer("❌ *На данный момент нет действующих акций.*")

    except Exception as e:
        # Логирование ошибки
        logger.error(f"Ошибка при обработке запроса на акции от пользователя {message.from_user.id}: {e}")
        await message.answer("🚨 Произошла ошибка при обработке вашего запроса.")


@router.message(F.text == "О нас")
async def process_about(message: Message):
    about_info = (
        "Мы — ресторан Mari с многолетней историей, где традиции встречаются с современными вкусами. "
        "Всегда рады приветствовать вас и ваших близких в уютной атмосфере наших заведений!\n\n"
        "Мы являемся сетью из 4 ресторанов, каждый из которых готов предложить вам высококлассное обслуживание и изысканные блюда:\n\n"
        "1. Mari — ул. Лобненская, 4А, ☎ 8 (495) 526-33-03\n"
        "2. Mari — ул. Костромская, 17, ☎ 8 (495) 616-33-03\n"
        "3. Mari — ул. Дежнева, 13, ☎ 8 (496) 616-66-03\n"
        "4. Mari — пр-т Мира, 97, ☎ 8 (495) 616-66-03\n\n"
        "📧 Для связи и бронирования вы можете написать нам на почту: info@mari-rest.ru\n\n"
        "Мы всегда стараемся сделать ваш визит незабываемым и наполнить его теплом и заботой. "
        "Приходите в Mari, чтобы насладиться вкусом и уютом! ❤️"
    )

    await message.answer(about_info)

#----------------------------------------------- Бронирование

@router.message(F.text == "Бронь")
async def register_start(message: Message, state: FSMContext):
    await message.answer("Приступим к бронированию 😊", reply_markup=kb.main_without_bron)
    await state.set_state(Register.rest_id)

    restaurants = await rq_b.all_rest_view()
    if not restaurants:
        await message.answer("Рестораны не найдены.")
        return

    markup = kb.generate_restaurant_buttons(restaurants)
    await message.answer("Выберите ресторан:", reply_markup=markup)

@router.callback_query(Register.rest_id)
async def register_restaurant(callback: CallbackQuery, state: FSMContext):
    try:
        data = callback.data.split(":")
        restaurant_id = int(data[1])
        restaurant_name = data[2]

        await state.update_data(restaurant_id=restaurant_id, restaurant_name=restaurant_name)
        await state.set_state(Register.date)
        await callback.message.answer("Выберите дату бронирования:", reply_markup=kb.generate_date_buttons())
    except Exception:
        await callback.message.answer("Ошибка в выборе ресторана, попробуйте снова.")

@router.callback_query(Register.date)
async def register_date(callback: CallbackQuery, state: FSMContext):
    try:
        day = int(callback.data.split(":")[1])
        date = (datetime.now().date() + timedelta(days=day)).strftime("%d-%m-%Y")

        await state.update_data(date=date)
        await state.set_state(Register.time)
        time_buttons = kb.generate_time_buttons(date)
        await callback.message.answer("Выберите время:", reply_markup=time_buttons)
    except Exception:
        await callback.message.answer("Ошибка в выборе даты, попробуйте снова.")

# @router.callback_query(Register.time)
# async def register_time(callback: CallbackQuery, state: FSMContext):
#     try:
#         hour = int(callback.data.split(":")[1])
#         time = f"{hour:02d}:00"
#
#         await state.update_data(time=time)
#         await state.set_state(Register.hours)
#         await callback.message.answer("Выберите количество часов бронирования:", reply_markup=kb.generate_hours_buttons())
#     except Exception:
#         await callback.message.answer("Ошибка в выборе времени, попробуйте снова.")
@router.callback_query(Register.time)
async def register_time(callback: CallbackQuery, state: FSMContext):
    try:
        hour = int(callback.data.split(":")[1])  # Извлекаем выбранное время
        time = f"{hour:02d}:00"  # Форматируем время (например, 18:00)

        await state.update_data(time=time)  # Сохраняем выбранное время в состоянии
        await state.set_state(Register.hours)

        # Генерируем кнопки для выбора количества часов
        hours_buttons = kb.generate_hours_buttons(selected_time=hour)
        await callback.message.answer(
            "Выберите количество часов бронирования:",
            reply_markup=hours_buttons
        )
    except Exception:
        await callback.message.answer("Ошибка в выборе времени, попробуйте снова.")

@router.callback_query(Register.hours)
async def register_hours(callback: CallbackQuery, state: FSMContext):
    try:
        hours = int(callback.data.split(":")[1])
        await state.update_data(hours=hours)

        await state.set_state(Register.number_of_guests)
        await callback.message.answer("Введите количество гостей:")
    except Exception:
        await callback.message.answer("Ошибка в выборе количества часов, попробуйте снова.")

@router.message(Register.number_of_guests)
async def register_guests(message: Message, state: FSMContext):
    if message.text.isdigit():
        number_of_guests = int(message.text)
        if number_of_guests <= 10:  # Ограничение на количество гостей
            data = await state.get_data()
            reservation_time = datetime.strptime(f"{data['date']} {data['time']}", "%d-%m-%Y %H:%M")
            restaurant_id = data['restaurant_id']
            reservation_hours = data['hours']


            suitable_tables = await rq_b.find_suitable_table(restaurant_id, number_of_guests, reservation_time, reservation_hours)

            if suitable_tables:
                markup = kb.generate_table_buttons(suitable_tables)
                await state.update_data(number_of_guests=number_of_guests)
                await state.set_state(Register.table_choice)
                phot = FSInputFile('D:\\PycharmProjects\\bron_kur\\столы2.jpg')
                await message.answer_photo(phot)
                await message.answer("Выберите столик:", reply_markup=markup)
            else:
                await message.answer("Подходящие столы не найдены. Попробуйте другое время.")
                await state.clear()
        else:
            await message.answer("Максимальное количество гостей — 6.\n Пожалуйста, укажите другое количество или обратитесь к администратору.")
    else:
        await message.answer("Пожалуйста, укажите количество гостей числом.")



@router.callback_query(lambda c: c.data and c.data.startswith("select_table:"))
async def register_table_choice(callback: CallbackQuery, state: FSMContext):
    try:
        _, table_id, table_number = callback.data.split(":")
        table_id = int(table_id)
        table_number = int(table_number)

        await state.update_data(table_id=table_id, table_number=table_number)
        await state.set_state(Register.name)
        await callback.message.answer("Введите имя, на которое будет сделано бронирование:")
    except Exception as e:
        print(f"Error in register_table_choice: {e}")
        await callback.message.answer("Ошибка в выборе столика, попробуйте снова.")


@router.message(Register.name)
async def register_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)

    await state.set_state(Register.confirm)
    await confirm_reservation(message, state)

async def confirm_reservation(message: Message, state: FSMContext):
    data = await state.get_data()
    confirmation = (
        f"Подтвердите бронирование:\n"
        f"🏠 Ресторан: {data['restaurant_name']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['time']}\n"
        f"⌛ Длительность: {data['hours']} ч.\n"
        f"👥 Гостей: {data['number_of_guests']}\n"
        f"🪑 Столик: {data['table_number']}\n"
        f"🙍 Имя: {data['name']}\n"
    )
    await message.answer(confirmation, reply_markup=kb.confirmation_buttons())


# Обработчик подтверждения бронирования
@router.callback_query(lambda c: c.data and c.data.startswith("confirm:"))
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.data == "confirm:yes":
        data = await state.get_data()
        reservation_time = datetime.strptime(f"{data['date']} {data['time']}", "%d-%m-%Y %H:%M")
        reservation_id = await rq_b.create_reservation(reservation_time,callback.from_user.id, data["name"], data["number_of_guests"],data["hours"],data['table_id'])
        await callback.message.answer("Бронирование успешно создано!")
        await state.update_data(reservation_id=reservation_id)
        await callback.message.answer("Вы хотите сделать предзаказ ?", reply_markup=kb.preorders_buttons())
        # await state.clear()
    elif callback.data == "confirm:no":
        await callback.message.answer("Что вы хотите исправить?", reply_markup=kb.correction_buttons())


#------------------------------PREORDER
@router.callback_query(lambda c: c.data and c.data.startswith("preorder:"))
async def register_preorder(callback: CallbackQuery, state: FSMContext):
    if callback.data == "preorder:yes":
        # Генерация клавиатуры категорий
        markup = await kb.generate_category_keyboard()
        await callback.message.answer("Выберите категорию блюд:", reply_markup=markup)
    elif callback.data == "preorder:no":
        await callback.message.answer("До скорой встречи ", reply_markup=kb.main)
        # await state.set_state(Register.confirm)
        # await confirm_reservation(callback.message, state)




@router.callback_query(lambda c: c.data and c.data.startswith("category:"))
async def select_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]  # Получаем название категории
    menu_items = await rq_b.get_menu_by_category(category)

    if not menu_items:
        await callback.message.answer("В этой категории пока нет блюд.")
        return

    # Генерация клавиатуры блюд
    markup = kb.generate_dish_keyboard(menu_items)
    await callback.message.answer(f"Вы выбрали категорию: {category.capitalize()}.\nВот список доступных блюд:", reply_markup=markup)


@router.callback_query(lambda c: c.data and c.data.startswith("dish:"))
async def select_dish(callback: CallbackQuery, state: FSMContext):
    dish_id = int(callback.data.split(":")[1])  # Получаем ID блюда

    # Генерация клавиатуры для выбора количества
    markup = kb.generate_quantity_keyboard(dish_id)
    await callback.message.answer("Выберите количество порций:", reply_markup=markup)


@router.callback_query(lambda c: c.data and c.data.startswith("quantity:"))
async def select_quantity(callback: CallbackQuery, state: FSMContext):
    _, dish_id, quantity = callback.data.split(":")
    dish_id = int(dish_id)
    quantity = int(quantity)

    # Загружаем информацию о блюде
    async with async_session() as session:
        dish = await session.get(Menu, dish_id)

    if not dish:
        await callback.message.answer("Ошибка: блюдо не найдено.")
        return

    # Сохраняем выбор в FSMContext
    data = await state.get_data()
    cart = data.get("cart", {})  # Корзина пользователя
    if dish_id in cart:
        cart[dish_id]["quantity"] += quantity
    else:
        cart[dish_id] = {
            "name": dish.name_dish,
            "quantity": quantity,
            "price": dish.price,
        }
    await state.update_data(cart=cart)

    # Подтверждаем добавление в корзину
    await callback.message.answer(
        f"{quantity} x {dish.name_dish} добавлено в корзину. Выберите следующее блюдо или завершите заказ.",reply_markup=kb.end_preorder
    )

    # Вернуться к выбору категорий
    markup = await kb.generate_category_keyboard()
    await callback.message.answer("Выберите следующую категорию блюд:", reply_markup=markup)

@router.callback_query(lambda c: c.data == "finish_preorder")
async def finish_preorder(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})  # Получаем корзину
    reservation_id = data.get("reservation_id")  # Получаем ID брони

    if not reservation_id:
        await callback.message.answer("Ошибка: не найдено бронирование.")
        return

    if not cart:
        await callback.message.answer("Вы не выбрали ни одного блюда.")
        return

    # Формируем текст с итоговым заказом
    order_summary = "Ваш предзаказ:\n\n"
    total_price = 0

    for dish_id, dish in cart.items():  # Проходим по корзине как по словарю
        order_summary += (
            f"🍽 {dish['name']} - {dish['quantity']} шт. "
            f"({dish['price']} руб. за шт.)\n"
        )
        total_price += dish['quantity'] * dish['price']

    order_summary += f"\n💵 Итого: {total_price} руб."

    # Выводим итоговый заказ
    await callback.message.answer(order_summary)

    try:
        # Создаем предзаказ
        await rq_b.create_preorder(reservation_id, cart)

        # Подтверждение успешного предзаказа
        await callback.message.answer("Предзаказ успешно создан! До скорой встречи!",reply_markup=kb.main)
        await state.clear()  # Это завершит состояние
    except Exception as e:
        await callback.message.answer(f"Ошибка при создании предзаказа: {str(e)}")



@router.callback_query(lambda c: c.data == "back_to_categories")
async def back_to_categories_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Вернуться к категориям".
    """
    # Генерируем клавиатуру с категориями
    category_keyboard = await kb.generate_category_keyboard()

    # Редактируем сообщение, заменяя клавиатуру
    await callback.message.edit_text(
        "Выберите категорию:",
        reply_markup=category_keyboard
    )