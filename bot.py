import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, BufferedInputFile

from config import settings
from scraper import collect_all
from knowledge import kb
from recommender import Background, pick_electives

class CompareForm(StatesGroup):
    goal = State()
    python = State()
    math = State()

class AskForm(StatesGroup):
    program = State()
    question = State()

class RecommendForm(StatesGroup):
    program = State()
    goal = State()
    python = State()
    math = State()

async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    txt = (
        "Привет! Я помогу разобраться с магистратурами ИТМО:\n"
        "• Искусственный интеллект (AI)\n"
        "• Управление ИИ-продуктами (AI Product)\n\n"
        "Команды: /compare — подобрать программу, /choose_program — зафиксировать программу, "
        "/plan — показать учебный план, /ask — вопросы по содержимому, /recommend — рекомендации по элективам."
    )
    await message.answer(txt)

async def cmd_compare(message: Message, state: FSMContext):
    await state.set_state(CompareForm.goal)
    await message.answer("Кем вы хотите работать? (ml_engineer / data_engineer / ai_product_manager / analyst)")

async def compare_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text.strip())
    await state.set_state(CompareForm.python)
    await message.answer("Ваш уровень Python? (none / basic / intermediate / advanced)")

async def compare_python(message: Message, state: FSMContext):
    await state.update_data(python=message.text.strip())
    await state.set_state(CompareForm.math)
    await message.answer("Уровень математики? (weak / medium / strong)")

async def compare_done(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    goal = (data.get("goal") or "").lower()
    if goal in ("ai_product_manager",):
        choice = "ai_product"
        reason = "нужны продуктовые компетенции + техническая база"
    elif goal in ("ml_engineer", "data_engineer"):
        choice = "ai"
        reason = "нужна углубленная техническая подготовка и проекты в ML/DE"
    else:
        choice = "ai_product"
        reason = "широкий спектр продуктовых и аналитических дисциплин"
    msg = f"Предлагаю: {('AI Product' if choice=='ai_product' else 'AI')} — {reason}.\n\n" + kb.compare_programs()
    await message.answer(msg)

async def cmd_choose_program(message: Message, state: FSMContext):
    await message.answer("Введите ключ программы: ai или ai_product")
    await state.set_state(AskForm.program)

async def choose_program_set(message: Message, state: FSMContext):
    program = message.text.strip().lower()
    if program not in ("ai", "ai_product"):
        await message.answer("Допустимо: ai или ai_product.")
        return
    await state.update_data(program=program)
    await message.answer(f"Ок! Программа зафиксирована: {program}. Теперь можете использовать /plan, /ask или /recommend.")

async def cmd_plan(message: Message, state: FSMContext):
    data = await state.get_data()
    program = data.get("program")
    if program not in ("ai", "ai_product"):
        await message.answer("Сначала /choose_program (ai или ai_product).")
        return
    df = kb.plan_for(program)
    if df is None or df.empty:
        await message.answer("Не удалось извлечь учебный план автоматически. Я все равно могу отвечать на вопросы по странице программы через /ask.")
        return
    csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    await message.answer_document(BufferedInputFile(csv_bytes, filename=f"{program}_plan.csv"), caption="Учебный план (извлечено из PDF)")

async def cmd_ask(message: Message, state: FSMContext):
    data = await state.get_data()
    program = data.get("program")
    if program not in ("ai", "ai_product"):
        await message.answer("Сначала /choose_program (ai или ai_product).")
        return
    await state.set_state(AskForm.question)
    await message.answer("Задайте вопрос по выбранной программе.")

async def ask_question(message: Message, state: FSMContext):
    data = await state.get_data()
    program = data.get("program")
    answer, sources = kb.answer(program, message.text.strip())
    await message.answer(answer)

async def cmd_recommend(message: Message, state: FSMContext):
    data = await state.get_data()
    program = data.get("program")
    if program not in ("ai", "ai_product"):
        await message.answer("Сначала /choose_program (ai или ai_product).")
        return
    await state.set_state(RecommendForm.goal)
    await message.answer("Цель: (ml_engineer / data_engineer / ai_product_manager / analyst)")

async def rec_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text.strip())
    await state.set_state(RecommendForm.python)
    await message.answer("Уровень Python? (none / basic / intermediate / advanced)")

async def rec_python(message: Message, state: FSMContext):
    await state.update_data(python=message.text.strip())
    await state.set_state(RecommendForm.math)
    await message.answer("Уровень математики? (weak / medium / strong)")

async def rec_done(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    program = data.get("program")
    bg = Background(
        goal=(data.get("goal") or "analyst").lower(),
        python=(data.get("python") or "basic").lower(),
        math=(data.get("math") or "medium").lower(),
    )
    df = kb.plan_for(program)
    recs = pick_electives(df, bg)
    if not recs:
        await message.answer("Пока не получилось подобрать элективы (нужен распарсенный план). Попробуйте позже или спросите через /ask.")
        return
    lines = [f"• {r['title']} (семестр {r['semester'] or '?'}, {r['type'] or 'электив'}, score {r['score']})" for r in recs]
    await message.answer("Рекомендации по элективам:\n" + "\n".join(lines))

async def prepare_data():
    collect_all()
    kb.load()

async def main():
    await prepare_data()
    token = settings.bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
    bot = Bot(token=token)
    dp = Dispatcher()

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_compare, Command("compare"))
    dp.message.register(cmd_choose_program, Command("choose_program"))
    dp.message.register(cmd_plan, Command("plan"))
    dp.message.register(cmd_ask, Command("ask"))
    dp.message.register(cmd_recommend, Command("recommend"))

    dp.message.register(choose_program_set, AskForm.program)
    dp.message.register(compare_goal, CompareForm.goal)
    dp.message.register(compare_python, CompareForm.python)
    dp.message.register(compare_done, CompareForm.math)
    dp.message.register(ask_question, AskForm.question)
    dp.message.register(rec_goal, RecommendForm.goal)
    dp.message.register(rec_python, RecommendForm.python)
    dp.message.register(rec_done, RecommendForm.math)

    @dp.message()
    async def fallback(message: Message):
        await message.answer("Я отвечаю только по магистерским программам ИТМО \"AI\" и \"AI Product\". Используйте /compare, /choose_program, /plan, /ask или /recommend.")

    print("Bot is running...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
