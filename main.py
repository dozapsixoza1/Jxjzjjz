import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройки
BOT_TOKEN = "8465744678:AAH4-rJleNyXHFzwldsI017BEccsXsItpDA"
ADMIN_CHAT_LINK = "https://t.me/+qaYhixzglrJlMzcy"
OWNER_ID = 6979133757

ADMINS_FILE = 'admins.json'
PENDING_APPLICATIONS_FILE = 'pending_applications.json'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# States для формы
class Form(StatesGroup):
    name = State()
    age = State()
    location = State()
    sphere = State()
    time = State()
    punishment = State()

class AdminBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.load_data()
        self.setup_handlers()
    
    def load_data(self):
        # Загрузка списка админов
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                self.admins = json.load(f)
        else:
            self.admins = []
        
        # Загрузка pending заявок
        if os.path.exists(PENDING_APPLICATIONS_FILE):
            with open(PENDING_APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
                self.pending_applications = json.load(f)
        else:
            self.pending_applications = {}
    
    def save_admins(self):
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.admins, f, ensure_ascii=False)
    
    def save_pending_applications(self):
        with open(PENDING_APPLICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.pending_applications, f, ensure_ascii=False)
    
    def setup_handlers(self):
        # Команды
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.message.register(self.admin_panel_handler, Command("admin"))
        self.dp.message.register(self.form_handler, Command("form"))
        self.dp.message.register(self.add_admin_handler, Command("addadmin"))
        self.dp.message.register(self.remove_admin_handler, Command("removeadmin"))
        self.dp.message.register(self.list_admins_handler, Command("listadmins"))
        
        # Обработчики формы
        self.dp.message.register(self.process_name, Form.name)
        self.dp.message.register(self.process_age, Form.age)
        self.dp.message.register(self.process_location, Form.location)
        self.dp.message.register(self.process_sphere, Form.sphere)
        self.dp.message.register(self.process_time, Form.time)
        self.dp.message.register(self.process_punishment, Form.punishment)
        
        # Обработчики callback кнопок
        self.dp.callback_query.register(self.handle_button, F.data.startswith(('pending_', 'approved_', 'rejected_')))
    
    async def start_handler(self, message: types.Message):
        await message.answer(
            "Привет! Я бот для подачи заявки на пост администратора.\n"
            "Используй команду /form чтобы заполнить заявку."
        )
    
    async def form_handler(self, message: types.Message, state: FSMContext):
        await state.set_state(Form.name)
        await message.answer(
            "Заполните форму для подачи заявки на пост администратора:\n\n"
            "1. Ваше имя:"
        )
    
    async def process_name(self, message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await state.set_state(Form.age)
        await message.answer("2. Ваш возраст:")
    
    async def process_age(self, message: types.Message, state: FSMContext):
        await state.update_data(age=message.text)
        await state.set_state(Form.location)
        await message.answer("3. Где проживаете:")
    
    async def process_location(self, message: types.Message, state: FSMContext):
        await state.update_data(location=message.text)
        await state.set_state(Form.sphere)
        await message.answer("4. На администратора какой сферы вы бы хотели пойти(Войс/Чат):")
    
    async def process_sphere(self, message: types.Message, state: FSMContext):
        await state.update_data(sphere=message.text)
        await state.set_state(Form.time)
        await message.answer("5. Сколько готовы уделять времени чату:")
    
    async def process_time(self, message: types.Message, state: FSMContext):
        await state.update_data(time=message.text)
        await state.set_state(Form.punishment)
        await message.answer("6. Готовы ли Вы в случае нарушений получить строгое наказание:")
    
    async def process_punishment(self, message: types.Message, state: FSMContext):
        form_data = await state.get_data()
        user_id = message.from_user.id
        
        # Форма завершена
        application_id = f"{user_id}_{message.date.timestamp()}"
        
        # Сохраняем заявку
        self.pending_applications[application_id] = {
            'user_id': user_id,
            'user_info': {
                'id': message.from_user.id,
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name
            },
            'form_data': form_data,
            'status': 'pending'
        }
        self.save_pending_applications()
        
        # Отправляем админам
        await self.send_to_admins(application_id, form_data, user_id)
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            "✅ Ваша заявка отправлена на рассмотрение! "
            "Мы свяжемся с вами в ближайшее время."
        )
    
    async def send_to_admins(self, application_id, form_data, applicant_id):
        message_text = (
            "📋 Новая заявка на пост администратора!\n\n"
            f"👤 ID пользователя: {applicant_id}\n"
            f"1. Имя: {form_data['name']}\n"
            f"2. Возраст: {form_data['age']}\n"
            f"3. Место проживания: {form_data['location']}\n"
            f"4. Сфера: {form_data['sphere']}\n"
            f"5. Время: {form_data['time']}\n"
            f"6. Готовность к наказанию: {form_data['punishment']}\n\n"
            f"ID заявки: {application_id}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(text="⏳ На рассмотрении", callback_data=f"pending_{application_id}"),
                InlineKeyboardButton(text="✅ Одобрено", callback_data=f"approved_{application_id}"),
            ],
            [
                InlineKeyboardButton(text="❌ Отказано", callback_data=f"rejected_{application_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        for admin_id in self.admins:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")
    
    async def handle_button(self, callback: CallbackQuery):
        data = callback.data
        admin_id = callback.from_user.id
        
        # Проверяем, является ли пользователь админом
        if admin_id not in self.admins:
            await callback.answer("❌ У вас нет прав для обработки заявок!", show_alert=True)
            return
        
        action, application_id = data.split('_', 1)
        
        if application_id not in self.pending_applications:
            await callback.answer("❌ Заявка не найдена!", show_alert=True)
            return
        
        application = self.pending_applications[application_id]
        applicant_id = application['user_id']
        admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.first_name
        
        if action == "pending":
            await callback.message.edit_text(
                callback.message.text + f"\n\n🔄 Статус: На рассмотрении\n👤 Обработал: {admin_username}"
            )
            await callback.answer("Статус изменен на 'На рассмотрении'")
        
        elif action == "approved":
            # Обновляем статус заявки
            self.pending_applications[application_id]['status'] = 'approved'
            self.save_pending_applications()
            
            # Отправляем сообщение пользователю
            try:
                await self.bot.send_message(
                    chat_id=applicant_id,
                    text=(
                        "🎉 Поздравляем! Ваша заявка на пост администратора одобрена!\n\n"
                        f"Ссылка для вступления в админ чат: {ADMIN_CHAT_LINK}\n\n"
                        "Добро пожаловать в команду! 🚀"
                    )
                )
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение пользователю: {e}")
            
            await callback.message.edit_text(
                callback.message.text + f"\n\n✅ Статус: ОДОБРЕНО\n👤 Одобрил: {admin_username}"
            )
            await callback.answer("Заявка одобрена!")
        
        elif action == "rejected":
            # Обновляем статус заявки
            self.pending_applications[application_id]['status'] = 'rejected'
            self.save_pending_applications()
            
            # Отправляем сообщение пользователю
            try:
                await self.bot.send_message(
                    chat_id=applicant_id,
                    text="❌ К сожалению, ваша заявка на пост администратора была отклонена."
                )
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение пользователю: {e}")
            
            await callback.message.edit_text(
                callback.message.text + f"\n\n❌ Статус: ОТКЛОНЕНО\n👤 Отклонил: {admin_username}"
            )
            await callback.answer("Заявка отклонена!")
    
    async def admin_panel_handler(self, message: types.Message):
        user_id = message.from_user.id
        
        if user_id == OWNER_ID:
            keyboard = [
                [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
                [InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins")],
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer("Панель управления ботом:", reply_markup=reply_markup)
        elif user_id in self.admins:
            pending_count = len([app for app in self.pending_applications.values() if app['status'] == 'pending'])
            await message.answer(
                f"Вы являетесь администратором бота.\n"
                f"Всего админов: {len(self.admins)}\n"
                f"Заявок на рассмотрении: {pending_count}"
            )
        else:
            await message.answer("У вас нет доступа к этой команде.")
    
    async def add_admin_handler(self, message: types.Message):
        user_id = message.from_user.id
        
        if user_id != OWNER_ID:
            await message.answer("❌ Только владелец может добавлять админов!")
            return
        
        if not message.text.split()[1:]:
            await message.answer("Использование: /addadmin <user_id>")
            return
        
        try:
            new_admin_id = int(message.text.split()[1])
            if new_admin_id not in self.admins:
                self.admins.append(new_admin_id)
                self.save_admins()
                await message.answer(f"✅ Пользователь {new_admin_id} добавлен в админы!")
            else:
                await message.answer("⚠️ Этот пользователь уже является админом!")
        except (ValueError, IndexError):
            await message.answer("❌ Неверный ID пользователя!")
    
    async def remove_admin_handler(self, message: types.Message):
        user_id = message.from_user.id
        
        if user_id != OWNER_ID:
            await message.answer("❌ Только владелец может удалять админов!")
            return
        
        if not message.text.split()[1:]:
            await message.answer("Использование: /removeadmin <user_id>")
            return
        
        try:
            admin_id = int(message.text.split()[1])
            if admin_id in self.admins:
                self.admins.remove(admin_id)
                self.save_admins()
                await message.answer(f"✅ Пользователь {admin_id} удален из админов!")
            else:
                await message.answer("⚠️ Этот пользователь не является админом!")
        except (ValueError, IndexError):
            await message.answer("❌ Неверный ID пользователя!")
    
    async def list_admins_handler(self, message: types.Message):
        user_id = message.from_user.id
        
        if user_id != OWNER_ID and user_id not in self.admins:
            await message.answer("❌ У вас нет прав для просмотра этого списка!")
            return
        
        admins_list = "\n".join([f"• {admin_id}" for admin_id in self.admins])
        await message.answer(f"👥 Список админов:\n{admins_list}\n\nВсего: {len(self.admins)}")
    
    async def run(self):
        await self.dp.start_polling(self.bot)

if __name__ == "__main__":
    bot = AdminBot()
    asyncio.run(bot.run())
