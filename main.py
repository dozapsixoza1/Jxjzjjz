import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import json
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Файл для хранения админов
ADMINS_FILE = 'admins.json'
PENDING_APPLICATIONS_FILE = 'pending_applications.json'

class AdminBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        self.load_data()
    
    def load_data(self):
        # Загрузка списка админов
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r') as f:
                self.admins = json.load(f)
        else:
            self.admins = []
        
        # Загрузка pending заявок
        if os.path.exists(PENDING_APPLICATIONS_FILE):
            with open(PENDING_APPLICATIONS_FILE, 'r') as f:
                self.pending_applications = json.load(f)
        else:
            self.pending_applications = {}
    
    def save_admins(self):
        with open(ADMINS_FILE, 'w') as f:
            json.dump(self.admins, f)
    
    def save_pending_applications(self):
        with open(PENDING_APPLICATIONS_FILE, 'w') as f:
            json.dump(self.pending_applications, f)
    
    def setup_handlers(self):
        # Команды
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("admin", self.admin_panel))
        self.application.add_handler(CommandHandler("form", self.send_form))
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработчики callback кнопок
        self.application.add_handler(CallbackQueryHandler(self.handle_button))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Привет! Я бот для подачи заявки на пост администратора.\n"
            "Используй команду /form чтобы заполнить заявку."
        )
    
    async def send_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        context.user_data['awaiting_form'] = True
        context.user_data['form_stage'] = 1
        
        await update.message.reply_text(
            "Заполните форму для подачи заявки на пост администратора:\n\n"
            "1. Ваше имя:"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if context.user_data.get('awaiting_form'):
            stage = context.user_data.get('form_stage', 1)
            text = update.message.text
            
            if 'form_data' not in context.user_data:
                context.user_data['form_data'] = {}
            
            if stage == 1:
                context.user_data['form_data']['name'] = text
                context.user_data['form_stage'] = 2
                await update.message.reply_text("2. Ваш возраст:")
            
            elif stage == 2:
                context.user_data['form_data']['age'] = text
                context.user_data['form_stage'] = 3
                await update.message.reply_text("3. Где проживаете:")
            
            elif stage == 3:
                context.user_data['form_data']['location'] = text
                context.user_data['form_stage'] = 4
                await update.message.reply_text("4. На администратора какой сферы вы бы хотели пойти(Войс/Чат):")
            
            elif stage == 4:
                context.user_data['form_data']['sphere'] = text
                context.user_data['form_stage'] = 5
                await update.message.reply_text("5. Сколько готовы уделять времени чату:")
            
            elif stage == 5:
                context.user_data['form_data']['time'] = text
                context.user_data['form_stage'] = 6
                await update.message.reply_text("6. Готовы ли Вы в случае нарушений получить строгое наказание:")
            
            elif stage == 6:
                context.user_data['form_data']['punishment'] = text
                
                # Форма завершена
                form_data = context.user_data['form_data']
                application_id = f"{user_id}_{update.message.date.timestamp()}"
                
                # Сохраняем заявку
                self.pending_applications[application_id] = {
                    'user_id': user_id,
                    'user_info': update.message.from_user.to_dict(),
                    'form_data': form_data,
                    'status': 'pending'
                }
                self.save_pending_applications()
                
                # Отправляем админам
                await self.send_to_admins(application_id, form_data, user_id)
                
                # Очищаем данные формы
                context.user_data.pop('awaiting_form', None)
                context.user_data.pop('form_stage', None)
                context.user_data.pop('form_data', None)
                
                await update.message.reply_text(
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
                InlineKeyboardButton("⏳ На рассмотрении", callback_data=f"pending_{application_id}"),
                InlineKeyboardButton("✅ Одобрено", callback_data=f"approved_{application_id}"),
            ],
            [
                InlineKeyboardButton("❌ Отказано", callback_data=f"rejected_{application_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for admin_id in self.admins:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение админу {admin_id}: {e}")
    
    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        admin_id = query.from_user.id
        
        # Проверяем, является ли пользователь админом
        if admin_id not in self.admins:
            await query.edit_message_text("❌ У вас нет прав для обработки заявок!")
            return
        
        action, application_id = data.split('_', 1)
        
        if application_id not in self.pending_applications:
            await query.edit_message_text("❌ Заявка не найдена!")
            return
        
        application = self.pending_applications[application_id]
        applicant_id = application['user_id']
        
        if action == "pending":
            await query.edit_message_text(
                query.message.text + f"\n\n🔄 Статус: На рассмотрении\n👤 Обработал: @{query.from_user.username}"
            )
        
        elif action == "approved":
            # Обновляем статус заявки
            self.pending_applications[application_id]['status'] = 'approved'
            self.save_pending_applications()
            
            # Отправляем сообщение пользователю
            try:
                await context.bot.send_message(
                    chat_id=applicant_id,
                    text=(
                        "🎉 Поздравляем! Ваша заявка на пост администратора одобрена!\n\n"
                        "Ссылка для вступления в админ чат: https://https://t.me/+qaYhixzglrJlMzcy\n\n"
                        "Добро пожаловать в команду! 🚀"
                    )
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю: {e}")
            
            await query.edit_message_text(
                query.message.text + f"\n\n✅ Статус: ОДОБРЕНО\n👤 Одобрил: @{query.from_user.username}"
            )
        
        elif action == "rejected":
            # Обновляем статус заявки
            self.pending_applications[application_id]['status'] = 'rejected'
            self.save_pending_applications()
            
            # Отправляем сообщение пользователю
            try:
                await context.bot.send_message(
                    chat_id=applicant_id,
                    text="❌ К сожалению, ваша заявка на пост администратора была отклонена."
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю: {e}")
            
            await query.edit_message_text(
                query.message.text + f"\n\n❌ Статус: ОТКЛОНЕНО\n👤 Отклонил: @{query.from_user.username}"
            )
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if user_id == self.get_owner_id():  # Владелец
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
                [InlineKeyboardButton("👥 Управление админами", callback_data="manage_admins")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Панель управления ботом:",
                reply_markup=reply_markup
            )
        elif user_id in self.admins:  # Админ
            await update.message.reply_text(
                f"Вы являетесь администратором бота.\n"
                f"Всего админов: {len(self.admins)}\n"
                f"Заявок на рассмотрении: {len([app for app in self.pending_applications.values() if app['status'] == 'pending'])}"
            )
        else:
            await update.message.reply_text("У вас нет доступа к этой команде.")
    
    def get_owner_id(self):
        # Здесь укажите ID владельца бота
        return 6979133757  # Замените на ваш ID
    
    def add_admin(self, admin_id):
        if admin_id not in self.admins:
            self.admins.append(admin_id)
            self.save_admins()
            return True
        return False
    
    def remove_admin(self, admin_id):
        if admin_id in self.admins:
            self.admins.remove(admin_id)
            self.save_admins()
            return True
        return False
    
    def run(self):
        self.application.run_polling()

# Использование бота
if __name__ == "__main__":
    # Замените 'YOUR_BOT_TOKEN' на токен вашего бота
    bot = AdminBot('8465744678:AAH4-rJleNyXHFzwldsI017BEccsXsItpDA')
    
    # Для добавления админов владельцем (пример):
    # bot.add_admin(123456789)  # ID админа
    
    bot.run()
