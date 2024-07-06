import os
import csv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from parser import fetch_vacancies
from db import create_table, insert_vacancies, fetch_all_vacancies, clear_table
# Состояния
VAC_SEARCH, VAC_REGION, VAC_COUNT, VAC_FILTERS, VAC_SALARY, VAC_EXPERIENCE, VAC_EMPLOYMENT, VAC_SCHEDULE = range(8)
# Старт
async def start_command(update: Update, context: CallbackContext) -> None:
    keyboard = [['/start', '/search', '/save', '/export', '/clear']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        'Привет! Я бот-парсер для вакансий с hh.ru.\nВыбери команду:',
        reply_markup=reply_markup
    )
# Сохранение
async def vac_save(update: Update, context: CallbackContext) -> None:
    create_table()
    vacancies = context.user_data.get('vacancies', [])
    if vacancies:
        insert_vacancies(vacancies)
        await update.message.reply_text('Я сохранил вакансии в базу данных.')
        context.user_data.pop('vacancies', None)
        return ConversationHandler.END
    else:
        await update.message.reply_text('Увы, у тебя нет вакансий для сохранения.')
# Экспорт
async def vac_export_start(update: Update, context: CallbackContext) -> None:
    vacancies = fetch_all_vacancies()
    if not vacancies:
        if update.message:
            await update.message.reply_text('Увы, у тебя нет данных для экспорта.')
        else:
            await update.callback_query.message.reply_text('Увы, у тебя нет данных для экспорта.')
        return
    keyboard = [
        [InlineKeyboardButton("Экспорт в CSV", callback_data='export_csv')],
        [InlineKeyboardButton("Экспорт в чат", callback_data='export_chat')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text('Выбери, как ты хочешь экспортировать вакансии:', reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text('Выбери, как ты хочешь экспортировать вакансии:', reply_markup=reply_markup)
# Обработчик для команды экспорта
async def vac_export_boss(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == 'export_csv':
        await vac_export_csv(update, context)
    elif query.data == 'export_chat':
        await vac_export_chat(update, context)
# Экспорт в CSV
async def vac_export_csv(update: Update, context: CallbackContext):
    vacancies = fetch_all_vacancies()
    if not vacancies:
        await update.callback_query.answer('Увы, у тебя нет данных для экспорта.', show_alert=True)
        return
    file_path = '/tmp/vacancies.csv'
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Название', 'Регион', 'Компания', 'Роли', 'Зарплата', 'Опыт', 'Тип занятости', 'График работы', 'Описание', 'Ссылка'])
        for v in vacancies:
            name, area, employer, roles, salary, experience, employment, schedule, snippet, url = v
            formatted_salary = salary_format(salary)
            writer.writerow([name, area, employer, ', '.join(roles), formatted_salary, experience, employment, schedule, snippet, url])
    with open(file_path, 'rb') as file:
        await update.callback_query.message.reply_document(file)
    os.remove(file_path)
# Экспорт в чат
async def vac_export_chat(update: Update, context: CallbackContext):
    vacancies = fetch_all_vacancies()
    if not vacancies:
        await update.callback_query.answer('Увы, у тебя нет данных для экспорта.', show_alert=True)
        return
    for v in vacancies:
        name, area, employer, roles, salary, experience, employment, schedule, snippet, url = v
        formatted_salary = salary_format(salary)
        message = (
            f"Название: {name}\n"
            f"Регион: {area}\n"
            f"Компания: {employer}\n"
            f"Роли: {', '.join(roles)}\n"
            f"Зарплата: {formatted_salary}\n"
            f"Опыт: {experience}\n"
            f"Тип занятости: {employment}\n"
            f"График работы: {schedule}\n"
            f"Описание: {snippet}\n"
            f"Ссылка: {url}\n"
            "------------------------------"
        )
        await update.callback_query.message.reply_text(message.strip())
# Очистка
async def vac_clear(update: Update, context: CallbackContext) -> None:
    clear_table()
    await update.message.reply_text('Я удалил все сохраненные вакансии.')
# Поиск
async def vac_search_name(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Введи название вакансии, которую ты хочешь найти:')
    return VAC_SEARCH
# Управление поиском
async def search_boss(update: Update, context: CallbackContext) -> int:
    vacancy = context.user_data.get('vacancy')
    region = context.user_data.get('region')
    count = context.user_data.get('count')
    salary = context.user_data.get('salary')
    experience = context.user_data.get('experience')
    employment = context.user_data.get('employment')
    schedule = context.user_data.get('schedule')
    vacancies = fetch_vacancies(vacancy, region, count, salary, experience, employment, schedule)
    context.user_data['vacancies'] = vacancies
    if vacancies:
        for v in vacancies:
            formatted_salary = salary_format(v['salary'])
            message = (
                f"Название: {v['name']}\n"
                f"Регион: {v['area']}\n"
                f"Компания: {v['employer']}\n"
                f"Роли: {', '.join(v['professional_roles'])}\n"
                f"Зарплата: {formatted_salary}\n"
                f"Опыт: {v['experience']}\n"
                f"Тип занятости: {v['employment']}\n"
                f"График работы: {v['schedule']}\n"
                f"Описание: {v['snippet']}\n"
                f"Ссылка: {v['url']}\n"
                "------------------------------"
            )
            if update.callback_query:
                await update.callback_query.message.reply_text(message.strip())
            else:
                await update.message.reply_text(message.strip())
    else:
        if update.callback_query:
            await update.callback_query.message.reply_text('Увы, но вакансии не найдены. Попробуй поменять фильтры.')
        else:
            await update.message.reply_text('Увы, но вакансии не найдены. Попробуй поменять фильтры.')
    return ConversationHandler.END
# Регион
async def vac_search_region(update: Update, context: CallbackContext) -> int:
    context.user_data['vacancy'] = update.message.text
    await update.message.reply_text('Введи регион для поиска вакансий:')
    return VAC_REGION
# Количество вакансий
async def vac_search_count(update: Update, context: CallbackContext) -> int:
    context.user_data['region'] = update.message.text
    await update.message.reply_text('Введи количество вакансий, которое ты хочешь получить (от 1 до 20):')
    return VAC_COUNT
# Защита от неверного ввода
async def vac_search_count_safe(update: Update, context: CallbackContext) -> int:
    try:
        count = int(update.message.text)
        if count <= 0:
            await update.message.reply_text('Пожалуйста, введи положительное число.')
            return VAC_COUNT
    except ValueError:
        await update.message.reply_text('Пожалуйста, введи число.')
        return VAC_COUNT

    context.user_data['count'] = count
    return await vac_filter_menu(update, context)
# Меню с фильтрами
async def vac_filter_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Зарплата", callback_data='salary')],
        [InlineKeyboardButton("Опыт работы", callback_data='experience')],
        [InlineKeyboardButton("Тип занятости", callback_data='employment')],
        [InlineKeyboardButton("График работы", callback_data='schedule')],
        [InlineKeyboardButton("Начать поиск", callback_data='start_search')],
        [InlineKeyboardButton("Сбросить фильтры", callback_data='reset_filters')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text('Выбери фильтр:', reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text('Выбери фильтр:', reply_markup=reply_markup)
    return VAC_FILTERS
# Обработчик фильтров
async def vac_filter_boss(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'salary':
        await query.edit_message_text('Введи зарплату в формате "от-до":')
        return VAC_SALARY
    elif query.data == 'experience':
        keyboard = [
            [InlineKeyboardButton("Не имеет значения", callback_data='no_matter')],
            [InlineKeyboardButton("Без опыта", callback_data='no_experience')],
            [InlineKeyboardButton("От 1 года до 3 лет", callback_data='1-3')],
            [InlineKeyboardButton("От 3 до 6 лет", callback_data='3-6')],
            [InlineKeyboardButton("Более 6 лет", callback_data='6+')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Выбери опыт работы:', reply_markup=reply_markup)
        return VAC_EXPERIENCE
    elif query.data == 'employment':
        keyboard = [
            [InlineKeyboardButton("Полная занятость", callback_data='full')],
            [InlineKeyboardButton("Частичная занятость", callback_data='part')],
            [InlineKeyboardButton("Стажировка", callback_data='internship')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Выбери занятость:', reply_markup=reply_markup)
        return VAC_EMPLOYMENT
    elif query.data == 'schedule':
        keyboard = [
            [InlineKeyboardButton("Полный день", callback_data='full_day')],
            [InlineKeyboardButton("Сменный график", callback_data='shift')],
            [InlineKeyboardButton("Гибкий график", callback_data='flexible')],
            [InlineKeyboardButton("Удаленная работа", callback_data='remote')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Выбери график работы:', reply_markup=reply_markup)
        return VAC_SCHEDULE
    elif query.data == 'reset_filters':
        context.user_data.pop('salary', None)
        context.user_data.pop('experience', None)
        context.user_data.pop('employment', None)
        context.user_data.pop('schedule', None)
        await query.edit_message_text('Фильтры сброшены.')
        return await vac_filter_menu(update, context)
    elif query.data == 'start_search':
        return await search_boss(update, context)
# Защита от неверного ввода
async def vac_salary_input_safe(update: Update, context: CallbackContext) -> int:
    salary_range = update.message.text.split('-')
    if len(salary_range) != 2:
        await update.message.reply_text('Пожалуйста, введи зарплату в правильном формате "от-до".')
        return VAC_SALARY
    try:
        salary_from = int(salary_range[0])
        salary_to = int(salary_range[1])
    except ValueError:
        await update.message.reply_text('Пожалуйста, введи зарплату в правильном формате "от-до".')
        return VAC_SALARY
    context.user_data['salary'] = (salary_from, salary_to)
    return await vac_filter_menu(update, context)
# Опыт работы
async def vac_experience_choose(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    experience_map = {
        'no_matter': 'Не имеет значения',
        'no_experience': 'Без опыта',
        '1-3': 'От 1 года до 3 лет',
        '3-6': 'От 3 до 6 лет',
        '6+': 'Более 6 лет',
    }
    context.user_data['experience'] = experience_map.get(query.data, 'Не имеет значения')
    return await vac_filter_menu(update, context)
# Занятость
async def vac_employment_choose(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    employment_map = {
        'full': 'Полная занятость',
        'part': 'Частичная занятость',
        'internship': 'Стажировка',
    }
    context.user_data['employment'] = employment_map.get(query.data, 'Полная занятость')
    return await vac_filter_menu(update, context)
# График
async def vac_schedule_choose(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    schedule_map = {
        'full_day': 'Полный день',
        'shift': 'Сменный график',
        'flexible': 'Гибкий график',
        'remote': 'Удаленная работа',
    }
    context.user_data['schedule'] = schedule_map.get(query.data, 'Полный день')
    return await vac_filter_menu(update, context)
# Форматирование зарплаты в читаемый вид
def salary_format(salary):
    if salary is None:
        return "Не указана"
    elif isinstance(salary, dict):
        if salary['from'] and salary['to']:
            return f"{salary['from']} - {salary['to']} {salary['currency']}"
        elif salary['from']:
            return f"от {salary['from']} {salary['currency']}"
        elif salary['to']:
            return f"до {salary['to']} {salary['currency']}"
    return "Не указана"
# Главная функция 
def main() -> None:
    application = Application.builder().token("Твой токен").build() # Тут нужно ввести свой токен
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('search', vac_search_name)],
    states={
        VAC_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, vac_search_region)],
        VAC_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, vac_search_count)],
        VAC_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, vac_search_count_safe)],
        VAC_FILTERS: [CallbackQueryHandler(vac_filter_boss)],
        VAC_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, vac_salary_input_safe)],
        VAC_EXPERIENCE: [CallbackQueryHandler(vac_experience_choose)],
        VAC_EMPLOYMENT: [CallbackQueryHandler(vac_employment_choose)],
        VAC_SCHEDULE: [CallbackQueryHandler(vac_schedule_choose)],
    },
    fallbacks=[CommandHandler('start', start_command)],
    )
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('save', vac_save))
    application.add_handler(CommandHandler('export', vac_export_start))
    application.add_handler(CommandHandler('clear', vac_clear))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(vac_export_boss, pattern='^export_(csv|chat)$'))
    application.run_polling()
if __name__ == '__main__':
    main()