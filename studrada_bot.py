import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
API_TOKEN = os.getenv("API_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.router import Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.command import Command
from aiogram.filters import StateFilter
import asyncio
import re

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Надіслати повідомлення")],
        [KeyboardButton(text="Надіслати анонімне повідомлення")]
    ],
    resize_keyboard=True
)

tags_markup = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Важливо", callback_data="tag_важливо")],
        [InlineKeyboardButton(text="Скарга", callback_data="tag_скарга")],
        [InlineKeyboardButton(text="Побажання", callback_data="tag_побажання")]
    ]
)

confirmation_markup = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Так", callback_data="confirm_send"),
         InlineKeyboardButton(text="Ні", callback_data="cancel_send")]
    ]
)

anonymous_confirmation_markup = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Так", callback_data="confirm_anonymous_send"),
         InlineKeyboardButton(text="Ні", callback_data="cancel_anonymous_send")]
    ]
)

class MessageState(StatesGroup):
    name = State()
    contact = State()
    group = State()
    media = State()
    message = State()
    tag = State()
    confirmation = State()

class AnonymousMessageState(StatesGroup):
    media = State()
    message = State()
    tag = State()
    contact = State()
    confirmation = State()

def escape_markdown_v2(text: str) -> str:
    escape_chars = r"*_[]()~>#+-=|{}.!"
    return re.sub(f"[{re.escape(escape_chars)}]", r"\\\g<0>", text)

async def format_regular_message(data: dict) -> str:
    return (
        f"Нове повідомлення:\n\n"
        f"👤 *Ім'я:* {escape_markdown_v2(data.get('name'))}\n"
        f"📞 *Контакт:* {escape_markdown_v2(data.get('contact'))}\n"
        f"📚 *Група:* {escape_markdown_v2(data.get('group'))}\n"
        f"📩 *Повідомлення:* {escape_markdown_v2(data.get('final_message', 'Не вказано'))}\n"
        f"🏷 *Тег:* {escape_markdown_v2(data.get('tag'))}"
    )

async def format_anonymous_message(data: dict) -> str:
    return (
        f"Анонімне повідомлення:\n\n"
        f"📩 *Повідомлення:* {escape_markdown_v2(data.get('final_message', 'Не вказано'))}\n"
        f"📞 *Контакт:* {escape_markdown_v2(data.get('contact', 'Не вказано'))}\n"
        f"🏷 *Тег:* {escape_markdown_v2(data.get('tag'))}"
    )

@router.message(Command(commands=["start"]))
async def start(message: types.Message):
    await message.answer(
        "Вітаю, шановний студенте\\! Я бот для надсилання повідомлень, побажань та скарг до студентської ради\\. Оберіть опцію нижче:",
        reply_markup=main_menu,
        parse_mode="MarkdownV2"
    )

@router.message(lambda message: message.text == "Надіслати повідомлення")
async def send_message(message: types.Message, state: FSMContext):
    await message.answer(
        "Введіть ваше *ім'я* та *прізвище* \\(Приклад: *Тарас Іваненко*\\):",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="MarkdownV2"
    )
    await state.set_state(MessageState.name)

@router.message(lambda message: message.text == "Надіслати анонімне повідомлення")
async def send_anonymous_message(message: types.Message, state: FSMContext):
    await message.answer(
        "Введіть ваше *повідомлення* або надішліть *медіафайл* \\(фото/документ\\):",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="MarkdownV2"
    )
    await state.set_state(AnonymousMessageState.media)

@router.message(StateFilter(MessageState.name))
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        "Як з вами *зв'язатися*? Залиште ваш контакт\\(Телеграм/Діскорд\\):",
        parse_mode="MarkdownV2"
    )
    await state.set_state(MessageState.contact)

@router.message(StateFilter(MessageState.contact))
async def get_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await message.answer(
        "Введіть вашу *групу* \\(наприклад, Е\\-14\\):",
        parse_mode="MarkdownV2"
    )
    await state.set_state(MessageState.group)

@router.message(StateFilter(MessageState.group))
async def get_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    await message.answer(
        "Надішліть *медіафайл* \\(фото/документ\\) або напишіть *текст* повідомлення:",
        parse_mode="MarkdownV2"
    )
    await state.set_state(MessageState.media)

async def handle_media_message(message: types.Message, state: FSMContext, is_anonymous: bool):
    data = {}
    if message.content_type == types.ContentType.TEXT:
        data = {"final_message": message.text}
        await state.update_data(**data)
        if is_anonymous:
            await message.answer(
                "Як з вами *зв'язатися*? Залиште ваш контакт\\(Телеграм/Діскорд\\):",
                parse_mode="MarkdownV2"
            )
            await state.set_state(AnonymousMessageState.contact)
        else:
            await message.answer(
                "Оберіть *тег* для повідомлення:",
                reply_markup=tags_markup,
                parse_mode="MarkdownV2"
            )
            await state.set_state(MessageState.tag)
        return

    if message.content_type == types.ContentType.PHOTO:
        file_id = message.photo[-1].file_id
        data = {"final_message": "Фото", "file_type": "photo", "file_id": file_id}
    elif message.content_type == types.ContentType.DOCUMENT:
        file_id = message.document.file_id
        data = {"final_message": "Документ", "file_type": "document", "file_id": file_id}
    else:
        await message.answer(
            "Підтримуються лише *текст*, *фото* або *документи*\\. Спробуйте знову\\.",
            parse_mode="MarkdownV2"
        )
        return

    await state.update_data(**data)
    await message.answer(
        "Напишіть *опис* до вашого медіафайлу або надішліть 'Пропустити', щоб залишити порожнім:",
        parse_mode="MarkdownV2"
    )
    await state.set_state(MessageState.message if not is_anonymous else AnonymousMessageState.message)

@router.message(StateFilter(MessageState.media))
async def get_media_or_message(message: types.Message, state: FSMContext):
    await handle_media_message(message, state, False)

@router.message(StateFilter(AnonymousMessageState.media))
async def get_anonymous_media_or_message(message: types.Message, state: FSMContext):
    await handle_media_message(message, state, True)

async def handle_message_text(message: types.Message, state: FSMContext, is_anonymous: bool):
    if message.text.lower() != "пропустити":
        await state.update_data(final_message=message.text)
    
    if is_anonymous:
        await message.answer(
            "Як з вами *зв'язатися*? \\(Телеграм/Діскорд\\):",
            parse_mode="MarkdownV2"
        )
        await state.set_state(AnonymousMessageState.contact)
    else:
        await message.answer(
            "Оберіть *тег* для повідомлення:",
            reply_markup=tags_markup,
            parse_mode="MarkdownV2"
        )
        await state.set_state(MessageState.tag)

@router.message(StateFilter(MessageState.message))
async def get_message_text(message: types.Message, state: FSMContext):
    await handle_message_text(message, state, False)

@router.message(StateFilter(AnonymousMessageState.message))
async def get_anonymous_message_text(message: types.Message, state: FSMContext):
    await handle_message_text(message, state, True)

@router.message(StateFilter(AnonymousMessageState.contact))
async def get_anonymous_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await message.answer(
        "Оберіть *тег* для повідомлення:",
        reply_markup=tags_markup,
        parse_mode="MarkdownV2"
    )
    await state.set_state(AnonymousMessageState.tag)

async def handle_tag_selection(callback_query: types.CallbackQuery, state: FSMContext, is_anonymous: bool):
    tag = callback_query.data.split("_")[1]
    await state.update_data(tag=tag)
    data = await state.get_data()

    final_text = await format_anonymous_message(data) if is_anonymous else await format_regular_message(data)
    markup = anonymous_confirmation_markup if is_anonymous else confirmation_markup

    await callback_query.message.answer(
        f"Ось підсумкове повідомлення:\n\n{final_text}\n\nБажаєте надіслати це повідомлення?",
        reply_markup=markup,
        parse_mode="MarkdownV2"
    )
    await state.set_state(AnonymousMessageState.confirmation if is_anonymous else MessageState.confirmation)

@router.callback_query(StateFilter(MessageState.tag))
async def select_tag(callback_query: types.CallbackQuery, state: FSMContext):
    await handle_tag_selection(callback_query, state, False)

@router.callback_query(StateFilter(AnonymousMessageState.tag))
async def select_anonymous_tag(callback_query: types.CallbackQuery, state: FSMContext):
    await handle_tag_selection(callback_query, state, True)

async def send_final_message(chat_id: str, data: dict, is_anonymous: bool):
    message_text = await format_anonymous_message(data) if is_anonymous else await format_regular_message(data)
    
    if data.get("file_type") == "photo":
        await bot.send_photo(
            chat_id=chat_id,
            photo=data["file_id"],
            caption=message_text,
            parse_mode="MarkdownV2"
        )
    elif data.get("file_type") == "document":
        await bot.send_document(
            chat_id=chat_id,
            document=data["file_id"],
            caption=message_text,
            parse_mode="MarkdownV2"
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode="MarkdownV2"
        )

async def handle_confirmation(callback_query: types.CallbackQuery, state: FSMContext, is_anonymous: bool):
    if callback_query.data.startswith("confirm"):
        data = await state.get_data()
        await send_final_message(GROUP_CHAT_ID, data, is_anonymous)
        await callback_query.message.answer(
            "Ваше повідомлення успішно надіслано!" if not is_anonymous else "Ваше анонімне повідомлення успішно надіслано!"
        )
    else:
        await callback_query.message.answer("Повертаємося до головного меню.")
    
    await callback_query.message.answer("Оберіть опцію нижче:", reply_markup=main_menu)
    await state.clear()

@router.callback_query(StateFilter(MessageState.confirmation))
async def confirm_send(callback_query: types.CallbackQuery, state: FSMContext):
    await handle_confirmation(callback_query, state, False)

@router.callback_query(StateFilter(AnonymousMessageState.confirmation))
async def confirm_anonymous_send(callback_query: types.CallbackQuery, state: FSMContext):
    await handle_confirmation(callback_query, state, True)

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())