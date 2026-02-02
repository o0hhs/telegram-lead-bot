import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = str(os.getenv("TOKEN"))
bot = Bot(TOKEN)
dp = Dispatcher()

# ID администратора (замените на свой Telegram ID)
# Чтобы узнать свой ID, напишите @userinfobot в Telegram
ADMIN_ID = 123456789  # ЗАМЕНИТЕ НА СВОЙ ID


# FSM для формы обратной связи
class FeedbackForm(StatesGroup):
    name = State()
    phone = State()
    message = State()


# Клавиатуры
def main_kb():
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Оставить заявку")],
            [KeyboardButton(text="ℹ️ О компании"), KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="❓ Частые вопросы")],
        ],
        resize_keyboard=True,
    )


def cancel_kb():
    """Кнопка отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]], resize_keyboard=True
    )


# Обработчики команд
@dp.message(CommandStart())
async def start(message: Message):
    """Приветствие при старте бота"""
    await message.answer(
        f"👋 <b>Добро пожаловать, {message.from_user.first_name}!</b>\n\n"
        "Я бот компании <b>«Ваша Компания»</b>\n\n"
        "Могу помочь вам:\n"
        "📝 Оставить заявку на услугу\n"
        "ℹ️ Узнать о нашей компании\n"
        "📞 Посмотреть контакты\n"
        "❓ Найти ответы на частые вопросы\n\n"
        "Выберите нужный пункт меню ниже 👇",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    """Справка по командам"""
    await message.answer(
        "<b>📖 Доступные команды:</b>\n\n"
        "/start - Главное меню\n"
        "/help - Справка\n"
        "/cancel - Отменить текущее действие",
        parse_mode="HTML",
    )


@dp.message(Command("cancel"))
@dp.message(F.text == "❌ Отменить")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять 😊", reply_markup=main_kb())
        return

    await state.clear()
    await message.answer(
        "✅ Действие отменено.\nВы вернулись в главное меню.", reply_markup=main_kb()
    )


# Форма обратной связи
@dp.message(F.text == "📝 Оставить заявку")
async def start_feedback(message: Message, state: FSMContext):
    """Начало заполнения формы"""
    await state.set_state(FeedbackForm.name)
    await message.answer(
        "📝 <b>Заполнение заявки</b>\n\nШаг 1 из 3\nКак вас зовут?",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )


@dp.message(FeedbackForm.name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени"""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "❌ Слишком короткое имя.\nПожалуйста, введите корректное имя:"
        )
        return

    await state.update_data(name=name)
    await state.set_state(FeedbackForm.phone)
    await message.answer(
        f"Отлично, <b>{name}</b>! 👍\n\n"
        "Шаг 2 из 3\n"
        "Теперь укажите ваш номер телефона:\n"
        "<i>(в формате +7XXXXXXXXXX или просто цифры)</i>",
        parse_mode="HTML",
    )


@dp.message(FeedbackForm.phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефона"""
    phone = message.text.strip()

    # Простая валидация телефона
    digits = "".join(filter(str.isdigit, phone))
    if len(digits) < 10:
        await message.answer(
            "❌ Некорректный номер телефона.\nПожалуйста, введите номер снова:"
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(FeedbackForm.message)
    await message.answer(
        "Отлично! 📱\n\n"
        "Шаг 3 из 3\n"
        "Опишите, что вас интересует или какая услуга нужна:",
        parse_mode="HTML",
    )


@dp.message(FeedbackForm.message)
async def process_message(message: Message, state: FSMContext):
    """Завершение формы и сохранение заявки"""
    user_message = message.text.strip()

    if len(user_message) < 5:
        await message.answer(
            "❌ Слишком короткое сообщение.\nПожалуйста, опишите подробнее:"
        )
        return

    # Получаем все данные
    data = await state.get_data()

    # Формируем данные заявки
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lead_info = (
        f"\n{'=' * 40}\n"
        f"НОВАЯ ЗАЯВКА - {timestamp}\n"
        f"{'=' * 40}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Сообщение: {user_message}\n"
        f"Telegram: @{message.from_user.username if message.from_user.username else 'Не указан'}\n"
        f"User ID: {message.from_user.id}\n"
        f"{'=' * 40}\n"
    )

    # Сохранение в файл
    try:
        with open("leads.txt", "a", encoding="utf-8") as f:
            f.write(lead_info)
    except Exception as e:
        print(f"Ошибка сохранения в файл: {e}")

    # Отправка уведомления администратору
    admin_message = (
        "🔔 <b>НОВАЯ ЗАЯВКА!</b>\n\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"💬 <b>Сообщение:</b>\n{user_message}\n\n"
        f"🆔 <b>Telegram:</b> @{message.from_user.username if message.from_user.username else 'Не указан'}\n"
        f"🕐 <b>Время:</b> {timestamp}"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_message, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
        # Если не получилось отправить админу - не проблема, данные сохранены в файл

    # Ответ пользователю
    await message.answer(
        "✅ <b>Спасибо за вашу заявку!</b>\n\n"
        f"Ваши данные:\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n\n"
        "Мы свяжемся с вами в ближайшее время! 📲\n"
        "Обычно это занимает 1-2 часа.",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )

    await state.clear()


# Информационные разделы
@dp.message(F.text == "ℹ️ О компании")
async def about(message: Message):
    """Информация о компании"""
    await message.answer(
        "🏢 <b>О компании «Ваша Компания»</b>\n\n"
        "Мы занимаемся <b>[описание деятельности]</b>\n\n"
        "📊 Наши преимущества:\n"
        "✅ Опыт работы более 5 лет\n"
        "✅ 500+ довольных клиентов\n"
        "✅ Гарантия качества\n"
        "✅ Индивидуальный подход\n\n"
        "🎯 Мы поможем вам:\n"
        "• [Услуга 1]\n"
        "• [Услуга 2]\n"
        "• [Услуга 3]\n\n"
        "Оставьте заявку, и мы свяжемся с вами! 👇",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )


@dp.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    """Контакты компании"""
    await message.answer(
        "📞 <b>Наши контакты:</b>\n\n"
        "📱 Телефон: <code>+7 (XXX) XXX-XX-XX</code>\n"
        "📧 Email: info@example.com\n"
        "🌐 Сайт: www.example.com\n"
        "📍 Адрес: г. Москва, ул. Примерная, 1\n\n"
        "🕐 <b>Режим работы:</b>\n"
        "Пн-Пт: 9:00 - 18:00\n"
        "Сб-Вс: Выходной\n\n"
        "Или оставьте заявку в боте — перезвоним! 📲",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )


@dp.message(F.text == "❓ Частые вопросы")
async def faq(message: Message):
    """FAQ"""
    await message.answer(
        "❓ <b>Частые вопросы:</b>\n\n"
        "<b>Q: Как быстро вы отвечаете на заявки?</b>\n"
        "A: Обычно в течение 1-2 часов в рабочее время.\n\n"
        "<b>Q: Какие способы оплаты доступны?</b>\n"
        "A: Наличные, безналичный расчёт, карта.\n\n"
        "<b>Q: Предоставляете ли вы гарантию?</b>\n"
        "A: Да, гарантия на все виды работ.\n\n"
        "<b>Q: Работаете ли вы в выходные?</b>\n"
        "A: По договорённости возможен выезд в выходные.\n\n"
        "Остались вопросы? Оставьте заявку! 👇",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )


# Обработка неизвестных сообщений
@dp.message()
async def unknown_message(message: Message):
    """Обработка всех остальных сообщений"""
    await message.answer(
        "🤔 Я не понял вашего сообщения.\n\n"
        "Пожалуйста, используйте кнопки меню ниже 👇\n"
        "Или напишите /help для справки.",
        reply_markup=main_kb(),
    )


# Запуск бота
async def main():
    print("🤖 Бот запущен!")
    print(f"⚠️  Не забудьте указать ADMIN_ID в коде!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
